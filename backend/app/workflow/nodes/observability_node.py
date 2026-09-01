"""Record workflow completion metadata without changing decisions."""

from __future__ import annotations

from typing import Protocol

from backend.app.observability.ai_trace import AITraceRecorder
from backend.app.observability.metrics import record_latency
from backend.app.workflow.state import WorkflowState


class CompletionRecorderProtocol(Protocol):
    """Optional sink for workflow completion events."""

    def record_workflow_completion(self, state: WorkflowState) -> None:
        """Record completion metadata without changing business state."""


def run(
    state: WorkflowState,
    *,
    trace_recorder: AITraceRecorder | None = None,
    completion_recorder: CompletionRecorderProtocol | None = None,
) -> WorkflowState:
    """Record trace latency and completion through injected observability sinks."""
    if trace_recorder is not None and state.trace is not None and state.trace.latency_ms is not None:
        record_latency(state.trace.latency_ms)
    if completion_recorder is not None:
        completion_recorder.record_workflow_completion(state)
    state.advance_step("observability", status="completed")
    state.add_history("observability", "completed", details={"ai_used": state.final_decision.ai_used if state.final_decision else False})
    return state