"""Mandate ORM model: the aggregate root for recurring payments."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, Enum, Index, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from backend.app.database.base import Base
from backend.app.models.enums import MandateStatus, enum_values

if TYPE_CHECKING:
    from backend.app.models.communication import Communication
    from backend.app.models.decision_log import DecisionLog
    from backend.app.models.escalation import Escalation
    from backend.app.models.payment_attempt import PaymentAttempt
    from backend.app.models.retry_schedule import RetrySchedule


class Mandate(Base):
    __tablename__ = "mandates"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_mandate_amount_positive"),
        Index("ix_mandates_customer_status", "customer_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    mandate_reference: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    bank_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    account_last4: Mapped[str | None] = mapped_column(String(4), nullable=True)
    status: Mapped[MandateStatus] = mapped_column(
        Enum(MandateStatus, name="mandate_status", values_callable=enum_values, validate_strings=True),
        nullable=False,
        default=MandateStatus.ACTIVE,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    payment_attempts: Mapped[list[PaymentAttempt]] = relationship(back_populates="mandate", cascade="all, delete-orphan", passive_deletes=True)
    retry_schedule: Mapped[RetrySchedule | None] = relationship(back_populates="mandate", cascade="all, delete-orphan", passive_deletes=True, uselist=False)
    communications: Mapped[list[Communication]] = relationship(back_populates="mandate", cascade="all, delete-orphan", passive_deletes=True)
    decision_logs: Mapped[list[DecisionLog]] = relationship(back_populates="mandate", cascade="all, delete-orphan", passive_deletes=True)
    escalations: Mapped[list[Escalation]] = relationship(back_populates="mandate", cascade="all, delete-orphan", passive_deletes=True)
