"""Current retry-plan ORM model for a mandate."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from backend.app.database.base import Base
from backend.app.models.enums import RetryStatus, enum_values

if TYPE_CHECKING:
    from backend.app.models.mandate import Mandate


class RetrySchedule(Base):
    __tablename__ = "retry_schedules"
    __table_args__ = (
        CheckConstraint("retry_count >= 0", name="ck_retry_schedule_count_nonnegative"),
        CheckConstraint("max_retries >= 0", name="ck_retry_schedule_max_nonnegative"),
        CheckConstraint("retry_count <= max_retries", name="ck_retry_schedule_count_within_max"),
        Index("ix_retry_schedules_status_recommended_time", "status", "recommended_time"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mandate_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("mandates.id", ondelete="CASCADE"), nullable=False, unique=True)
    retry_strategy: Mapped[str] = mapped_column(String(100), nullable=False)
    recommended_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    actual_retry_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    status: Mapped[RetryStatus] = mapped_column(Enum(RetryStatus, name="retry_status", values_callable=enum_values, validate_strings=True), nullable=False, default=RetryStatus.PENDING, index=True)

    mandate: Mapped[Mandate] = relationship(back_populates="retry_schedule")
