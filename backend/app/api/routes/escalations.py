"""Thin HTTP adapters over the existing escalation service."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field

from backend.app.api.dependencies import get_escalation_service
from backend.app.models.enums import EscalationLevel
from backend.app.models.escalation import Escalation
from backend.app.services.escalation_service import EscalationService

router = APIRouter(prefix="/escalations", tags=["Escalations"])


class EscalationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    mandate_id: uuid.UUID
    escalation_level: EscalationLevel
    reason: str
    assigned_to: str | None
    resolved: bool
    resolved_at: datetime | None


class CreateEscalationRequest(BaseModel):
    mandate_id: uuid.UUID
    reason: str = Field(min_length=1)
    escalation_level: EscalationLevel = EscalationLevel.LEVEL_1
    assigned_to: str | None = None


def _response(escalation: Escalation) -> EscalationResponse:
    return EscalationResponse.model_validate(escalation)


@router.get("/{escalation_id}", response_model=EscalationResponse)
def get_escalation(escalation_id: uuid.UUID, service: EscalationService = Depends(get_escalation_service)) -> EscalationResponse:
    return _response(service.get_escalation(escalation_id))


@router.get("", response_model=list[EscalationResponse])
def list_escalations(
    mandate_id: uuid.UUID | None = Query(default=None),
    resolved: bool = Query(default=False),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    service: EscalationService = Depends(get_escalation_service),
) -> list[EscalationResponse]:
    lister = service.list_resolved_escalations if resolved else service.list_open_escalations
    return [_response(item) for item in lister(mandate_id, offset=offset, limit=limit)]


@router.post("", response_model=EscalationResponse, status_code=201)
def create_escalation(request: CreateEscalationRequest, service: EscalationService = Depends(get_escalation_service)) -> EscalationResponse:
    return _response(
        service.create_escalation(
            request.mandate_id,
            request.reason,
            escalation_level=request.escalation_level,
            assigned_to=request.assigned_to,
        )
    )


@router.patch("/{escalation_id}/resolve", response_model=EscalationResponse)
def resolve_escalation(escalation_id: uuid.UUID, service: EscalationService = Depends(get_escalation_service)) -> EscalationResponse:
    return _response(service.resolve_escalation(escalation_id))
