"""Invoke the injected decision orchestrator and store its result."""

from __future__ import annotations

from dataclasses import replace
from typing import Protocol

from backend.app.observability.ai_trace import AITraceRecorder
from backend.app.orchestration.models import FinalDecision
from backend.app.workflow.state import WorkflowState


class DecisionOrchestratorProtocol(Protocol):
    """Minimal dependency contract required by this node."""

    def orchestrate(self, context: object) -> FinalDecision:
        """Produce one final decision from the supplied context."""
        raise NotImplementedError


def run(state: WorkflowState, *, orchestrator: DecisionOrchestratorProtocol, trace_recorder: AITraceRecorder | None = None) -> WorkflowState:
    """Call the injected orchestrator, store its result, and surface the AI trace."""
    if state.decision_context is None:
        raise ValueError("WorkflowState.decision_context is required")
    state.final_decision = orchestrator.orchestrate(state.decision_context)
    if state.final_decision.ai_used and trace_recorder is not None:
        traces = trace_recorder.traces
        if traces:
            state.trace = replace(traces[-1], confidence=state.final_decision.confidence)
    state.advance_step("decision", status="decision_ready")
    state.add_history("decision", "completed", details={"ai_used": state.final_decision.ai_used})
    return state