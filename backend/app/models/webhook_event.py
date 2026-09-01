"""Inbound payment-gateway webhook event ORM model — an audit trail, not a queue.

Every webhook delivery is persisted here before any processing happens,
including ones that fail signature verification, so a bad or malicious
delivery is still visible rather than silently dropped.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from backend.app.database.base import Base

if TYPE_CHECKING:
    from backend.app.models.mandate import Mandate
    from backend.app.models.payment_attempt import PaymentAttempt


class WebhookEvent(Base):
    __tablename__ = "webhook_events"
    __table_args__ = (
        # Razorpay may redeliver the same event on a non-2xx response; the
        # same (event_type, entity_id) pair identifies one real business
        # event, so a repeat delivery is a no-op rather than a duplicate row.
        UniqueConstraint("provider", "event_type", "entity_id", name="uq_webhook_event_dedupe"),
        Index("ix_webhook_events_mandate_created_at", "mandate_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider: Mapped[str] = mapped_column(String(50), nullable=False, default="razorpay")
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(255), nullable=False)
    signature_valid: Mapped[bool] = mapped_column(Boolean, nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    mandate_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("mandates.id", ondelete="SET NULL"), nullable=True, index=True)
    payment_attempt_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("payment_attempts.id", ondelete="SET NULL"), nullable=True)
    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    mandate: Mapped[Mandate | None] = relationship()
    payment_attempt: Mapped[PaymentAttempt | None] = relationship()
