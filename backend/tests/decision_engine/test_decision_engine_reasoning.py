"""Tests for DecisionEngine's retry reasoning text on terminal decline categories."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import cast

from backend.app.decision_engine.context_builder import (
    ContextBuilder,
    DecisionContext,
    MandateSnapshot,
    PaymentAttemptSnapshot,
    RetryScheduleSnapshot,
)
from backend.app.decision_engine.decision_engine import DecisionEngine

NOW = datetime(2026, 8, 28, tzinfo=timezone.utc)


def _context(decline_category: str) -> DecisionContext:
    return DecisionContext(
        mandate=MandateSnapshot(
            id="mandate-1", customer_id="cust-1", mandate_reference="REF-1",
            amount=Decimal("500.00"), currency="INR", status="active",
            created_at=NOW, updated_at=NOW,
        ),
        latest_payment_attempt=PaymentAttemptSnapshot(
            id="attempt-1", attempt_number=1, attempted_at=NOW,
            amount=Decimal("500.00"), status="failed", decline_category=decline_category,
        ),
        retry_schedule=RetryScheduleSnapshot(
            id="schedule-1", retry_strategy="exponential_backoff", recommended_time=NOW,
            retry_count=0, max_retries=3, status="pending",
        ),
    )


def test_reasoning_names_the_terminal_decline_category_when_retry_is_blocked() -> None:
    engine = DecisionEngine(context_builder=cast(ContextBuilder, None))

    result = engine._build_result(_context("account_closed"))

    assert result.retry.allowed is False
    assert "account_closed" in result.retry.reasoning
    assert "no further automated retries" in result.retry.reasoning.lower()


def test_reasoning_explains_an_unresolved_attempt_blocks_retry() -> None:
    engine = DecisionEngine(context_builder=cast(ContextBuilder, None))
    context = DecisionContext(
        mandate=MandateSnapshot(
            id="mandate-1", customer_id="cust-1", mandate_reference="REF-1",
            amount=Decimal("500.00"), currency="INR", status="active",
            created_at=NOW, updated_at=NOW,
        ),
        latest_payment_attempt=PaymentAttemptSnapshot(
            id="attempt-1", attempt_number=1, attempted_at=NOW,
            amount=Decimal("500.00"), status="pending",
        ),
        retry_schedule=RetryScheduleSnapshot(
            id="schedule-1", retry_strategy="exponential_backoff", recommended_time=NOW,
            retry_count=0, max_retries=3, status="pending",
        ),
    )

    result = engine._build_result(context)

    assert result.retry.allowed is False
    assert "pending" in result.retry.reasoning.lower()
    assert "unresolved" in result.retry.reasoning.lower() or "not yet resolved" in result.retry.reasoning.lower()
