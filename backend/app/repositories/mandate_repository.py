"""Data access queries for recurring payment mandates."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.models.enums import MandateStatus, PaymentStatus
from backend.app.models.mandate import Mandate
from backend.app.models.payment_attempt import PaymentAttempt
from backend.app.repositories.base_repository import BaseRepository

class MandateRepository(BaseRepository[Mandate]):
    """Repository for mandate lookup, lifecycle filtering, and customer search."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, Mandate)

    def get_by_reference(self, mandate_reference: str) -> Mandate | None:
        """Return the unique mandate associated with an external reference."""
        try:
            statement = select(Mandate).where(Mandate.mandate_reference == mandate_reference)
            return self.session.execute(statement).scalar_one_or_none()
        except SQLAlchemyError as exc:
            self._raise_database_error("get_by_reference", exc)

    def get_active(self, *, offset: int = 0, limit: int = 100) -> list[Mandate]:
        """Return active mandates, newest first."""
        return self._get_by_status(MandateStatus.ACTIVE, offset=offset, limit=limit)

    def get_by_status(self, status: MandateStatus, *, offset: int = 0, limit: int = 100) -> list[Mandate]:
        """Return mandates in a given lifecycle status, newest first."""
        return self._get_by_status(status, offset=offset, limit=limit)

    def count_by_status(self) -> dict[MandateStatus, int]:
        """Return the number of mandates grouped by lifecycle status."""
        try:
            statement = select(Mandate.status, func.count(Mandate.id)).group_by(Mandate.status)
            rows = self.session.execute(statement).all()
            return {status: count for status, count in rows}
        except SQLAlchemyError as exc:
            self._raise_database_error("count_by_status", exc)

    def get_failed(self, *, offset: int = 0, limit: int = 100) -> list[Mandate]:
        """Return mandates having at least one failed payment attempt.

        Mandate status describes the recurring mandate lifecycle; payment
        failure belongs to ``PaymentAttempt``. ``distinct`` prevents one
        mandate appearing more than once when multiple attempts failed.
        """
        self._validate_pagination(offset, limit)
        try:
            statement = (
                select(Mandate)
                .join(PaymentAttempt, PaymentAttempt.mandate_id == Mandate.id)
                .where(PaymentAttempt.status == PaymentStatus.FAILED)
                .distinct()
                .order_by(Mandate.updated_at.desc())
                .offset(offset)
                .limit(limit)
            )
            return list(self.session.execute(statement).scalars().all())
        except SQLAlchemyError as exc:
            self._raise_database_error("get_failed", exc)

    def search_by_customer(self, customer_id: str, *, offset: int = 0, limit: int = 100) -> list[Mandate]:
        """Return mandates for an exact customer identifier, newest first."""
        self._validate_pagination(offset, limit)
        try:
            statement = (
                select(Mandate)
                .where(Mandate.customer_id == customer_id)
                .order_by(Mandate.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
            return list(self.session.execute(statement).scalars().all())
        except SQLAlchemyError as exc:
            self._raise_database_error("search_by_customer", exc)

    def _get_by_status(self, status: MandateStatus, *, offset: int, limit: int) -> list[Mandate]:
        self._validate_pagination(offset, limit)
        try:
            statement = select(Mandate).where(Mandate.status == status).order_by(Mandate.updated_at.desc()).offset(offset).limit(limit)
            return list(self.session.execute(statement).scalars().all())
        except SQLAlchemyError as exc:
            self._raise_database_error("get_by_status", exc)
