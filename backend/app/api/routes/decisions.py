"""Thin HTTP adapters over the existing decision (AI audit log) service."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field

from backend.app.api.dependencies import get_decision_service
from backend.app.models.decision_log import DecisionLog
from backend.app.services.decision_service import DecisionService

router = APIRouter(prefix="/decisions", tags=["Decisions"])


class DecisionLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    mandate_id: uuid.UUID
    decision_type: str
    explanation: str
    confidence_score: Decimal
    created_at: datetime


class RecordDecisionRequest(BaseModel):
    mandate_id: uuid.UUID
    decision_type: str = Field(min_length=1, max_length=100)
    explanation: str = Field(min_length=1)
    confidence_score: Decimal = Field(ge=0, le=1)


def _response(decision: DecisionLog) -> DecisionLogResponse:
    return DecisionLogResponse.model_validate(decision)


@router.get("/{decision_log_id}", response_model=DecisionLogResponse)
def get_decision(decision_log_id: uuid.UUID, service: DecisionService = Depends(get_decision_service)) -> DecisionLogResponse:
    return _response(service.get_decision(decision_log_id))


@router.get("", response_model=list[DecisionLogResponse])
def list_decisions(
    mandate_id: uuid.UUID | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    service: DecisionService = Depends(get_decision_service),
) -> list[DecisionLogResponse]:
    return [_response(item) for item in service.list_decisions(mandate_id, offset=offset, limit=limit)]


@router.post("", response_model=DecisionLogResponse, status_code=201)
def record_decision(request: RecordDecisionRequest, service: DecisionService = Depends(get_decision_service)) -> DecisionLogResponse:
    return _response(
        service.record_ai_decision(
            request.mandate_id,
            request.decision_type,
            request.explanation,
            request.confidence_score,
        )
    )
