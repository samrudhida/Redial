"""Validate and prepare the shared workflow context."""

from __future__ import annotations

from backend.app.workflow.state import WorkflowState


def run(state: WorkflowState) -> WorkflowState:
    """Validate state, require a decision context, and mark context prepared."""
    WorkflowState.model_validate(state.model_dump(mode="json"))
    if state.decision_context is None:
        raise ValueError("WorkflowState.decision_context is required")
    state.advance_step("context", status="context_ready")
    state.add_history("context", "validated")
    return state