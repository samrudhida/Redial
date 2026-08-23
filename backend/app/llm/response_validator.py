"""Defence-in-depth validation for structured AI response objects."""

from __future__ import annotations

import math
from typing import TypeVar

from backend.app.llm.schemas import AIResponse, CommunicationSuggestion, EscalationDecision, RetryDecision

ResponseT = TypeVar("ResponseT", bound=AIResponse)


class AIResponseValidationError(ValueError):
    """Raised when a parsed AI response fails safety or completeness checks."""


def validate_retry_decision(response: RetryDecision) -> RetryDecision:
    """Validate that a retry decision is complete and safe for downstream use."""
    return _validate_response(response)


def validate_communication_suggestion(response: CommunicationSuggestion) -> CommunicationSuggestion:
    """Validate that a communication suggestion includes a customer message."""
    _validate_response(response)
    if not response.message.strip():
        raise AIResponseValidationError("communication message is required")
    return response


def validate_escalation_decision(response: EscalationDecision) -> EscalationDecision:
    """Validate that an escalation decision is complete and safe to consume."""
    return _validate_response(response)


def _validate_response(response: ResponseT) -> ResponseT:
    """Apply response rules independent of a provider's JSON formatting."""
    if not response.decision.strip():
        raise AIResponseValidationError("decision is required")
    if not math.isfinite(response.confidence) or not 0 <= response.confidence <= 1:
        raise AIResponseValidationError("confidence must be a finite value between 0 and 1")
    if not response.reasoning.strip():
        raise AIResponseValidationError("reasoning is required")
    if not response.recommended_action.strip():
        raise AIResponseValidationError("recommended_action is required")
    return response
