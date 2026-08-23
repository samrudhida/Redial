"""Business operations for persisting AI decision audit entries."""

from __future__ import annotations

import uuid
from decimal import Decimal, InvalidOperation

from sqlalchemy.orm import Session

from backend.app.models.decision_log import DecisionLog
from backend.app.repositories.decision_log_repository import DecisionLogRepository
from backend.app.services.base_service import BaseService, ValidationError


class DecisionService(BaseService):
    """Stores supplied AI decisions without implementing AI generation logic."""

    def __init__(self, session: Session, decision_log_repository: DecisionLogRepository | None = None) -> None:
        self.decision_logs = decision_log_repository or DecisionLogRepository(session)
        super().__init__(session, repositories={"decision_logs": self.decision_logs})

    def record_ai_decision(self, mandate_id: uuid.UUID, decision_type: str, explanation: str, confidence_score: Decimal | float) -> DecisionLog:
        """Validate and persist an externally produced AI decision and confidence score."""
        self._require(bool(decision_type.strip()), "decision_type is required")
        self._require(bool(explanation.strip()), "explanation is required")
        try:
            confidence = Decimal(str(confidence_score))
        except InvalidOperation as exc:
            raise ValidationError("confidence_score must be numeric") from exc
        self._require(Decimal("0") <= confidence <= Decimal("1"), "confidence_score must be between 0 and 1")
        return self._in_transaction("record_ai_decision", lambda: self.decision_logs.create(mandate_id=mandate_id, decision_type=decision_type, explanation=explanation, confidence_score=confidence))

    def get_latest_decision(self, mandate_id: uuid.UUID) -> DecisionLog | None:
        """Return the latest decision audit entry for a mandate."""
        return self.decision_logs.get_latest_decision(mandate_id)
