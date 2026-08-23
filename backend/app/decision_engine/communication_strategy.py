"""Deterministic channel-selection policy for customer communications."""

from __future__ import annotations

from backend.app.decision_engine.context_builder import DecisionContext
from backend.app.decision_engine.retry_strategy import remaining_retry_attempts


def determine_communication_channel(context: DecisionContext) -> str:
    """Select ``sms``, ``email``, ``whatsapp``, or ``none`` from case facts.

    Terminal or exhausted cases use email for a more detailed record. Repeated
    temporary failures prefer WhatsApp; an initial eligible retry uses SMS.
    No communication is recommended after a successful payment or before any
    payment attempt exists.
    """
    attempt = context.latest_payment_attempt
    if attempt is None or attempt.status == "succeeded":
        return "none"
    if attempt.decline_category in {"account_closed", "mandate_inactive"}:
        return "email"
    if remaining_retry_attempts(context) == 0:
        return "email"
    if context.retry_schedule and context.retry_schedule.retry_count >= 2:
        return "whatsapp"
    return "sms"
