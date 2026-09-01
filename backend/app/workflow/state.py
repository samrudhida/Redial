"""Provider-independent state passed through future workflow steps.

This module intentionally contains data and small state-transition helpers
only. It does not import LangGraph or execute any application workflow.
"""

from __future__ import annotations

from datetime import datetime, timezone
from threading import RLock
from typing import TypeAlias
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from backend.app.decision_engine.context_builder import DecisionContext
from backend.app.decision_engine.decision_engine import (
    CommunicationRecommendation,
    DecisionResult,
    EscalationRecommendation,
    RetryRecommendation,
)
from backend.app.observability.ai_trace import AITrace
from backend.app.orchestration.models import FinalDecision

JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | list[JsonScalar] | dict[str, JsonScalar]
_state_lock = RLock()


def _now() -> datetime:
    return datetime.now(timezone.utc)


class WorkflowMetadata(BaseModel):
    """Identity and progress metadata shared by every workflow execution."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    workflow_id: str = Field(default_factory=lambda: str(uuid4()))
    execution_id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)
    status: str = "created"
    current_step: str | None = None
    version: str = "1.0"


class WorkflowHistoryEntry(BaseModel):
    """Immutable, serializable record of a workflow transition or event."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    step: str
    event: str
    timestamp: datetime = Field(default_factory=_now)
    details: dict[str, JsonValue] = Field(default_factory=dict)


class WorkflowError(BaseModel):
    """Immutable normalized error record safe to carry between workflow steps."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    message: str
    code: str = "workflow_error"
    timestamp: datetime = Field(default_factory=_now)
    details: dict[str, JsonValue] = Field(default_factory=dict)


class WorkflowState(BaseModel):
    """Complete typed state contract for future graph nodes.

    The state is intentionally mutable at the workflow boundary because each
    future node will advance it. Its records are immutable, and helper methods
    serialize all transitions consistently while guarding concurrent updates.
    """

    model_config = ConfigDict(extra="forbid")

    metadata: WorkflowMetadata = Field(default_factory=WorkflowMetadata)
    decision_context: DecisionContext | None = None
    decision_result: DecisionResult | None = None
    final_decision: FinalDecision | None = None
    trace: AITrace | None = None
    retry_plan: RetryRecommendation | None = None
    communication_plan: CommunicationRecommendation | None = None
    escalation_plan: EscalationRecommendation | None = None
    history: list[WorkflowHistoryEntry] = Field(default_factory=list)
    errors: list[WorkflowError] = Field(default_factory=list)
    ai_enabled: bool = False
    metadata_map: dict[str, JsonValue] = Field(default_factory=dict)

    def add_history(self, step: str, event: str, *, details: dict[str, JsonValue] | None = None) -> None:
        """Append an immutable transition record and refresh state time."""
        with _state_lock:
            self.history.append(WorkflowHistoryEntry(step=step, event=event, details=dict(details or {})))
            self._touch_locked()

    def add_error(self, message: str, *, code: str = "workflow_error", details: dict[str, JsonValue] | None = None) -> None:
        """Append a normalized error without exposing provider-specific types."""
        with _state_lock:
            self.errors.append(WorkflowError(message=message, code=code, details=dict(details or {})))
            self._touch_locked()

    def advance_step(self, step: str, *, status: str | None = None) -> None:
        """Update the current workflow step and optionally its status."""
        with _state_lock:
            self.metadata = self.metadata.model_copy(
                update={"current_step": step, "status": status or self.metadata.status, "updated_at": _now()}
            )

    def update_timestamp(self) -> None:
        """Refresh the metadata update time without changing workflow state."""
        with _state_lock:
            self._touch_locked()

    def clear_errors(self) -> None:
        """Remove recoverable errors before a new workflow attempt."""
        with _state_lock:
            self.errors.clear()
            self._touch_locked()

    def _touch_locked(self) -> None:
        self.metadata = self.metadata.model_copy(update={"updated_at": _now()})