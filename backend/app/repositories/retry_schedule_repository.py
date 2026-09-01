"""Data access queries for the mandate retry queue."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.models.enums import RetryStatus
from backend.app.models.retry_schedule import RetrySchedule
from backend.app.repositories.base_repository import BaseRepository

class RetryScheduleRepository(BaseRepository[RetrySchedule]):
    """Repository for finding and updating persisted retry plans."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, RetrySchedule)

    def get_by_mandate(self, mandate_id: uuid.UUID) -> RetrySchedule | None:
        """Return the single retry plan for a mandate, if one exists."""
        try:
            statement = select(RetrySchedule).where(RetrySchedule.mandate_id == mandate_id)
            return self.session.execute(statement).scalar_one_or_none()
        except SQLAlchemyError as exc:
            self._raise_database_error("get_by_mandate", exc)

    def count_pending_retries(self) -> int:
        """Return the number of retry plans awaiting processing."""
        try:
            statement = select(func.count(RetrySchedule.id)).where(RetrySchedule.status.in_((RetryStatus.PENDING, RetryStatus.SCHEDULED)))
            return self.session.execute(statement).scalar_one()
        except SQLAlchemyError as exc:
            self._raise_database_error("count_pending_retries", exc)

    def get_pending_retries(self, *, offset: int = 0, limit: int = 100) -> list[RetrySchedule]:
        """Return retry plans awaiting processing, ordered by recommended time."""
        self._validate_pagination(offset, limit)
        try:
            statement = select(RetrySchedule).where(RetrySchedule.status.in_((RetryStatus.PENDING, RetryStatus.SCHEDULED))).order_by(RetrySchedule.recommended_time).offset(offset).limit(limit)
            return list(self.session.execute(statement).scalars().all())
        except SQLAlchemyError as exc:
            self._raise_database_error("get_pending_retries", exc)

    def get_due_retries(self, *, as_of: datetime | None = None, limit: int = 100) -> list[RetrySchedule]:
        """Return pending retry plans whose recommended time is at or before ``as_of``."""
        self._validate_pagination(0, limit)
        due_at = as_of or datetime.now(timezone.utc)
        try:
            statement = select(RetrySchedule).where(RetrySchedule.status.in_((RetryStatus.PENDING, RetryStatus.SCHEDULED)), RetrySchedule.recommended_time <= due_at).order_by(RetrySchedule.recommended_time).limit(limit)
            return list(self.session.execute(statement).scalars().all())
        except SQLAlchemyError as exc:
            self._raise_database_error("get_due_retries", exc)

    def update_retry_status(self, retry_schedule_id: uuid.UUID, status: RetryStatus, *, actual_retry_time: datetime | None = None) -> RetrySchedule | None:
        """Update retry plan status and optionally record when the retry occurred."""
        values: dict[str, object] = {"status": status}
        if actual_retry_time is not None:
            values["actual_retry_time"] = actual_retry_time
        return self.update(retry_schedule_id, **values)
