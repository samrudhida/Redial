"""Tests for the deterministic retry-eligibility policy."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from backend.app.decision_engine.context_builder import (
    DecisionContext,
    MandateSnapshot,
    PaymentAttemptSnapshot,
    RetryScheduleSnapshot,
)
from backend.app.decision_engine.retry_strategy import is_retry_allowed

NOW = datetime(2026, 8, 28, tzinfo=timezone.utc)


def _mandate(status: str = "active") -> MandateSnapshot:
    return MandateSnapshot(
        id="mandate-1",
        customer_id="cust-1",
        mandate_reference="REF-1",
        amount=Decimal("500.00"),
        currency="INR",
        status=status,
        created_at=NOW,
        updated_at=NOW,
    )


def _attempt(status: str = "failed", decline_category: str | None = None) -> PaymentAttemptSnapshot:
    return PaymentAttemptSnapshot(
        id="attempt-1",
        attempt_number=1,
        attempted_at=NOW,
        amount=Decimal("500.00"),
        status=status,
        decline_category=decline_category,
    )


def _schedule(status: str = "pending", retry_count: int = 0, max_retries: int = 3) -> RetryScheduleSnapshot:
    return RetryScheduleSnapshot(
        id="schedule-1",
        retry_strategy="exponential_backoff",
        recommended_time=NOW,
        retry_count=retry_count,
        max_retries=max_retries,
        status=status,
    )


def test_retry_allowed_for_a_soft_decline_with_capacity_remaining() -> None:
    context = DecisionContext(
        mandate=_mandate(),
        latest_payment_attempt=_attempt(decline_category="insufficient_funds"),
        retry_schedule=_schedule(),
    )

    assert is_retry_allowed(context) is True


def test_retry_blocked_when_latest_decline_is_account_closed() -> None:
    """A closed account can never succeed on retry — no automated retry should be recommended."""
    context = DecisionContext(
        mandate=_mandate(),
        latest_payment_attempt=_attempt(decline_category="account_closed"),
        retry_schedule=_schedule(),
    )

    assert is_retry_allowed(context) is False


def test_retry_blocked_when_latest_decline_is_mandate_inactive() -> None:
    context = DecisionContext(
        mandate=_mandate(),
        latest_payment_attempt=_attempt(decline_category="mandate_inactive"),
        retry_schedule=_schedule(),
    )

    assert is_retry_allowed(context) is False


def test_retry_blocked_when_latest_decline_requires_authentication() -> None:
    context = DecisionContext(
        mandate=_mandate(),
        latest_payment_attempt=_attempt(decline_category="authentication_required"),
        retry_schedule=_schedule(),
    )

    assert is_retry_allowed(context) is False


def test_retry_blocked_when_latest_attempt_is_still_pending() -> None:
    """A retry must never be booked on top of an attempt that hasn't been
    resolved yet — that risks a duplicate real charge once a real payment
    gateway settles the still-pending attempt.
    """
    context = DecisionContext(
        mandate=_mandate(),
        latest_payment_attempt=_attempt(status="pending"),
        retry_schedule=_schedule(),
    )

    assert is_retry_allowed(context) is False


def test_retry_blocked_when_latest_attempt_is_still_processing() -> None:
    context = DecisionContext(
        mandate=_mandate(),
        latest_payment_attempt=_attempt(status="processing"),
        retry_schedule=_schedule(),
    )

    assert is_retry_allowed(context) is False
