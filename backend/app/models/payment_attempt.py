"""Payment attempt ORM model."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from backend.app.database.base import Base
from backend.app.models.enums import DeclineCategory, PaymentStatus, enum_values

if TYPE_CHECKING:
    from backend.app.models.mandate import Mandate


class PaymentAttempt(Base):
    __tablename__ = "payment_attempts"
    __table_args__ = (
        UniqueConstraint("mandate_id", "attempt_number", name="uq_payment_attempt_mandate_number"),
        CheckConstraint("attempt_number > 0", name="ck_payment_attempt_number_positive"),
        CheckConstraint("amount > 0", name="ck_payment_attempt_amount_positive"),
        Index("ix_payment_attempts_mandate_attempted_at", "mandate_id", "attempted_at"),
        Index("ix_payment_attempts_status_next_retry_at", "status", "next_retry_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mandate_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("mandates.id", ondelete="CASCADE"), nullable=False, index=True)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    attempted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus, name="payment_status", values_callable=enum_values, validate_strings=True), nullable=False, default=PaymentStatus.PENDING, index=True)
    bank_response_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    bank_response_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    decline_category: Mapped[DeclineCategory | None] = mapped_column(Enum(DeclineCategory, name="decline_category", values_callable=enum_values, validate_strings=True), nullable=True, index=True)
    ai_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    mandate: Mapped[Mandate] = relationship(back_populates="payment_attempts")
