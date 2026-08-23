"""Deterministic escalation-routing policy for payment-retry cases."""

from __future__ import annotations

from backend.app.decision_engine.context_builder import DecisionContext
from backend.app.decision_engine.retry_strategy import remaining_retry_attempts


def determine_escalation(context: DecisionContext) -> str:
    """Return ``none``, ``merchant``, ``support``, or ``customer`` escalation.

    The strategy is intentionally deterministic and auditable. It classifies
    terminal mandate issues for merchants, infrastructure failures for support,
    exhausted recoverable attempts for customer follow-up, and all other cases
    as requiring no escalation.
    """
    attempt = context.latest_payment_attempt
    if attempt is None or attempt.status == "succeeded":
        return "none"
    if attempt.decline_category in {"account_closed", "mandate_inactive"}:
        return "merchant"
    if attempt.decline_category in {"bank_unavailable", "technical_error"}:
        return "support"
    if remaining_retry_attempts(context) == 0:
        return "customer"
    return "none"
