"""Data access queries for auditable AI decisions."""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.models.decision_log import DecisionLog
from backend.app.repositories.base_repository import BaseRepository

class DecisionLogRepository(BaseRepository[DecisionLog]):
    """Repository for confidence-based AI-decision audit retrieval."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, DecisionLog)

    def get_by_confidence(self, minimum_confidence: Decimal | float, *, offset: int = 0, limit: int = 100) -> list[DecisionLog]:
        """Return decisions with confidence at least ``minimum_confidence``."""
        confidence = Decimal(str(minimum_confidence))
        if not Decimal("0") <= confidence <= Decimal("1"):
            raise ValueError("minimum_confidence must be between 0 and 1")
        self._validate_pagination(offset, limit)
        try:
            statement = select(DecisionLog).where(DecisionLog.confidence_score >= confidence).order_by(DecisionLog.confidence_score.desc(), DecisionLog.created_at.desc()).offset(offset).limit(limit)
            return list(self.session.execute(statement).scalars().all())
        except SQLAlchemyError as exc:
            self._raise_database_error("get_by_confidence", exc)

    def get_latest_decision(self, mandate_id: uuid.UUID) -> DecisionLog | None:
        """Return the most recently recorded AI decision for a mandate."""
        try:
            statement = select(DecisionLog).where(DecisionLog.mandate_id == mandate_id).order_by(DecisionLog.created_at.desc()).limit(1)
            return self.session.execute(statement).scalars().first()
        except SQLAlchemyError as exc:
            self._raise_database_error("get_latest_decision", exc)
