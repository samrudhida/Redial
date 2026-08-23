"""Data access queries for merchant and support escalations."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.models.escalation import Escalation
from backend.app.repositories.base_repository import BaseRepository

class EscalationRepository(BaseRepository[Escalation]):
    """Repository for escalation-work queues and resolved escalation history."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, Escalation)

    def get_open_escalations(self, mandate_id: uuid.UUID | None = None, *, offset: int = 0, limit: int = 100) -> list[Escalation]:
        """Return unresolved escalations, optionally for one mandate."""
        return self._get_by_resolution(False, mandate_id=mandate_id, offset=offset, limit=limit)

    def get_resolved_escalations(self, mandate_id: uuid.UUID | None = None, *, offset: int = 0, limit: int = 100) -> list[Escalation]:
        """Return resolved escalations, optionally for one mandate."""
        return self._get_by_resolution(True, mandate_id=mandate_id, offset=offset, limit=limit)

    def _get_by_resolution(self, resolved: bool, *, mandate_id: uuid.UUID | None, offset: int, limit: int) -> list[Escalation]:
        self._validate_pagination(offset, limit)
        try:
            statement = select(Escalation).where(Escalation.resolved.is_(resolved))
            if mandate_id is not None:
                statement = statement.where(Escalation.mandate_id == mandate_id)
            statement = statement.order_by(Escalation.resolved_at.desc(), Escalation.id).offset(offset).limit(limit)
            return list(self.session.execute(statement).scalars().all())
        except SQLAlchemyError as exc:
            self._raise_database_error("get_escalations_by_resolution", exc)
