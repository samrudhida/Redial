"""Business operations for the mandate lifecycle."""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy.orm import Session

from backend.app.core.exceptions import NotFoundError
from backend.app.models.enums import MandateStatus
from backend.app.models.mandate import Mandate
from backend.app.repositories.mandate_repository import MandateRepository
from backend.app.services.base_service import BaseService, InvalidStateError, ValidationError


class MandateService(BaseService):
    """Registers mandates and enforces their permitted lifecycle transitions."""

    def __init__(self, session: Session, mandate_repository: MandateRepository | None = None) -> None:
        self.mandates = mandate_repository or MandateRepository(session)
        super().__init__(session, repositories={"mandates": self.mandates})

    def register_mandate(self, customer_id: str, mandate_reference: str, amount: Decimal, *, currency: str = "INR", bank_name: str | None = None, account_last4: str | None = None) -> Mandate:
        """Validate and register a new active recurring-payment mandate."""
        self._validate_registration(customer_id, mandate_reference, amount, currency, account_last4)

        def action() -> Mandate:
            if self.mandates.get_by_reference(mandate_reference) is not None:
                raise ValidationError("A mandate with this reference already exists")
            return self.mandates.create(customer_id=customer_id, mandate_reference=mandate_reference, amount=amount, currency=currency.upper(), bank_name=bank_name, account_last4=account_last4, status=MandateStatus.ACTIVE)

        return self._in_transaction("register_mandate", action)

    def activate_mandate(self, mandate_id: uuid.UUID) -> Mandate:
        """Activate a paused mandate; cancelled, expired, and completed mandates stay terminal."""
        return self._transition(mandate_id, allowed_from={MandateStatus.PAUSED}, target=MandateStatus.ACTIVE, operation="activate_mandate")

    def pause_mandate(self, mandate_id: uuid.UUID) -> Mandate:
        """Pause an active mandate so future collection work can be withheld."""
        return self._transition(mandate_id, allowed_from={MandateStatus.ACTIVE}, target=MandateStatus.PAUSED, operation="pause_mandate")

    def cancel_mandate(self, mandate_id: uuid.UUID) -> Mandate:
        """Cancel an active or paused mandate; terminal mandates cannot be changed."""
        return self._transition(mandate_id, allowed_from={MandateStatus.ACTIVE, MandateStatus.PAUSED}, target=MandateStatus.CANCELLED, operation="cancel_mandate")

    def list_mandates(self, *, status: MandateStatus | None = None, customer_id: str | None = None, offset: int = 0, limit: int = 100) -> list[Mandate]:
        """Return mandates, optionally filtered to one lifecycle status or customer."""
        if customer_id is not None:
            return self.mandates.search_by_customer(customer_id, offset=offset, limit=limit)
        if status is not None:
            return self.mandates.get_by_status(status, offset=offset, limit=limit)
        return self.mandates.get_all(offset=offset, limit=limit)

    def count_by_status(self) -> dict[MandateStatus, int]:
        """Return the number of mandates grouped by lifecycle status."""
        return self.mandates.count_by_status()

    def get_mandate(self, mandate_id: uuid.UUID) -> Mandate:
        """Return a mandate or raise a domain-level not-found exception."""
        mandate = self.mandates.get_by_id(mandate_id)
        if mandate is None:
            raise NotFoundError("Mandate not found")
        return mandate

    def validate_mandate(self, mandate_id: uuid.UUID) -> Mandate:
        """Ensure a mandate is active and has valid payment configuration."""
        mandate = self.get_mandate(mandate_id)
        if mandate.status is not MandateStatus.ACTIVE:
            raise InvalidStateError("Mandate must be active")
        self._require(mandate.amount > Decimal("0"), "Mandate amount must be positive")
        self._require(len(mandate.currency) == 3, "Mandate currency must be a three-letter code")
        return mandate

    def _transition(self, mandate_id: uuid.UUID, *, allowed_from: set[MandateStatus], target: MandateStatus, operation: str) -> Mandate:
        def action() -> Mandate:
            mandate = self.get_mandate(mandate_id)
            if mandate.status not in allowed_from:
                self._raise_invalid_state(f"Cannot transition mandate from {mandate.status.value} to {target.value}")
            updated = self.mandates.update(mandate_id, status=target)
            if updated is None:
                raise NotFoundError("Mandate not found")
            return updated

        return self._in_transaction(operation, action)

    def _validate_registration(self, customer_id: str, mandate_reference: str, amount: Decimal, currency: str, account_last4: str | None) -> None:
        self._require(bool(customer_id.strip()), "customer_id is required")
        self._require(bool(mandate_reference.strip()), "mandate_reference is required")
        self._require(amount > Decimal("0"), "amount must be positive")
        self._require(len(currency.strip()) == 3 and currency.strip().isalpha(), "currency must be a three-letter code")
        if account_last4 is not None:
            self._require(len(account_last4) == 4, "account_last4 must contain exactly four characters")
