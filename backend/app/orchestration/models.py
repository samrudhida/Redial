"""Pydantic models shared by decision orchestration callers."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from backend.app.decision_engine.decision_engine import (
    CommunicationRecommendation,
    EscalationRecommendation,
    RetryRecommendation,
)


class FinalDecision(BaseModel):
    """Deterministic decision enriched with optional validated AI evidence."""

    model_config = ConfigDict(extra="forbid")

    retry: RetryRecommendation
    communication: CommunicationRecommendation
    escalation: EscalationRecommendation
    confidence: float = Field(ge=0, le=1)
    reasoning: str
    ai_used: bool
    trace_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)