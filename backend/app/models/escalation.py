"""Merchant or support escalation ORM model."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from backend.app.database.base import Base
from backend.app.models.enums import EscalationLevel, enum_values

if TYPE_CHECKING:
    from backend.app.models.mandate import Mandate


class Escalation(Base):
    __tablename__ = "escalations"
    __table_args__ = (Index("ix_escalations_resolved_level", "resolved", "escalation_level"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mandate_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("mandates.id", ondelete="CASCADE"), nullable=False, index=True)
    escalation_level: Mapped[EscalationLevel] = mapped_column(Enum(EscalationLevel, name="escalation_level", values_callable=enum_values, validate_strings=True), nullable=False, index=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    assigned_to: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    mandate: Mapped[Mandate] = relationship(back_populates="escalations")
