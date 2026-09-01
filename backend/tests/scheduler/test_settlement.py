"""Tests for the dev-mode settlement job: resolves stale pending/processing
payment attempts so Recovery rate and related metrics reflect real, ongoing
movement even when no real payment gateway ever calls back to resolve them.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from backend.app.models.enums import PaymentStatus
from backend.app.scheduler.settlement import settle_pending_payments
from backend.app.services.mandate_service import MandateService
from backend.app.services.payment_service import PaymentService


def _make_stale_pending_attempt(db_session: Session, reference: str, *, minutes_old: int = 5):
    mandate_service = MandateService(db_session)
    payment_service = PaymentService(db_session)
    mandate = mandate_service.register_mandate(f"cust-{reference}", reference, Decimal("500.00"))
    attempt = payment_service.record_payment_attempt(mandate.id, attempted_at=datetime.now(timezone.utc) - timedelta(minutes=minutes_old))
    return mandate, attempt


def test_settle_pending_payments_resolves_a_stale_pending_attempt(db_session: Session) -> None:
    _, attempt = _make_stale_pending_attempt(db_session, "SETTLE-REF-1")
    attempt_id = attempt.id  # snapshot before the job closes the shared test session

    result = settle_pending_payments(session_factory=lambda: db_session, settle_after=timedelta(minutes=2), success_rate=1.0)

    assert result.settled == 1
    resolved = PaymentService(db_session).get_attempt(attempt_id)
    assert resolved.status == PaymentStatus.SUCCEEDED


def test_settle_pending_payments_can_resolve_to_failure(db_session: Session) -> None:
    _, attempt = _make_stale_pending_attempt(db_session, "SETTLE-REF-2")
    attempt_id = attempt.id

    result = settle_pending_payments(session_factory=lambda: db_session, settle_after=timedelta(minutes=2), success_rate=0.0)

    assert result.settled == 1
    resolved = PaymentService(db_session).get_attempt(attempt_id)
    assert resolved.status == PaymentStatus.FAILED
    assert resolved.decline_category is not None


def test_settle_pending_payments_ignores_attempts_that_are_not_stale_yet(db_session: Session) -> None:
    _make_stale_pending_attempt(db_session, "SETTLE-REF-3", minutes_old=0)

    result = settle_pending_payments(session_factory=lambda: db_session, settle_after=timedelta(minutes=2), success_rate=1.0)

    assert result.settled == 0
