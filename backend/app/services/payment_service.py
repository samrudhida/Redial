"""Business operations for recording and resolving payment attempts."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from backend.app.core.exceptions import NotFoundError
from backend.app.models.enums import DeclineCategory, PaymentStatus
from backend.app.models.mandate import Mandate
from backend.app.models.payment_attempt import PaymentAttempt
from backend.app.repositories.mandate_repository import MandateRepository
from backend.app.repositories.payment_attempt_repository import PaymentAttemptRepository
from backend.app.services.base_service import BaseService, InvalidStateError


class PaymentService(BaseService):
    """Coordinates mandate eligibility with payment-attempt lifecycle changes."""

    def __init__(self, session: Session, payment_attempt_repository: PaymentAttemptRepository | None = None, mandate_repository: MandateRepository | None = None) -> None:
        self.payment_attempts = payment_attempt_repository or PaymentAttemptRepository(session)
        self.mandates = mandate_repository or MandateRepository(session)
        super().__init__(session, repositories={"payment_attempts": self.payment_attempts, "mandates": self.mandates})

    def record_payment_attempt(self, mandate_id: uuid.UUID, *, amount: Decimal | None = None, attempted_at: datetime | None = None, bank_response_code: str | None = None, bank_response_message: str | None = None, ai_reasoning: str | None = None) -> PaymentAttempt:
        """Record the next pending collection attempt for an active mandate."""
        def action() -> PaymentAttempt:
            mandate = self._require_active_mandate(mandate_id)
            attempt_amount = amount if amount is not None else mandate.amount
            self._require(attempt_amount > Decimal("0"), "attempt amount must be positive")
            latest = self.payment_attempts.get_latest_attempt(mandate_id)
            attempt_number = (latest.attempt_number if latest else 0) + 1
            values: dict[str, object] = {"mandate_id": mandate_id, "attempt_number": attempt_number, "amount": attempt_amount, "status": PaymentStatus.PENDING, "bank_response_code": bank_response_code, "bank_response_message": bank_response_message, "ai_reasoning": ai_reasoning}
            if attempted_at is not None:
                values["attempted_at"] = attempted_at
            return self.payment_attempts.create(**values)

        return self._in_transaction("record_payment_attempt", action)

    def mark_payment_success(self, payment_attempt_id: uuid.UUID) -> PaymentAttempt:
        """Mark a non-terminal payment attempt as successful and clear retry timing."""
        return self._update_outcome(payment_attempt_id, PaymentStatus.SUCCEEDED, "mark_payment_success", next_retry_at=None)

    def mark_payment_failure(self, payment_attempt_id: uuid.UUID, *, decline_category: DeclineCategory | None = None, bank_response_code: str | None = None, bank_response_message: str | None = None, ai_reasoning: str | None = None, next_retry_at: datetime | None = None) -> PaymentAttempt:
        """Mark a non-successful payment attempt as failed with optional failure context."""
        return self._update_outcome(payment_attempt_id, PaymentStatus.FAILED, "mark_payment_failure", decline_category=decline_category, bank_response_code=bank_response_code, bank_response_message=bank_response_message, ai_reasoning=ai_reasoning, next_retry_at=next_retry_at)

    def get_latest_attempt(self, mandate_id: uuid.UUID) -> PaymentAttempt | None:
        """Return the latest attempt for a mandate without opening a write transaction."""
        return self.payment_attempts.get_latest_attempt(mandate_id)

    def _update_outcome(self, payment_attempt_id: uuid.UUID, status: PaymentStatus, operation: str, **values: object) -> PaymentAttempt:
        def action() -> PaymentAttempt:
            attempt = self.payment_attempts.get_by_id(payment_attempt_id)
            if attempt is None:
                raise NotFoundError("Payment attempt not found")
            if attempt.status is PaymentStatus.SUCCEEDED and status is not PaymentStatus.SUCCEEDED:
                raise InvalidStateError("A successful payment attempt cannot be changed")
            updated = self.payment_attempts.update(payment_attempt_id, status=status, **values)
            if updated is None:
                raise NotFoundError("Payment attempt not found")
            return updated

        return self._in_transaction(operation, action)

    def _require_active_mandate(self, mandate_id: uuid.UUID) -> Mandate:
        mandate = self.mandates.get_by_id(mandate_id)
        if mandate is None:
            raise NotFoundError("Mandate not found")
        if mandate.status.value != "active":
            raise InvalidStateError("Payment attempts require an active mandate")
        return mandate
