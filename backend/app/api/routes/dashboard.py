"""Thin HTTP adapters over the dashboard aggregation service."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict

from backend.app.api.dependencies import get_dashboard_service
from backend.app.api.routes.decisions import DecisionLogResponse
from backend.app.api.routes.escalations import EscalationResponse
from backend.app.api.routes.retry_schedules import RetryScheduleResponse
from backend.app.models.enums import MandateStatus, PaymentStatus
from backend.app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


class DashboardSummaryResponse(BaseModel):
    mandate_counts_by_status: dict[MandateStatus, int]
    payment_attempt_counts_by_status: dict[PaymentStatus, int]
    revenue_recovered: Decimal
    pending_retries: int
    open_escalations: int
    recent_decisions: list[DecisionLogResponse]


class DailyTrendPointResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    day: date
    attempts_total: int
    attempts_succeeded: int
    attempts_failed: int
    collected_amount: Decimal
    recovered_amount: Decimal


@router.get("/summary", response_model=DashboardSummaryResponse)
def get_dashboard_summary(
    recent_decision_limit: int = Query(default=10, ge=1, le=100),
    service: DashboardService = Depends(get_dashboard_service),
) -> DashboardSummaryResponse:
    summary = service.get_summary(recent_decision_limit=recent_decision_limit)
    return DashboardSummaryResponse(
        mandate_counts_by_status=summary.mandate_counts_by_status,
        payment_attempt_counts_by_status=summary.payment_attempt_counts_by_status,
        revenue_recovered=summary.revenue_recovered,
        pending_retries=summary.pending_retries,
        open_escalations=summary.open_escalations,
        recent_decisions=[DecisionLogResponse.model_validate(item) for item in summary.recent_decisions],
    )


@router.get("/trend", response_model=list[DailyTrendPointResponse])
def get_dashboard_trend(
    days: int = Query(default=14, ge=1, le=90),
    service: DashboardService = Depends(get_dashboard_service),
) -> list[DailyTrendPointResponse]:
    """Real per-day payment attempt/collection/recovery figures for the last `days` days."""
    return [DailyTrendPointResponse.model_validate(point) for point in service.get_trend(days=days)]


@router.get("/retry-queue", response_model=list[RetryScheduleResponse])
def get_retry_queue(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    service: DashboardService = Depends(get_dashboard_service),
) -> list[RetryScheduleResponse]:
    return [RetryScheduleResponse.model_validate(item) for item in service.get_retry_queue(offset=offset, limit=limit)]


@router.get("/escalations", response_model=list[EscalationResponse])
def get_dashboard_escalations(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    service: DashboardService = Depends(get_dashboard_service),
) -> list[EscalationResponse]:
    return [EscalationResponse.model_validate(item) for item in service.get_open_escalations(offset=offset, limit=limit)]


class ActivityEventResponse(BaseModel):
    event_type: str
    mandate_id: uuid.UUID
    description: str
    timestamp: datetime


@router.get("/activity", response_model=list[ActivityEventResponse])
def get_dashboard_activity(
    limit: int = Query(default=20, ge=1, le=100),
    service: DashboardService = Depends(get_dashboard_service),
) -> list[ActivityEventResponse]:
    """Real recent workflow events (decisions made, communications sent), newest first."""
    return [ActivityEventResponse(event_type=event.event_type, mandate_id=event.mandate_id, description=event.description, timestamp=event.timestamp) for event in service.get_recent_activity(limit=limit)]
