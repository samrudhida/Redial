"""Deterministic retry-policy calculations independent of any LLM provider."""

from __future__ import annotations

from datetime import datetime

from backend.app.decision_engine.context_builder import DecisionContext


def remaining_retry_attempts(context: DecisionContext) -> int:
    """Return the non-negative retry capacity available in the current schedule."""
    if context.retry_schedule is None:
        return 0
    return max(context.retry_schedule.max_retries - context.retry_schedule.retry_count, 0)


def is_retry_allowed(context: DecisionContext) -> bool:
    """Determine whether mandate and retry-plan state permit another payment retry."""
    if context.mandate.status != "active" or context.retry_schedule is None:
        return False
    if context.retry_schedule.status not in {"pending", "scheduled"}:
        return False
    if context.latest_payment_attempt and context.latest_payment_attempt.status == "succeeded":
        return False
    return remaining_retry_attempts(context) > 0


def calculate_retry_priority(context: DecisionContext) -> str:
    """Classify retry urgency using only mandate, attempt, and capacity facts."""
    if not is_retry_allowed(context):
        return "none"
    attempt = context.latest_payment_attempt
    if attempt is None:
        return "normal"
    if attempt.decline_category in {"bank_unavailable", "technical_error"}:
        return "high"
    if remaining_retry_attempts(context) == 1:
        return "high"
    return "normal"


def calculate_retry_window(context: DecisionContext) -> datetime | None:
    """Return the configured retry window when a retry is currently allowed."""
    if not is_retry_allowed(context):
        return None
    if context.latest_payment_attempt and context.latest_payment_attempt.next_retry_at is not None:
        return context.latest_payment_attempt.next_retry_at
    return context.retry_schedule.recommended_time if context.retry_schedule else None
