"""Data access queries for individual payment collection attempts."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.models.enums import PaymentStatus
from backend.app.models.payment_attempt import PaymentAttempt
from backend.app.repositories.base_repository import BaseRepository

class PaymentAttemptRepository(BaseRepository[PaymentAttempt]):
    """Repository for attempt history and outcome-oriented read queries."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, PaymentAttempt)

    def get_latest_attempt(self, mandate_id: uuid.UUID) -> PaymentAttempt | None:
        """Return the latest attempt for a mandate, preferring attempt sequence."""
        try:
            statement = select(PaymentAttempt).where(PaymentAttempt.mandate_id == mandate_id).order_by(PaymentAttempt.attempt_number.desc(), PaymentAttempt.attempted_at.desc()).limit(1)
            return self.session.execute(statement).scalars().first()
        except SQLAlchemyError as exc:
            self._raise_database_error("get_latest_attempt", exc)

    def get_failed_attempts(self, mandate_id: uuid.UUID, *, offset: int = 0, limit: int = 100) -> list[PaymentAttempt]:
        """Return failed attempts for a mandate, newest first."""
        return self._get_by_status(mandate_id, PaymentStatus.FAILED, offset=offset, limit=limit)

    def get_successful_attempts(self, mandate_id: uuid.UUID, *, offset: int = 0, limit: int = 100) -> list[PaymentAttempt]:
        """Return successful attempts for a mandate, newest first."""
        return self._get_by_status(mandate_id, PaymentStatus.SUCCEEDED, offset=offset, limit=limit)

    def get_attempt_history(self, mandate_id: uuid.UUID, *, offset: int = 0, limit: int = 100) -> list[PaymentAttempt]:
        """Return all payment attempts in chronological attempt order."""
        self._validate_pagination(offset, limit)
        try:
            statement = select(PaymentAttempt).where(PaymentAttempt.mandate_id == mandate_id).order_by(PaymentAttempt.attempt_number, PaymentAttempt.attempted_at).offset(offset).limit(limit)
            return list(self.session.execute(statement).scalars().all())
        except SQLAlchemyError as exc:
            self._raise_database_error("get_attempt_history", exc)

    def _get_by_status(self, mandate_id: uuid.UUID, status: PaymentStatus, *, offset: int, limit: int) -> list[PaymentAttempt]:
        self._validate_pagination(offset, limit)
        try:
            statement = select(PaymentAttempt).where(PaymentAttempt.mandate_id == mandate_id, PaymentAttempt.status == status).order_by(PaymentAttempt.attempted_at.desc()).offset(offset).limit(limit)
            return list(self.session.execute(statement).scalars().all())
        except SQLAlchemyError as exc:
            self._raise_database_error("get_attempts_by_status", exc)
