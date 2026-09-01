"""Business operations for retry-plan lifecycle and retry capacity."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from backend.app.core.exceptions import NotFoundError
from backend.app.models.enums import MandateStatus, RetryStatus
from backend.app.models.retry_schedule import RetrySchedule
from backend.app.repositories.mandate_repository import MandateRepository
from backend.app.repositories.retry_schedule_repository import RetryScheduleRepository
from backend.app.services.base_service import BaseService, InvalidStateError


class RetryService(BaseService):
    """Coordinates retry plans with mandate eligibility and retry-count rules."""

    def __init__(self, session: Session, retry_schedule_repository: RetryScheduleRepository | None = None, mandate_repository: MandateRepository | None = None) -> None:
        self.retry_schedules = retry_schedule_repository or RetryScheduleRepository(session)
        self.mandates = mandate_repository or MandateRepository(session)
        super().__init__(session, repositories={"retry_schedules": self.retry_schedules, "mandates": self.mandates})

    def create_retry_schedule(self, mandate_id: uuid.UUID, retry_strategy: str, recommended_time: datetime, *, max_retries: int = 3) -> RetrySchedule:
        """Create the current retry plan for an active mandate."""
        self._require(bool(retry_strategy.strip()), "retry_strategy is required")
        self._require_time(recommended_time, "recommended_time")
        self._require(max_retries >= 0, "max_retries cannot be negative")

        def action() -> RetrySchedule:
            mandate = self.mandates.get_by_id(mandate_id)
            if mandate is None:
                raise NotFoundError("Mandate not found")
            if mandate.status is not MandateStatus.ACTIVE:
                raise InvalidStateError("Retry schedules require an active mandate")
            return self.retry_schedules.create(mandate_id=mandate_id, retry_strategy=retry_strategy, recommended_time=recommended_time, retry_count=0, max_retries=max_retries, status=RetryStatus.PENDING)

        return self._in_transaction("create_retry_schedule", action)

    def update_retry_schedule(self, retry_schedule_id: uuid.UUID, *, retry_strategy: str | None = None, recommended_time: datetime | None = None, actual_retry_time: datetime | None = None, retry_count: int | None = None, max_retries: int | None = None, status: RetryStatus | None = None) -> RetrySchedule:
        """Update a retry plan while preserving non-negative, bounded retry counts."""
        def action() -> RetrySchedule:
            schedule = self.retry_schedules.get_by_id(retry_schedule_id)
            if schedule is None:
                raise NotFoundError("Retry schedule not found")
            effective_count = retry_count if retry_count is not None else schedule.retry_count
            effective_max = max_retries if max_retries is not None else schedule.max_retries
            self._require(effective_count >= 0, "retry_count cannot be negative")
            self._require(effective_max >= effective_count, "max_retries cannot be less than retry_count")
            if retry_strategy is not None:
                self._require(bool(retry_strategy.strip()), "retry_strategy cannot be blank")
            if recommended_time is not None:
                self._require_time(recommended_time, "recommended_time")
            if actual_retry_time is not None:
                self._require_time(actual_retry_time, "actual_retry_time")
            values = {key: value for key, value in {"retry_strategy": retry_strategy, "recommended_time": recommended_time, "actual_retry_time": actual_retry_time, "retry_count": retry_count, "max_retries": max_retries, "status": status}.items() if value is not None}
            if not values:
                return schedule
            updated = self.retry_schedules.update(retry_schedule_id, **values)
            if updated is None:
                raise NotFoundError("Retry schedule not found")
            return updated

        return self._in_transaction("update_retry_schedule", action)

    def get_retry_schedule(self, retry_schedule_id: uuid.UUID) -> RetrySchedule:
        """Return a retry plan or raise a domain-level not-found exception."""
        schedule = self.retry_schedules.get_by_id(retry_schedule_id)
        if schedule is None:
            raise NotFoundError("Retry schedule not found")
        return schedule

    def get_retry_schedule_for_mandate(self, mandate_id: uuid.UUID) -> RetrySchedule | None:
        """Return the single retry plan associated with a mandate, if any."""
        return self.retry_schedules.get_by_mandate(mandate_id)

    def list_pending_retries(self, *, offset: int = 0, limit: int = 100) -> list[RetrySchedule]:
        """Return retry plans awaiting processing, ordered by recommended time."""
        return self.retry_schedules.get_pending_retries(offset=offset, limit=limit)

    def count_pending_retries(self) -> int:
        """Return the number of retry plans awaiting processing."""
        return self.retry_schedules.count_pending_retries()

    def calculate_remaining_retries(self, retry_schedule_id: uuid.UUID) -> int:
        """Return the non-negative number of attempts still allowed by a retry plan."""
        schedule = self.retry_schedules.get_by_id(retry_schedule_id)
        if schedule is None:
            raise NotFoundError("Retry schedule not found")
        return max(schedule.max_retries - schedule.retry_count, 0)

    def get_due_retries(self, *, as_of: datetime | None = None, limit: int = 100) -> list[RetrySchedule]:
        """Return retry plans due for processing at the supplied time."""
        return self.retry_schedules.get_due_retries(as_of=as_of, limit=limit)

    def _require_time(self, value: datetime, field_name: str) -> None:
        self._require(value.tzinfo is not None and value.utcoffset() is not None, f"{field_name} must be timezone-aware")
