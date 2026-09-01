"""Data access for persisted inbound payment-gateway webhook deliveries."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.models.webhook_event import WebhookEvent
from backend.app.repositories.base_repository import BaseRepository


class WebhookEventRepository(BaseRepository[WebhookEvent]):
    """Repository for the webhook-event audit trail."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, WebhookEvent)

    def get_by_dedupe_key(self, provider: str, event_type: str, entity_id: str) -> WebhookEvent | None:
        """Return an already-persisted delivery of the same real event, if Razorpay redelivered it."""
        try:
            statement = select(WebhookEvent).where(
                WebhookEvent.provider == provider,
                WebhookEvent.event_type == event_type,
                WebhookEvent.entity_id == entity_id,
            )
            return self.session.execute(statement).scalars().first()
        except SQLAlchemyError as exc:
            self._raise_database_error("get_by_dedupe_key", exc)

    def list_recent(self, *, offset: int = 0, limit: int = 100) -> list[WebhookEvent]:
        """Return the most recent webhook deliveries, newest first."""
        self._validate_pagination(offset, limit)
        try:
            statement = select(WebhookEvent).order_by(WebhookEvent.created_at.desc()).offset(offset).limit(limit)
            return list(self.session.execute(statement).scalars().all())
        except SQLAlchemyError as exc:
            self._raise_database_error("list_recent", exc)

    def record(
        self,
        *,
        provider: str,
        event_type: str,
        entity_id: str,
        signature_valid: bool,
        payload: str,
        mandate_id: uuid.UUID | None,
        payment_attempt_id: uuid.UUID | None,
        processing_error: str | None,
        processed_at: datetime | None,
    ) -> WebhookEvent:
        """Persist one webhook delivery — called exactly once per real event, before any side effects."""
        return self.create(
            provider=provider,
            event_type=event_type,
            entity_id=entity_id,
            signature_valid=signature_valid,
            payload=payload,
            mandate_id=mandate_id,
            payment_attempt_id=payment_attempt_id,
            processing_error=processing_error,
            processed_at=processed_at,
        )
