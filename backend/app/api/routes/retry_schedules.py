"""Thin HTTP adapters over the existing retry service."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from backend.app.api.dependencies import get_retry_service
from backend.app.models.enums import RetryStatus
from backend.app.models.retry_schedule import RetrySchedule
from backend.app.services.retry_service import RetryService

router = APIRouter(prefix="/retry-schedules", tags=["Retry Schedules"])


class RetryScheduleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    mandate_id: uuid.UUID
    retry_strategy: str
    recommended_time: datetime
    actual_retry_time: datetime | None
    retry_count: int
    max_retries: int
    status: RetryStatus


class CreateRetryScheduleRequest(BaseModel):
    mandate_id: uuid.UUID
    retry_strategy: str = Field(min_length=1, max_length=100)
    recommended_time: datetime
    max_retries: int = Field(default=3, ge=0)


class UpdateRetryScheduleRequest(BaseModel):
    retry_strategy: str | None = Field(default=None, min_length=1, max_length=100)
    recommended_time: datetime | None = None
    actual_retry_time: datetime | None = None
    retry_count: int | None = Field(default=None, ge=0)
    max_retries: int | None = Field(default=None, ge=0)
    status: RetryStatus | None = None


def _response(schedule: RetrySchedule) -> RetryScheduleResponse:
    return RetryScheduleResponse.model_validate(schedule)


@router.get("/{retry_schedule_id}", response_model=RetryScheduleResponse)
def get_retry_schedule(retry_schedule_id: uuid.UUID, service: RetryService = Depends(get_retry_service)) -> RetryScheduleResponse:
    return _response(service.get_retry_schedule(retry_schedule_id))


@router.get("", response_model=list[RetryScheduleResponse])
def list_pending_retries(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    service: RetryService = Depends(get_retry_service),
) -> list[RetryScheduleResponse]:
    return [_response(item) for item in service.list_pending_retries(offset=offset, limit=limit)]


@router.get("/mandate/{mandate_id}", response_model=RetryScheduleResponse)
def get_retry_schedule_for_mandate(mandate_id: uuid.UUID, service: RetryService = Depends(get_retry_service)) -> RetryScheduleResponse:
    schedule = service.get_retry_schedule_for_mandate(mandate_id)
    if schedule is None:
        raise HTTPException(status_code=404, detail="No retry schedule exists for this mandate")
    return _response(schedule)


@router.post("", response_model=RetryScheduleResponse, status_code=201)
def create_retry_schedule(request: CreateRetryScheduleRequest, service: RetryService = Depends(get_retry_service)) -> RetryScheduleResponse:
    return _response(
        service.create_retry_schedule(
            request.mandate_id,
            request.retry_strategy,
            request.recommended_time,
            max_retries=request.max_retries,
        )
    )


@router.patch("/{retry_schedule_id}", response_model=RetryScheduleResponse)
def update_retry_schedule(retry_schedule_id: uuid.UUID, request: UpdateRetryScheduleRequest, service: RetryService = Depends(get_retry_service)) -> RetryScheduleResponse:
    return _response(service.update_retry_schedule(retry_schedule_id, **request.model_dump()))
