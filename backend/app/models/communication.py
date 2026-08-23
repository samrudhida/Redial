"""Customer communication ORM model."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from backend.app.database.base import Base
from backend.app.models.enums import CommunicationChannel, DeliveryStatus, enum_values

if TYPE_CHECKING:
    from backend.app.models.mandate import Mandate


class Communication(Base):
    __tablename__ = "communications"
    __table_args__ = (Index("ix_communications_mandate_sent_at", "mandate_id", "sent_at"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mandate_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("mandates.id", ondelete="CASCADE"), nullable=False, index=True)
    channel: Mapped[CommunicationChannel] = mapped_column(Enum(CommunicationChannel, name="communication_channel", values_callable=enum_values, validate_strings=True), nullable=False)
    template_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    delivery_status: Mapped[DeliveryStatus] = mapped_column(Enum(DeliveryStatus, name="delivery_status", values_callable=enum_values, validate_strings=True), nullable=False, default=DeliveryStatus.PENDING, index=True)

    mandate: Mapped[Mandate] = relationship(back_populates="communications")
