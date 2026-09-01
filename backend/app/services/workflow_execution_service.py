"""Persists real workflow execution history and serves the observability reads.

``persist_workflow`` is the concrete implementation of
backend/app/workflow/nodes/persistence_node.PersistenceServiceProtocol — it
turns the WorkflowState a real graph run produces (WorkflowMetadata,
WorkflowHistoryEntry entries, FinalDecision, WorkflowError) into real rows,
so every number the observability API reports traces back to an actual
execution of the actual workflow graph.

Aggregations are computed in Python over the (small, bounded) set of
execution rows rather than with dialect-specific SQL — this codebase runs
against both SQLite (tests) and PostgreSQL (dev), and datetime-arithmetic
functions differ between them.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from backend.app.config.settings import get_settings
from backend.app.core.exceptions import NotFoundError
from backend.app.models.workflow_execution import WorkflowExecution, WorkflowExecutionNode
from backend.app.observability.metrics import average_latency as ai_average_latency
from backend.app.observability.metrics import failure_count as ai_failure_count
from backend.app.repositories.workflow_execution_repository import WorkflowExecutionRepository
from backend.app.workflow.state import WorkflowState

# Fixed, linear node order compiled into backend/app/workflow/builder.py.
NODE_SEQUENCE = ["context", "decision", "communication", "escalation", "persistence", "observability"]


def _duration_ms(started_at: datetime, finished_at: datetime | None) -> float | None:
    if finished_at is None:
        return None
    return max(0.0, (finished_at - started_at).total_seconds() * 1000)


def _average(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


@dataclass
class ObservabilityOverview:
    workflows_executed: int = 0
    successful_workflows: int = 0
    failed_workflows: int = 0
    average_execution_time_ms: float = 0.0
    average_ai_latency_ms: float = 0.0
    average_confidence: float = 0.0
    total_ai_calls: int = 0


@dataclass
class WorkflowExecutionSummary:
    id: uuid.UUID
    workflow_id: str
    mandate_id: uuid.UUID
    started_at: datetime
    finished_at: datetime | None
    duration_ms: float | None
    status: str
    ai_provider: str | None
    ai_model: str | None
    confidence: Decimal | None
    retry_decision: str | None
    communication_decision: str | None
    escalation_decision: str | None


@dataclass
class WorkflowExecutionNodeDetail:
    node_name: str
    event: str
    started_at: datetime
    finished_at: datetime
    duration_ms: float
    success: bool
    details: dict


@dataclass
class WorkflowExecutionDetail:
    summary: WorkflowExecutionSummary
    reasoning: str | None
    error_message: str | None
    failed_node: str | None
    nodes: list[WorkflowExecutionNodeDetail] = field(default_factory=list)


@dataclass
class ProviderHealth:
    provider: str
    model: str | None
    status: str
    requests_today: int
    failures: int
    average_latency_ms: float
    average_confidence: float


@dataclass
class WorkflowErrorEntry:
    workflow_id: str
    mandate_id: uuid.UUID
    node: str | None
    exception: str
    timestamp: datetime


@dataclass
class ObservabilityMetrics:
    average_workflow_duration_ms: float = 0.0
    average_node_duration_ms: float = 0.0
    decision_latency_ms: float = 0.0
    communication_latency_ms: float = 0.0
    escalation_latency_ms: float = 0.0
    ai_latency_ms: float = 0.0
    database_persistence_latency_ms: float = 0.0


def _to_summary(execution: WorkflowExecution) -> WorkflowExecutionSummary:
    return WorkflowExecutionSummary(
        id=execution.id,
        workflow_id=execution.workflow_id,
        mandate_id=execution.mandate_id,
        started_at=execution.started_at,
        finished_at=execution.finished_at,
        duration_ms=_duration_ms(execution.started_at, execution.finished_at),
        status=execution.status,
        ai_provider=execution.ai_provider,
        ai_model=execution.ai_model,
        confidence=execution.confidence,
        retry_decision=("allowed" if execution.retry_allowed else "not allowed") if execution.retry_allowed is not None else None,
        communication_decision=execution.communication_channel,
        escalation_decision=execution.escalation_type,
    )


class WorkflowExecutionService:
    """Implements PersistenceServiceProtocol and serves observability reads."""

    def __init__(self, session: Session, repository: WorkflowExecutionRepository | None = None) -> None:
        self.session = session
        self.executions = repository or WorkflowExecutionRepository(session)

    # ------------------------------------------------------------------ #
    # PersistenceServiceProtocol
    # ------------------------------------------------------------------ #

    def persist_workflow(self, state: WorkflowState) -> None:
        """Write one real execution + its real node timeline from a finished WorkflowState."""
        if state.decision_context is None:
            raise ValueError("Cannot persist a workflow execution without a decision context")

        final = state.final_decision
        trace = state.trace
        status = "failed" if state.errors else "completed"
        failed_node = NODE_SEQUENCE[len(state.history)] if state.errors and len(state.history) < len(NODE_SEQUENCE) else None
        execution_id = uuid.UUID(state.metadata.execution_id)

        fields = {
            "workflow_id": state.metadata.workflow_id,
            "mandate_id": uuid.UUID(state.decision_context.mandate.id),
            "status": status,
            "started_at": state.metadata.created_at,
            "finished_at": state.metadata.updated_at,
            "ai_provider": trace.provider if trace else None,
            "ai_model": trace.model if trace else None,
            "ai_used": final.ai_used if final else False,
            "confidence": Decimal(str(final.confidence)) if final else None,
            "retry_allowed": final.retry.allowed if final else None,
            "retry_priority": final.retry.priority if final else None,
            "communication_channel": final.communication.channel if final else None,
            "escalation_type": final.escalation.escalation_type if final else None,
            "reasoning": final.reasoning if final else None,
            "error_message": state.errors[-1].message if state.errors else None,
            "failed_node": failed_node,
        }

        # persistence_node calls this mid-graph, before its own and
        # observability's history entries exist yet — and the runner calls it
        # again once the full graph has finished, when state.history is
        # actually complete. Upserting (rather than a plain insert) keeps both
        # calls safe and leaves the row reflecting the most complete state.
        execution = self.session.get(WorkflowExecution, execution_id)
        if execution is None:
            execution = WorkflowExecution(id=execution_id, **fields)
            self.session.add(execution)
        else:
            for field_name, value in fields.items():
                setattr(execution, field_name, value)
            for node in list(execution.nodes):
                self.session.delete(node)
        self.session.flush()

        previous_timestamp = state.metadata.created_at
        for entry in state.history:
            self.session.add(
                WorkflowExecutionNode(
                    execution_id=execution.id,
                    node_name=entry.step,
                    event=entry.event,
                    started_at=previous_timestamp,
                    finished_at=entry.timestamp,
                    success=True,
                    details=entry.details,
                )
            )
            previous_timestamp = entry.timestamp

        self.session.commit()

    def persist_failed_execution(self, mandate_id: uuid.UUID, error_message: str) -> None:
        """Write a minimal failed execution row for a failure that happened
        before the workflow graph could even start (e.g. the retry-schedule
        lookup or context assembly itself raised, so no WorkflowState/
        DecisionContext ever existed to pass to persist_workflow). Without
        this, such a failure is invisible to GET /observability/errors and
        the overview's failed_workflows count forever, no matter how many
        times it happens — it would only ever show up in application logs.
        """
        now = datetime.now(timezone.utc)
        self.session.add(
            WorkflowExecution(
                id=uuid.uuid4(),
                workflow_id=str(uuid.uuid4()),
                mandate_id=mandate_id,
                status="failed",
                started_at=now,
                finished_at=now,
                error_message=error_message,
                failed_node="context",
            )
        )
        self.session.commit()

    # ------------------------------------------------------------------ #
    # Reads
    # ------------------------------------------------------------------ #

    def get_overview(self) -> ObservabilityOverview:
        executions = self.executions.list_all_for_aggregation()
        durations = [d for e in executions if (d := _duration_ms(e.started_at, e.finished_at)) is not None]
        ai_calls = [e for e in executions if e.ai_used]
        # Deterministic-only runs always persist confidence=0.0 as a documented
        # placeholder (see persist_workflow) — including them here would dilute
        # "how confident was the AI" with runs the AI never touched. Only count
        # ai_used executions, matching get_provider_health()'s average below.
        confidences = [float(e.confidence) for e in ai_calls if e.confidence is not None]
        return ObservabilityOverview(
            workflows_executed=len(executions),
            successful_workflows=sum(1 for e in executions if e.status == "completed"),
            failed_workflows=sum(1 for e in executions if e.status == "failed"),
            average_execution_time_ms=_average(durations),
            average_ai_latency_ms=ai_average_latency(),
            average_confidence=_average(confidences),
            total_ai_calls=len(ai_calls),
        )

    def list_executions(self, *, offset: int = 0, limit: int = 100) -> list[WorkflowExecutionSummary]:
        return [_to_summary(execution) for execution in self.executions.list_recent(offset=offset, limit=limit)]

    def get_execution_detail(self, execution_id: uuid.UUID) -> WorkflowExecutionDetail:
        execution = self.executions.get_with_nodes(execution_id)
        if execution is None:
            raise NotFoundError("Workflow execution not found")
        nodes = [
            WorkflowExecutionNodeDetail(
                node_name=node.node_name,
                event=node.event,
                started_at=node.started_at,
                finished_at=node.finished_at,
                duration_ms=_duration_ms(node.started_at, node.finished_at) or 0.0,
                success=node.success,
                details=node.details,
            )
            for node in execution.nodes
        ]
        return WorkflowExecutionDetail(
            summary=_to_summary(execution),
            reasoning=execution.reasoning,
            error_message=execution.error_message,
            failed_node=execution.failed_node,
            nodes=nodes,
        )

    def get_provider_health(self) -> list[ProviderHealth]:
        """Reports the real configured provider (from settings), real AI-usage
        counts from execution rows, and real failure/latency counters recorded
        live by every AIService call (backend.app.observability.metrics). When
        no API key is configured, every execution's ai_used is honestly False
        (the orchestrator never even attempts an AI call — see
        DecisionOrchestrator.orchestrate) rather than representing a failed
        request, so failures stays 0 in that case.
        """
        settings = get_settings()
        executions = self.executions.list_all_for_aggregation()
        configured = bool(settings.GROQ_API_KEY)
        ai_used_executions = [e for e in executions if e.ai_used]
        confidences = [float(e.confidence) for e in ai_used_executions if e.confidence is not None]
        status = "not_configured" if not configured else ("healthy" if ai_used_executions else "idle")
        return [
            ProviderHealth(
                provider="groq",
                model=settings.GROQ_MODEL,
                status=status,
                requests_today=len(ai_used_executions),
                failures=ai_failure_count(),
                average_latency_ms=ai_average_latency(),
                average_confidence=_average(confidences),
            )
        ]

    def list_errors(self, *, offset: int = 0, limit: int = 100) -> list[WorkflowErrorEntry]:
        failed = self.executions.list_failed(offset=offset, limit=limit)
        return [
            WorkflowErrorEntry(
                workflow_id=execution.workflow_id,
                mandate_id=execution.mandate_id,
                node=execution.failed_node,
                exception=execution.error_message or "Unknown error",
                timestamp=execution.finished_at or execution.started_at,
            )
            for execution in failed
        ]

    def get_metrics(self) -> ObservabilityMetrics:
        executions = self.executions.list_all_for_aggregation()
        node_durations_by_name: dict[str, list[float]] = {name: [] for name in NODE_SEQUENCE}
        all_node_durations: list[float] = []

        for execution in executions:
            for node in execution.nodes:
                duration = _duration_ms(node.started_at, node.finished_at)
                if duration is None:
                    continue
                all_node_durations.append(duration)
                node_durations_by_name.setdefault(node.node_name, []).append(duration)

        workflow_durations = [d for e in executions if (d := _duration_ms(e.started_at, e.finished_at)) is not None]

        return ObservabilityMetrics(
            average_workflow_duration_ms=_average(workflow_durations),
            average_node_duration_ms=_average(all_node_durations),
            decision_latency_ms=_average(node_durations_by_name.get("decision", [])),
            communication_latency_ms=_average(node_durations_by_name.get("communication", [])),
            escalation_latency_ms=_average(node_durations_by_name.get("escalation", [])),
            ai_latency_ms=ai_average_latency(),
            database_persistence_latency_ms=_average(node_durations_by_name.get("persistence", [])),
        )
