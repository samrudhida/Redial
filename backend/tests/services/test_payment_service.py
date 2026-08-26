"""Tests for PaymentService read/list/aggregate operations.

``get_revenue_recovered`` is the one piece of real business logic introduced
here: it must count a payment that succeeds after a prior failure, but must
NOT count a mandate's very first attempt succeeding outright.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from backend.app.core.exceptions import NotFoundError
from backend.app.models.enums import PaymentStatus, RetryStatus
from backend.app.repositories.retry_schedule_repository import RetryScheduleRepository
from backend.app.services.mandate_service import MandateService
from backend.app.services.payment_service import PaymentService


@pytest.fixture()
def mandate_id(db_session: Session):
    return MandateService(db_session).register_mandate("cust-1", "REF-1", Decimal("500.00")).id


def test_get_attempt_raises_not_found_for_unknown_id(db_session: Session) -> None:
    service = PaymentService(db_session)

    with pytest.raises(NotFoundError):
        service.get_attempt(uuid.uuid4())


def test_list_attempts_filters_by_status(db_session: Session, mandate_id) -> None:
    service = PaymentService(db_session)
    failed = service.record_payment_attempt(mandate_id)
    service.mark_payment_failure(failed.id)
    succeeded = service.record_payment_attempt(mandate_id)
    service.mark_payment_success(succeeded.id)

    assert len(service.list_attempts(mandate_id)) == 2
    assert [a.id for a in service.list_attempts(mandate_id, status=PaymentStatus.FAILED)] == [failed.id]
    assert [a.id for a in service.list_attempts(mandate_id, status=PaymentStatus.SUCCEEDED)] == [succeeded.id]


def test_revenue_recovered_excludes_first_attempt_success(db_session: Session) -> None:
    mandate_id = MandateService(db_session).register_mandate("cust-1", "REF-1", Decimal("750.00")).id
    service = PaymentService(db_session)

    first_attempt = service.record_payment_attempt(mandate_id, amount=Decimal("750.00"))
    service.mark_payment_success(first_attempt.id)

    assert service.get_revenue_recovered() == Decimal("0")


def test_revenue_recovered_counts_success_after_prior_failure(db_session: Session, mandate_id) -> None:
    service = PaymentService(db_session)

    failed = service.record_payment_attempt(mandate_id, amount=Decimal("500.00"))
    service.mark_payment_failure(failed.id)
    recovered = service.record_payment_attempt(mandate_id, amount=Decimal("500.00"))
    service.mark_payment_success(recovered.id)

    assert service.get_revenue_recovered() == Decimal("500.00")


def test_count_by_status_groups_correctly(db_session: Session, mandate_id) -> None:
    service = PaymentService(db_session)
    a1 = service.record_payment_attempt(mandate_id)
    service.mark_payment_failure(a1.id)
    a2 = service.record_payment_attempt(mandate_id)
    service.mark_payment_success(a2.id)

    counts = service.count_by_status()

    assert counts[PaymentStatus.FAILED] == 1
    assert counts[PaymentStatus.SUCCEEDED] == 1


class _FakeRazorpayClient:
    """Stands in for RazorpayClient — no network, no real credentials required."""

    def __init__(self, *, order_id: str = "order_fake123", should_fail: bool = False) -> None:
        self.order_id = order_id
        self.should_fail = should_fail
        self.create_order_calls: list[dict] = []

    def create_order(self, *, amount, currency, receipt, notes=None):
        from backend.app.payments.razorpay_client import RazorpayUnavailableError

        self.create_order_calls.append({"amount": amount, "currency": currency, "receipt": receipt, "notes": notes})
        if self.should_fail:
            raise RazorpayUnavailableError("simulated Razorpay outage")
        return {"id": self.order_id, "amount": int(amount * 100), "currency": currency, "status": "created"}


def test_record_payment_attempt_creates_a_real_order_when_razorpay_is_configured(db_session: Session, mandate_id) -> None:
    fake_client = _FakeRazorpayClient(order_id="order_abc123")
    service = PaymentService(db_session, razorpay_client=fake_client)

    attempt = service.record_payment_attempt(mandate_id, amount=Decimal("500.00"))

    assert attempt.razorpay_order_id == "order_abc123"
    assert fake_client.create_order_calls == [{"amount": Decimal("500.00"), "currency": "INR", "receipt": str(attempt.id), "notes": {"mandate_id": str(mandate_id), "payment_attempt_id": str(attempt.id)}}]


def test_record_payment_attempt_degrades_gracefully_when_razorpay_order_creation_fails(db_session: Session, mandate_id) -> None:
    fake_client = _FakeRazorpayClient(should_fail=True)
    service = PaymentService(db_session, razorpay_client=fake_client)

    attempt = service.record_payment_attempt(mandate_id, amount=Decimal("500.00"))

    assert attempt.razorpay_order_id is None
    assert attempt.status == PaymentStatus.PENDING


def test_record_payment_attempt_without_razorpay_client_behaves_exactly_as_before(db_session: Session, mandate_id) -> None:
    service = PaymentService(db_session)  # no razorpay_client — demo mode

    attempt = service.record_payment_attempt(mandate_id, amount=Decimal("500.00"))

    assert attempt.razorpay_order_id is None


def test_get_by_razorpay_order_id_resolves_the_matching_attempt(db_session: Session, mandate_id) -> None:
    fake_client = _FakeRazorpayClient(order_id="order_xyz789")
    service = PaymentService(db_session, razorpay_client=fake_client)
    attempt = service.record_payment_attempt(mandate_id, amount=Decimal("500.00"))

    resolved = service.get_by_razorpay_order_id("order_xyz789")

    assert resolved is not None
    assert resolved.id == attempt.id
    assert service.get_by_razorpay_order_id("order_does_not_exist") is None


def test_mark_payment_success_stores_the_real_razorpay_payment_id(db_session: Session, mandate_id) -> None:
    service = PaymentService(db_session)
    attempt = service.record_payment_attempt(mandate_id)

    updated = service.mark_payment_success(attempt.id, razorpay_payment_id="pay_captured123")

    assert updated.razorpay_payment_id == "pay_captured123"
    assert updated.status == PaymentStatus.SUCCEEDED


def test_mark_payment_failure_creates_a_retry_schedule_when_none_exists(db_session: Session, mandate_id) -> None:
    service = PaymentService(db_session)
    attempt = service.record_payment_attempt(mandate_id)

    service.mark_payment_failure(attempt.id)

    schedule = RetryScheduleRepository(db_session).get_by_mandate(mandate_id)
    assert schedule is not None
    assert schedule.status == RetryStatus.PENDING
    assert schedule.retry_count == 0
    assert schedule.max_retries == 3


def test_mark_payment_failure_uses_the_supplied_next_retry_at_as_the_schedules_recommended_time(db_session: Session, mandate_id) -> None:
    service = PaymentService(db_session)
    attempt = service.record_payment_attempt(mandate_id)
    next_retry_at = datetime.now(timezone.utc) + timedelta(hours=6)

    service.mark_payment_failure(attempt.id, next_retry_at=next_retry_at)

    schedule = RetryScheduleRepository(db_session).get_by_mandate(mandate_id)
    assert schedule is not None
    # SQLite (used in tests) doesn't preserve tzinfo on round-trip like Postgres does.
    assert schedule.recommended_time.replace(tzinfo=timezone.utc) == next_retry_at


def test_mark_payment_failure_leaves_an_already_active_schedule_untouched(db_session: Session, mandate_id) -> None:
    service = PaymentService(db_session)
    attempt1 = service.record_payment_attempt(mandate_id)
    service.mark_payment_failure(attempt1.id)
    schedule_after_first_failure = RetryScheduleRepository(db_session).get_by_mandate(mandate_id)

    attempt2 = service.record_payment_attempt(mandate_id)
    service.mark_payment_failure(attempt2.id)

    schedule_after_second_failure = RetryScheduleRepository(db_session).get_by_mandate(mandate_id)
    assert schedule_after_second_failure.id == schedule_after_first_failure.id
    assert schedule_after_second_failure.recommended_time == schedule_after_first_failure.recommended_time


def test_mark_payment_success_resolves_an_active_retry_schedule(db_session: Session, mandate_id) -> None:
    service = PaymentService(db_session)
    retry_repo = RetryScheduleRepository(db_session)
    failed = service.record_payment_attempt(mandate_id)
    service.mark_payment_failure(failed.id)

    recovered = service.record_payment_attempt(mandate_id)
    service.mark_payment_success(recovered.id)

    schedule = retry_repo.get_by_mandate(mandate_id)
    assert schedule is not None
    assert schedule.status == RetryStatus.EXECUTED


def test_mark_payment_success_does_nothing_when_no_retry_schedule_exists(db_session: Session, mandate_id) -> None:
    service = PaymentService(db_session)
    attempt = service.record_payment_attempt(mandate_id)

    service.mark_payment_success(attempt.id)

    assert RetryScheduleRepository(db_session).get_by_mandate(mandate_id) is None


def test_mark_payment_failure_reactivates_an_exhausted_schedule(db_session: Session, mandate_id) -> None:
    service = PaymentService(db_session)
    retry_repo = RetryScheduleRepository(db_session)
    attempt1 = service.record_payment_attempt(mandate_id)
    service.mark_payment_failure(attempt1.id)
    exhausted = retry_repo.get_by_mandate(mandate_id)
    assert exhausted is not None
    retry_repo.update(exhausted.id, status=RetryStatus.EXHAUSTED, retry_count=3)

    attempt2 = service.record_payment_attempt(mandate_id)
    service.mark_payment_failure(attempt2.id)

    reactivated = retry_repo.get_by_mandate(mandate_id)
    assert reactivated is not None
    assert reactivated.id == exhausted.id
    assert reactivated.status == RetryStatus.PENDING
    assert reactivated.retry_count == 0
