"""Ingests real Razorpay webhook deliveries into the existing payment/workflow flow.

This is deliberately the only place Razorpay's webhook envelope shape is
understood. Everything downstream — marking a payment attempt succeeded or
failed, and (at the route layer) re-running the recovery workflow — reuses
the exact same PaymentService/WorkflowRunnerService methods a manual or
simulated call already uses. There is no parallel state machine.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from backend.app.models.webhook_event import WebhookEvent
from backend.app.payments.razorpay_client import RazorpayClient
from backend.app.repositories.webhook_event_repository import WebhookEventRepository
from backend.app.services.base_service import BaseService, InvalidStateError
from backend.app.services.payment_service import PaymentService

logger = logging.getLogger(__name__)

_SUCCESS_EVENTS = {"payment.captured", "order.paid"}
_FAILURE_EVENTS = {"payment.failed"}


class RazorpayService(BaseService):
    """Verifies, persists, and applies one inbound Razorpay webhook delivery at a time."""

    def __init__(
        self,
        session: Session,
        client: RazorpayClient | None,
        payment_service: PaymentService | None = None,
        webhook_event_repository: WebhookEventRepository | None = None,
    ) -> None:
        self.client = client
        self.payments = payment_service or PaymentService(session)
        self.webhook_events = webhook_event_repository or WebhookEventRepository(session)
        super().__init__(session, repositories={"webhook_events": self.webhook_events})

    def process_webhook(self, *, raw_body: bytes, signature: str) -> WebhookEvent:
        """Verify the signature, persist the delivery, and apply it if it resolves to a known attempt.

        Always persists a WebhookEvent row — including deliveries that fail
        signature verification or can't be matched to an attempt — so no
        incoming event is ever silently dropped. Only a genuine
        infrastructure failure (a DB error) rolls this back; Razorpay will
        then retry the delivery later, which is the correct behavior for a
        transient failure.
        """
        def action() -> WebhookEvent:
            signature_valid = self.client.verify_webhook_signature(raw_body=raw_body, signature=signature) if self.client is not None else False
            payload = self._safe_json(raw_body)
            event_type = str(payload.get("event", "unknown"))
            entity = self._extract_entity(payload, event_type)
            entity_id = str(entity.get("id") or "")

            if entity_id:
                existing = self.webhook_events.get_by_dedupe_key("razorpay", event_type, entity_id)
                if existing is not None:
                    return existing

            mandate_id = None
            payment_attempt_id = None
            processing_error: str | None = None

            if not signature_valid:
                processing_error = "Signature verification failed"
            elif not entity_id:
                processing_error = "Could not identify an entity id on this event"
            else:
                order_id = entity.get("id") if event_type.startswith("order.") else entity.get("order_id")
                attempt = self.payments.get_by_razorpay_order_id(order_id) if order_id else None
                if attempt is None:
                    processing_error = f"No payment attempt found for Razorpay order {order_id!r}"
                else:
                    payment_attempt_id = attempt.id
                    mandate_id = attempt.mandate_id
                    try:
                        self._apply_event(attempt.id, event_type, entity)
                    except InvalidStateError as exc:
                        processing_error = str(exc)

            return self.webhook_events.record(
                provider="razorpay",
                event_type=event_type,
                entity_id=entity_id or "unknown",
                signature_valid=signature_valid,
                payload=raw_body.decode("utf-8", errors="replace"),
                mandate_id=mandate_id,
                payment_attempt_id=payment_attempt_id,
                processing_error=processing_error,
                processed_at=None if processing_error else datetime.now(timezone.utc),
            )

        return self._in_transaction("process_webhook", action)

    def _apply_event(self, payment_attempt_id: Any, event_type: str, entity: dict[str, Any]) -> None:
        """Apply a resolved event through the existing PaymentService — no separate state machine."""
        if event_type in _SUCCESS_EVENTS:
            razorpay_payment_id = entity.get("id") if event_type == "payment.captured" else None
            self.payments.mark_payment_success(payment_attempt_id, razorpay_payment_id=razorpay_payment_id)
        elif event_type in _FAILURE_EVENTS:
            self.payments.mark_payment_failure(
                payment_attempt_id,
                bank_response_code=entity.get("error_code"),
                bank_response_message=entity.get("error_description"),
                razorpay_payment_id=entity.get("id"),
            )
        # Other event types (e.g. payment.authorized, ahead of auto-capture)
        # are legitimately received but don't change our own outcome state —
        # they're still persisted above for observability.

    @staticmethod
    def _safe_json(raw_body: bytes) -> dict[str, Any]:
        try:
            return json.loads(raw_body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {}

    @staticmethod
    def _extract_entity(payload: dict[str, Any], event_type: str) -> dict[str, Any]:
        """Pull the real payment/order object out of Razorpay's webhook envelope.

        Shape: {"event": "payment.captured", "contains": ["payment"],
        "payload": {"payment": {"entity": {...}}}}. Falls back to deriving
        the entity key from the event type if "contains" is absent.
        """
        nested = payload.get("payload", {})
        for key in payload.get("contains") or []:
            entity = nested.get(key, {}).get("entity")
            if entity:
                return entity
        fallback_key = event_type.split(".", 1)[0]
        return nested.get(fallback_key, {}).get("entity", {})
