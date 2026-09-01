"""Thin HTTP adapters over the existing payment service."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field

from backend.app.api.dependencies import get_payment_service
from backend.app.models.enums import DeclineCategory, PaymentStatus
from backend.app.models.payment_attempt import PaymentAttempt
from backend.app.services.payment_service import PaymentService

router = APIRouter(prefix="/payments", tags=["Payments"])


class PaymentAttemptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    mandate_id: uuid.UUID
    attempt_number: int
    attempted_at: datetime
    amount: Decimal
    status: PaymentStatus
    bank_response_code: str | None
    bank_response_message: str | None
    decline_category: DeclineCategory | None
    ai_reasoning: str | None
    next_retry_at: datetime | None
    razorpay_order_id: str | None
    razorpay_payment_id: str | None


class RecordAttemptRequest(BaseModel):
    mandate_id: uuid.UUID
    amount: Decimal | None = Field(default=None, gt=0)
    bank_response_code: str | None = None
    bank_response_message: str | None = None
    ai_reasoning: str | None = None


class MarkFailureRequest(BaseModel):
    decline_category: DeclineCategory | None = None
    bank_response_code: str | None = None
    bank_response_message: str | None = None
    ai_reasoning: str | None = None
    next_retry_at: datetime | None = None


def _response(attempt: PaymentAttempt) -> PaymentAttemptResponse:
    return PaymentAttemptResponse.model_validate(attempt)


@router.get("/{payment_attempt_id}", response_model=PaymentAttemptResponse)
def get_payment_attempt(payment_attempt_id: uuid.UUID, service: PaymentService = Depends(get_payment_service)) -> PaymentAttemptResponse:
    return _response(service.get_attempt(payment_attempt_id))


@router.get("", response_model=list[PaymentAttemptResponse])
def list_payment_attempts(
    mandate_id: uuid.UUID = Query(...),
    status_filter: PaymentStatus | None = Query(default=None, alias="status"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    service: PaymentService = Depends(get_payment_service),
) -> list[PaymentAttemptResponse]:
    attempts = service.list_attempts(mandate_id, status=status_filter, offset=offset, limit=limit)
    return [_response(item) for item in attempts]


@router.post("", response_model=PaymentAttemptResponse, status_code=201)
def record_payment_attempt(request: RecordAttemptRequest, service: PaymentService = Depends(get_payment_service)) -> PaymentAttemptResponse:
    return _response(service.record_payment_attempt(**request.model_dump()))


@router.patch("/{payment_attempt_id}/success", response_model=PaymentAttemptResponse)
def mark_payment_success(payment_attempt_id: uuid.UUID, service: PaymentService = Depends(get_payment_service)) -> PaymentAttemptResponse:
    return _response(service.mark_payment_success(payment_attempt_id))


@router.patch("/{payment_attempt_id}/failure", response_model=PaymentAttemptResponse)
def mark_payment_failure(payment_attempt_id: uuid.UUID, request: MarkFailureRequest, service: PaymentService = Depends(get_payment_service)) -> PaymentAttemptResponse:
    return _response(service.mark_payment_failure(payment_attempt_id, **request.model_dump()))
