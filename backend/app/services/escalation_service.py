"""Business operations for merchant and support escalation workflows."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from backend.app.core.exceptions import NotFoundError
from backend.app.models.escalation import Escalation
from backend.app.models.enums import EscalationLevel
from backend.app.repositories.escalation_repository import EscalationRepository
from backend.app.services.base_service import BaseService


class EscalationService(BaseService):
    """Creates escalation work items and records their resolution lifecycle."""

    def __init__(self, session: Session, escalation_repository: EscalationRepository | None = None) -> None:
        self.escalations = escalation_repository or EscalationRepository(session)
        super().__init__(session, repositories={"escalations": self.escalations})

    def create_escalation(self, mandate_id: uuid.UUID, reason: str, *, escalation_level: EscalationLevel = EscalationLevel.LEVEL_1, assigned_to: str | None = None) -> Escalation:
        """Validate and create an unresolved escalation for merchant or support review."""
        self._require(bool(reason.strip()), "reason is required")
        return self._in_transaction("create_escalation", lambda: self.escalations.create(mandate_id=mandate_id, escalation_level=escalation_level, reason=reason, assigned_to=assigned_to, resolved=False))

    def resolve_escalation(self, escalation_id: uuid.UUID, *, resolved_at: datetime | None = None) -> Escalation:
        """Mark an open escalation resolved, recording an aware UTC timestamp by default."""
        resolved_time = resolved_at or datetime.now(timezone.utc)
        self._require(resolved_time.tzinfo is not None and resolved_time.utcoffset() is not None, "resolved_at must be timezone-aware")

        def action() -> Escalation:
            escalation = self.escalations.get_by_id(escalation_id)
            if escalation is None:
                raise NotFoundError("Escalation not found")
            if escalation.resolved:
                return escalation
            updated = self.escalations.update(escalation_id, resolved=True, resolved_at=resolved_time)
            if updated is None:
                raise NotFoundError("Escalation not found")
            return updated

        return self._in_transaction("resolve_escalation", action)

    def list_open_escalations(self, mandate_id: uuid.UUID | None = None, *, offset: int = 0, limit: int = 100) -> list[Escalation]:
        """Return unresolved escalations for an operational review queue."""
        return self.escalations.get_open_escalations(mandate_id, offset=offset, limit=limit)

    def list_resolved_escalations(self, mandate_id: uuid.UUID | None = None, *, offset: int = 0, limit: int = 100) -> list[Escalation]:
        """Return resolved escalations, optionally scoped to one mandate."""
        return self.escalations.get_resolved_escalations(mandate_id, offset=offset, limit=limit)

    def count_open_escalations(self) -> int:
        """Return the number of unresolved escalations awaiting human review."""
        return self.escalations.count_open_escalations()

    def get_escalation(self, escalation_id: uuid.UUID) -> Escalation:
        """Return an escalation or raise a domain-level not-found exception."""
        escalation = self.escalations.get_by_id(escalation_id)
        if escalation is None:
            raise NotFoundError("Escalation not found")
        return escalation
