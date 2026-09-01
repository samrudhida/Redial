"""Real workflow-execution observability endpoints.

Every number here is read from workflow_executions / workflow_execution_nodes
rows written by WorkflowExecutionService.persist_workflow — themselves only
ever written when the real workflow graph actually runs (see
WorkflowRunnerService). Nothing here is computed from placeholder data.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from backend.app.api.dependencies import get_workflow_execution_service
from backend.app.services.workflow_execution_service import WorkflowExecutionService

router = APIRouter(prefix="/observability", tags=["Observability"])


class OverviewResponse(BaseModel):
    workflows_executed: int
    successful_workflows: int
    failed_workflows: int
    average_execution_time_ms: float
    average_ai_latency_ms: float
    average_confidence: float
    total_ai_calls: int


class WorkflowExecutionSummaryResponse(BaseModel):
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


class WorkflowExecutionNodeResponse(BaseModel):
    node_name: str
    event: str
    started_at: datetime
    finished_at: datetime
    duration_ms: float
    success: bool
    details: dict


class WorkflowExecutionDetailResponse(BaseModel):
    execution: WorkflowExecutionSummaryResponse
    reasoning: str | None
    error_message: str | None
    failed_node: str | None
    nodes: list[WorkflowExecutionNodeResponse]


class ProviderHealthResponse(BaseModel):
    provider: str
    model: str | None
    status: str
    requests_today: int
    failures: int
    average_latency_ms: float
    average_confidence: float


class WorkflowErrorResponse(BaseModel):
    workflow_id: str
    mandate_id: uuid.UUID
    node: str | None
    exception: str
    timestamp: datetime


class MetricsResponse(BaseModel):
    average_workflow_duration_ms: float
    average_node_duration_ms: float
    decision_latency_ms: float
    communication_latency_ms: float
    escalation_latency_ms: float
    ai_latency_ms: float
    database_persistence_latency_ms: float


def _summary_response(summary) -> WorkflowExecutionSummaryResponse:
    return WorkflowExecutionSummaryResponse(
        id=summary.id,
        workflow_id=summary.workflow_id,
        mandate_id=summary.mandate_id,
        started_at=summary.started_at,
        finished_at=summary.finished_at,
        duration_ms=summary.duration_ms,
        status=summary.status,
        ai_provider=summary.ai_provider,
        ai_model=summary.ai_model,
        confidence=summary.confidence,
        retry_decision=summary.retry_decision,
        communication_decision=summary.communication_decision,
        escalation_decision=summary.escalation_decision,
    )


@router.get("/overview", response_model=OverviewResponse)
def get_overview(service: WorkflowExecutionService = Depends(get_workflow_execution_service)) -> OverviewResponse:
    overview = service.get_overview()
    return OverviewResponse(**overview.__dict__)


@router.get("/workflows", response_model=list[WorkflowExecutionSummaryResponse])
def list_workflows(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    service: WorkflowExecutionService = Depends(get_workflow_execution_service),
) -> list[WorkflowExecutionSummaryResponse]:
    return [_summary_response(item) for item in service.list_executions(offset=offset, limit=limit)]


@router.get("/workflows/{execution_id}", response_model=WorkflowExecutionDetailResponse)
def get_workflow_detail(execution_id: uuid.UUID, service: WorkflowExecutionService = Depends(get_workflow_execution_service)) -> WorkflowExecutionDetailResponse:
    detail = service.get_execution_detail(execution_id)
    return WorkflowExecutionDetailResponse(
        execution=_summary_response(detail.summary),
        reasoning=detail.reasoning,
        error_message=detail.error_message,
        failed_node=detail.failed_node,
        nodes=[
            WorkflowExecutionNodeResponse(
                node_name=node.node_name,
                event=node.event,
                started_at=node.started_at,
                finished_at=node.finished_at,
                duration_ms=node.duration_ms,
                success=node.success,
                details=node.details,
            )
            for node in detail.nodes
        ],
    )


@router.get("/provider", response_model=list[ProviderHealthResponse])
def get_provider_health(service: WorkflowExecutionService = Depends(get_workflow_execution_service)) -> list[ProviderHealthResponse]:
    return [ProviderHealthResponse(**provider.__dict__) for provider in service.get_provider_health()]


@router.get("/errors", response_model=list[WorkflowErrorResponse])
def list_errors(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    service: WorkflowExecutionService = Depends(get_workflow_execution_service),
) -> list[WorkflowErrorResponse]:
    return [WorkflowErrorResponse(**error.__dict__) for error in service.list_errors(offset=offset, limit=limit)]


@router.get("/metrics", response_model=MetricsResponse)
def get_metrics(service: WorkflowExecutionService = Depends(get_workflow_execution_service)) -> MetricsResponse:
    return MetricsResponse(**service.get_metrics().__dict__)
