"""Pydantic v2 schemas for normalized, provider-independent AI outputs."""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AIResponse(BaseModel):
    """Common validated fields returned by all AI decision workflows."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    decision: Annotated[str, Field(min_length=1, max_length=500)]
    confidence: Annotated[float, Field(ge=0, le=1)]
    reasoning: Annotated[str, Field(min_length=1, max_length=10_000)]
    recommended_action: Annotated[str, Field(min_length=1, max_length=2_000)]
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("confidence")
    @classmethod
    def confidence_must_be_finite(cls, value: float) -> float:
        """Reject non-finite confidence values that cannot be trusted downstream."""
        if value != value or value in (float("inf"), float("-inf")):
            raise ValueError("confidence must be a finite number")
        return value


class RetryDecision(AIResponse):
    """Structured recommendation for a failed mandate payment retry."""


class CommunicationSuggestion(AIResponse):
    """Structured customer-facing communication recommendation."""

    message: Annotated[str, Field(min_length=1, max_length=5_000)]


class EscalationDecision(AIResponse):
    """Structured recommendation for whether and how to escalate a case."""
