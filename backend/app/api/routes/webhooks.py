"""Inbound payment-gateway webhooks.

The one genuinely new endpoint this integration requires — nothing existing
handles inbound webhook deliveries. Everything the webhook triggers
(marking a payment attempt's outcome, re-running the recovery workflow)
reuses the exact same PaymentService / WorkflowRunnerService the rest of the
application already uses; this route is composition, not a parallel flow.
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.api.dependencies import get_ai_service, get_razorpay_service
from backend.app.database.session import get_db
from backend.app.llm.ai_service import AIService
from backend.app.services.razorpay_service import RazorpayService
from backend.app.services.workflow_runner_service import WorkflowRunnerService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


class WebhookAcceptedResponse(BaseModel):
    event_type: str
    signature_valid: bool
    processed: bool


@router.post("/razorpay", response_model=WebhookAcceptedResponse, summary="Receive a Razorpay webhook delivery")
async def receive_razorpay_webhook(
    request: Request,
    db: Session = Depends(get_db),
    razorpay_service: RazorpayService = Depends(get_razorpay_service),
    ai_service: AIService | None = Depends(get_ai_service),
) -> WebhookAcceptedResponse:
    """Verify, persist, and apply one Razorpay webhook delivery.

    Signature is verified against the exact raw request bytes (see
    RazorpayClient.verify_webhook_signature) — never against a re-parsed body.
    A missing/invalid signature returns 400 so it's visible in Razorpay's
    delivery log, rather than being silently swallowed.
    """
    raw_body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")

    event = razorpay_service.process_webhook(raw_body=raw_body, signature=signature)

    if not event.signature_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Razorpay webhook signature verification failed")

    if event.mandate_id is not None and event.processing_error is None:
        _rerun_workflow_after_webhook(db, ai_service, event.mandate_id)

    return WebhookAcceptedResponse(event_type=event.event_type, signature_valid=event.signature_valid, processed=event.processing_error is None)


def _rerun_workflow_after_webhook(db: Session, ai_service: AIService | None, mandate_id: uuid.UUID) -> None:
    """React to the new payment state through the existing workflow engine.

    A failure here is logged, not raised: the webhook's own job (persisting
    the event, updating the payment attempt) already committed successfully,
    and Razorpay retrying the delivery would not fix an unrelated workflow
    error — it would just redeliver an event that's already been applied.
    """
    try:
        WorkflowRunnerService(db, ai_service=ai_service).run_for_mandate(mandate_id)
    except Exception:
        logger.exception("Workflow re-run after Razorpay webhook failed", extra={"mandate_id": str(mandate_id)})
