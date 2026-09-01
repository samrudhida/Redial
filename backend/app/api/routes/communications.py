"""Thin HTTP adapters over the existing communication service."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from backend.app.api.dependencies import get_communication_service
from backend.app.models.communication import Communication
from backend.app.models.enums import CommunicationChannel, DeliveryStatus
from backend.app.services.communication_service import CommunicationService

router = APIRouter(prefix="/communications", tags=["Communications"])


class CommunicationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    mandate_id: uuid.UUID
    channel: CommunicationChannel
    template_name: str | None
    message: str
    sent_at: datetime
    delivery_status: DeliveryStatus


class RecordCommunicationRequest(BaseModel):
    mandate_id: uuid.UUID
    message: str = Field(min_length=1)
    template_name: str | None = None


class UpdateDeliveryStatusRequest(BaseModel):
    delivery_status: DeliveryStatus


_RECORDERS = {
    CommunicationChannel.SMS: "record_sms",
    CommunicationChannel.EMAIL: "record_email",
    CommunicationChannel.WHATSAPP: "record_whatsapp",
}


def _response(communication: Communication) -> CommunicationResponse:
    return CommunicationResponse.model_validate(communication)


@router.get("/{communication_id}", response_model=CommunicationResponse)
def get_communication(communication_id: uuid.UUID, service: CommunicationService = Depends(get_communication_service)) -> CommunicationResponse:
    return _response(service.get_communication(communication_id))


@router.get("", response_model=list[CommunicationResponse])
def list_communications(
    mandate_id: uuid.UUID | None = Query(default=None),
    channel: CommunicationChannel | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    service: CommunicationService = Depends(get_communication_service),
) -> list[CommunicationResponse]:
    communications = service.list_communications(mandate_id, channel=channel, offset=offset, limit=limit)
    return [_response(item) for item in communications]


@router.post("/{channel}", response_model=CommunicationResponse, status_code=201)
def record_communication(channel: CommunicationChannel, request: RecordCommunicationRequest, service: CommunicationService = Depends(get_communication_service)) -> CommunicationResponse:
    recorder_name = _RECORDERS.get(channel)
    if recorder_name is None:
        raise HTTPException(status_code=422, detail="Unsupported communication channel")
    recorder = getattr(service, recorder_name)
    return _response(recorder(request.mandate_id, request.message, template_name=request.template_name))


@router.patch("/{communication_id}/delivery-status", response_model=CommunicationResponse)
def update_delivery_status(communication_id: uuid.UUID, request: UpdateDeliveryStatusRequest, service: CommunicationService = Depends(get_communication_service)) -> CommunicationResponse:
    return _response(service.update_delivery_status(communication_id, request.delivery_status))
