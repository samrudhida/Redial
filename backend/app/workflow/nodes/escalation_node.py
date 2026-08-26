"""Store the escalation recommendation and create a real escalation when one is required."""

from __future__ import annotations

import uuid
from typing import Protocol

from backend.app.models.enums import EscalationLevel
from backend.app.workflow.state import WorkflowState


class EscalationServiceProtocol(Protocol):
    """Minimal dependency contract required by this node."""

    def list_open_escalations(self, mandate_id: uuid.UUID | None = None, *, offset: int = 0, limit: int = 100) -> list:
        raise NotImplementedError

    def create_escalation(self, mandate_id: uuid.UUID, reason: str, *, escalation_level: EscalationLevel = EscalationLevel.LEVEL_1, assigned_to: str | None = None) -> object:
        raise NotImplementedError


_ESCALATION_LEVELS: dict[str, EscalationLevel] = {
    "merchant": EscalationLevel.LEVEL_3,
    "support": EscalationLevel.LEVEL_2,
    "customer": EscalationLevel.LEVEL_1,
}


def run(state: WorkflowState, *, escalation_service: EscalationServiceProtocol | None = None) -> WorkflowState:
    """Store the already-selected escalation recommendation and act on it.

    Guards against duplicates: a mandate whose latest attempt keeps
    qualifying for escalation across repeated runs (e.g. a persistent
    bank-unavailable decline) must not accumulate a new Escalation row
    every time this node runs — only the first one matters operationally.
    """
    if state.final_decision is None:
        raise ValueError("WorkflowState.final_decision is required")
    plan = state.final_decision.escalation
    state.escalation_plan = plan

    if plan.required and escalation_service is not None and state.decision_context is not None:
        mandate_id = uuid.UUID(state.decision_context.mandate.id)
        already_open = escalation_service.list_open_escalations(mandate_id, limit=1)
        if not already_open:
            level = _ESCALATION_LEVELS.get(plan.escalation_type, EscalationLevel.LEVEL_1)
            escalation_service.create_escalation(mandate_id, plan.reasoning, escalation_level=level)

    state.advance_step("escalation", status="escalation_ready")
    state.add_history("escalation", "completed")
    return state
