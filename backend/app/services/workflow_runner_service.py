"""Composition root that actually executes the recovery workflow graph.

Before this module, backend/app/api/dependencies.py::get_workflow() always
raised 503 — nothing ever supplied WorkflowBuilder with a real
decision_orchestrator/persistence_adapter, so the LangGraph pipeline had
never been invoked anywhere in the application. This wires real, already-
existing pieces together (ContextBuilder, DecisionEngine's deterministic
policy, DecisionOrchestrator, WorkflowExecutionService as the persistence
adapter) so a workflow run is a real execution of the real graph, not a
simulation.

AI enrichment is optional (ai_service defaults to None): callers that don't
supply one (e.g. tests constructing this directly) get deterministic-only
behavior exactly as before. backend/app/api/dependencies.py::get_ai_service
builds a real Groq-backed AIService from settings and injects it here when
GROQ_API_KEY is configured; DecisionOrchestrator already handles a missing AI
service by falling back to deterministic policy.
"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from backend.app.decision_engine.context_builder import ContextBuilder
from backend.app.decision_engine.decision_engine import DecisionEngine
from backend.app.llm.ai_service import AIService
from backend.app.observability.ai_trace import AITraceRecorder
from backend.app.orchestration.decision_orchestrator import DecisionOrchestrator
from backend.app.services.communication_service import CommunicationService
from backend.app.services.decision_service import DecisionService
from backend.app.services.escalation_service import EscalationService
from backend.app.services.mandate_service import MandateService
from backend.app.services.payment_service import PaymentService
from backend.app.services.retry_service import RetryService
from backend.app.services.workflow_execution_service import WorkflowExecutionService
from backend.app.workflow.builder import WorkflowBuilder
from backend.app.workflow.state import WorkflowState


class WorkflowRunnerService:
    """Builds a session-scoped workflow graph and runs it for one mandate."""

    def __init__(self, session: Session, ai_service: AIService | None = None) -> None:
        self.session = session
        self.mandate_service = MandateService(session)
        self.payment_service = PaymentService(session)
        self.decision_service = DecisionService(session)
        self.retry_service = RetryService(session)
        self.communication_service = CommunicationService(session)
        self.escalation_service = EscalationService(session)
        self.execution_service = WorkflowExecutionService(session)

        self.context_builder = ContextBuilder(self.mandate_service, self.payment_service, self.decision_service)
        # DecisionEngine._build_result(context) is exactly the deterministic
        # evaluator DecisionOrchestrator expects (Callable[[DecisionContext],
        # DecisionResult]) — reused directly rather than re-implementing the
        # retry/communication/escalation policy it already owns.
        decision_engine = DecisionEngine(self.context_builder)
        orchestrator = DecisionOrchestrator(
            deterministic_evaluator=lambda context: decision_engine._build_result(context),  # noqa: SLF001
            ai_service=ai_service,
        )
        # Share one recorder between AIService and the workflow so decision_node
        # can surface the same AITrace it recorded onto WorkflowState.trace.
        trace_recorder = AITraceRecorder()
        if ai_service is not None:
            ai_service.recorder = trace_recorder
        self._graph = WorkflowBuilder(
            decision_orchestrator=orchestrator,  # type: ignore[arg-type]
            persistence_adapter=self.execution_service,
            trace_recorder=trace_recorder,
            payment_service=self.payment_service,
            retry_service=self.retry_service,
            communication_service=self.communication_service,
            escalation_service=self.escalation_service,
        ).build()

    def run_for_mandate(self, mandate_id: uuid.UUID) -> WorkflowState:
        """Run the real workflow graph for one mandate and return its final state.

        On success, persistence already happened inside the graph
        (persistence_node -> WorkflowExecutionService.persist_workflow). On
        failure, this still persists a "failed" execution with whatever
        node history accumulated before the exception, so failed runs are
        just as observable as successful ones.
        """
        retry_schedule = self.retry_service.get_retry_schedule_for_mandate(mandate_id)
        communications = self.communication_service.list_communications(mandate_id, limit=20)
        context = self.context_builder.build_for_mandate(mandate_id, retry_schedule=retry_schedule, communication_history=communications)
        state = WorkflowState(decision_context=context)

        try:
            finished_state = self._graph.invoke(state)
            # persistence_node already wrote a row mid-graph, but at that
            # point state.history is missing its own and observability's
            # entries — persist again now that the full node timeline exists.
            self.execution_service.persist_workflow(finished_state)
            final_decision = finished_state.final_decision
            if final_decision is not None and final_decision.ai_used:
                self.decision_service.record_ai_decision(
                    mandate_id,
                    decision_type="retry_decision",
                    explanation=final_decision.reasoning,
                    confidence_score=final_decision.confidence,
                )
            return finished_state
        except Exception as exc:
            self.session.rollback()  # clear any partial DB state left by the failure before persisting it
            state.metadata = state.metadata.model_copy(update={"status": "failed"})
            state.add_error(str(exc), code="workflow_execution_error")
            self.execution_service.persist_workflow(state)
            raise
