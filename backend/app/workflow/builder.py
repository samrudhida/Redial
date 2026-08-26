"""Dependency-injected construction of the Redial LangGraph workflow."""

from __future__ import annotations

from threading import RLock
from typing import ClassVar

from langgraph.graph import END, START, StateGraph

from backend.app.observability.ai_trace import AITraceRecorder
from backend.app.workflow.graph import WorkflowGraph
from backend.app.workflow.nodes import communication_node, context_node, decision_node, escalation_node, observability_node, persistence_node
from backend.app.workflow.state import WorkflowState


class WorkflowBuilder:
    """Construct a reusable compiled graph from injected runtime components."""

    _singleton: ClassVar[WorkflowBuilder | None] = None
    _singleton_lock: ClassVar[RLock] = RLock()

    def __init__(
        self,
        *,
        decision_orchestrator: decision_node.DecisionOrchestratorProtocol,
        persistence_adapter: persistence_node.PersistenceServiceProtocol,
        observability_adapter: observability_node.CompletionRecorderProtocol | None = None,
        trace_recorder: AITraceRecorder | None = None,
        payment_service: persistence_node.PaymentServiceProtocol | None = None,
        retry_service: persistence_node.RetryServiceProtocol | None = None,
        communication_service: communication_node.CommunicationServiceProtocol | None = None,
        escalation_service: escalation_node.EscalationServiceProtocol | None = None,
    ) -> None:
        self._decision_orchestrator = decision_orchestrator
        self._persistence_adapter = persistence_adapter
        self._observability_adapter = observability_adapter
        self._trace_recorder = trace_recorder
        self._payment_service = payment_service
        self._retry_service = retry_service
        self._communication_service = communication_service
        self._escalation_service = escalation_service
        self._workflow: WorkflowGraph | None = None
        self._build_lock = RLock()

    @classmethod
    def get_instance(
        cls,
        *,
        decision_orchestrator: decision_node.DecisionOrchestratorProtocol,
        persistence_adapter: persistence_node.PersistenceServiceProtocol,
        observability_adapter: observability_node.CompletionRecorderProtocol | None = None,
        trace_recorder: AITraceRecorder | None = None,
        payment_service: persistence_node.PaymentServiceProtocol | None = None,
        retry_service: persistence_node.RetryServiceProtocol | None = None,
        communication_service: communication_node.CommunicationServiceProtocol | None = None,
        escalation_service: escalation_node.EscalationServiceProtocol | None = None,
    ) -> WorkflowBuilder:
        """Return the lazily created process-local builder singleton."""
        with cls._singleton_lock:
            if cls._singleton is None:
                cls._singleton = cls(
                    decision_orchestrator=decision_orchestrator,
                    persistence_adapter=persistence_adapter,
                    observability_adapter=observability_adapter,
                    trace_recorder=trace_recorder,
                    payment_service=payment_service,
                    retry_service=retry_service,
                    communication_service=communication_service,
                    escalation_service=escalation_service,
                )
            return cls._singleton

    def build(self) -> WorkflowGraph:
        """Construct, compile, and return a reusable workflow facade."""
        with self._build_lock:
            if self._workflow is not None:
                return self._workflow

            self._workflow = self._compile_workflow()
            return self._workflow

    def _compile_workflow(self) -> WorkflowGraph:
        """Construct and compile the fixed workflow topology once."""
        def run_context(state: WorkflowState) -> WorkflowState:
            return context_node.run(state)

        def run_communication(state: WorkflowState) -> WorkflowState:
            return communication_node.run(state, communication_service=self._communication_service)

        def run_escalation(state: WorkflowState) -> WorkflowState:
            return escalation_node.run(state, escalation_service=self._escalation_service)

        def run_decision(state: WorkflowState) -> WorkflowState:
            return decision_node.run(state, orchestrator=self._decision_orchestrator, trace_recorder=self._trace_recorder)

        def run_persistence(state: WorkflowState) -> WorkflowState:
            return persistence_node.run(state, service=self._persistence_adapter, payment_service=self._payment_service, retry_service=self._retry_service)

        def run_observability(state: WorkflowState) -> WorkflowState:
            return observability_node.run(
                state,
                trace_recorder=self._trace_recorder,
                completion_recorder=self._observability_adapter,
            )

        graph = StateGraph(WorkflowState)

        graph.add_node("context", run_context)
        graph.add_node("decision", run_decision)
        graph.add_node("communication", run_communication)
        graph.add_node("escalation", run_escalation)
        graph.add_node("persistence", run_persistence)
        graph.add_node("observability", run_observability)

        graph.add_edge(START, "context")
        graph.add_edge("context", "decision")
        graph.add_edge("decision", "communication")
        graph.add_edge("communication", "escalation")
        graph.add_edge("escalation", "persistence")
        graph.add_edge("persistence", "observability")
        graph.add_edge("observability", END)
        return WorkflowGraph(graph.compile())
