"""Thin HTTP adapters over the existing mandate service."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, ConfigDict, Field

from backend.app.api.dependencies import get_mandate_service
from backend.app.models.enums import MandateStatus
from backend.app.models.mandate import Mandate
from backend.app.services.mandate_service import MandateService

router = APIRouter(prefix="/mandates", tags=["Mandates"])


class MandateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    customer_id: str
    mandate_reference: str
    amount: Decimal
    currency: str
    bank_name: str | None
    account_last4: str | None
    status: MandateStatus
    created_at: datetime
    updated_at: datetime


class MandateCreateRequest(BaseModel):
    customer_id: str = Field(min_length=1, max_length=255)
    mandate_reference: str = Field(min_length=1, max_length=255)
    amount: Decimal = Field(gt=0)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    bank_name: str | None = Field(default=None, max_length=255)
    account_last4: str | None = Field(default=None, min_length=4, max_length=4)


class MandatePatchRequest(BaseModel):
    status: MandateStatus


def _response(mandate: Mandate) -> MandateResponse:
    return MandateResponse.model_validate(mandate)


@router.get("/{mandate_id}", response_model=MandateResponse)
def get_mandate(mandate_id: uuid.UUID, service: MandateService = Depends(get_mandate_service)) -> MandateResponse:
    return _response(service.get_mandate(mandate_id))


@router.get("", response_model=list[MandateResponse])
def list_mandates(
    service: MandateService = Depends(get_mandate_service),
    status_filter: MandateStatus | None = Query(default=None, alias="status"),
    customer_id: str | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
) -> list[MandateResponse]:
    mandates = service.list_mandates(status=status_filter, customer_id=customer_id, offset=offset, limit=limit)
    return [_response(item) for item in mandates]


@router.post("", response_model=MandateResponse, status_code=status.HTTP_201_CREATED)
def create_mandate(request: MandateCreateRequest, service: MandateService = Depends(get_mandate_service)) -> MandateResponse:
    return _response(service.register_mandate(**request.model_dump()))


@router.patch("/{mandate_id}", response_model=MandateResponse)
def update_mandate(mandate_id: uuid.UUID, request: MandatePatchRequest, service: MandateService = Depends(get_mandate_service)) -> MandateResponse:
    transitions = {
        MandateStatus.ACTIVE: service.activate_mandate,
        MandateStatus.PAUSED: service.pause_mandate,
        MandateStatus.CANCELLED: service.cancel_mandate,
    }
    transition = transitions.get(request.status)
    if transition is None:
        raise HTTPException(status_code=422, detail="Only active, paused, and cancelled lifecycle transitions are supported")
    return _response(transition(mandate_id))


@router.delete("/{mandate_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_mandate(mandate_id: uuid.UUID, service: MandateService = Depends(get_mandate_service)) -> Response:
    service.cancel_mandate(mandate_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)