"""Data access queries for customer communication records."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.models.communication import Communication
from backend.app.models.enums import CommunicationChannel, DeliveryStatus
from backend.app.repositories.base_repository import BaseRepository

class CommunicationRepository(BaseRepository[Communication]):
    """Repository for channel delivery records and delivery-failure review."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, Communication)

    def get_by_channel(
        self,
        channel: CommunicationChannel,
        mandate_id: uuid.UUID | None = None,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Communication]:
        """Return communications for a channel, optionally scoped to a mandate."""
        self._validate_pagination(offset, limit)
        try:
            statement = select(Communication).where(Communication.channel == channel)
            if mandate_id is not None:
                statement = statement.where(Communication.mandate_id == mandate_id)
            statement = statement.order_by(Communication.sent_at.desc()).offset(offset).limit(limit)
            return list(self.session.execute(statement).scalars().all())
        except SQLAlchemyError as exc:
            self._raise_database_error("get_by_channel", exc)

    def list_recent(self, *, offset: int = 0, limit: int = 100) -> list[Communication]:
        """Return communications across every mandate, newest first."""
        self._validate_pagination(offset, limit)
        try:
            statement = select(Communication).order_by(Communication.sent_at.desc()).offset(offset).limit(limit)
            return list(self.session.execute(statement).scalars().all())
        except SQLAlchemyError as exc:
            self._raise_database_error("list_recent", exc)

    def get_by_mandate(self, mandate_id: uuid.UUID, *, offset: int = 0, limit: int = 100) -> list[Communication]:
        """Return all communications for a mandate, newest first."""
        self._validate_pagination(offset, limit)
        try:
            statement = select(Communication).where(Communication.mandate_id == mandate_id).order_by(Communication.sent_at.desc()).offset(offset).limit(limit)
            return list(self.session.execute(statement).scalars().all())
        except SQLAlchemyError as exc:
            self._raise_database_error("get_by_mandate", exc)

    def get_delivery_failures(self, mandate_id: uuid.UUID | None = None, *, offset: int = 0, limit: int = 100) -> list[Communication]:
        """Return failed deliveries, optionally restricted to one mandate."""
        self._validate_pagination(offset, limit)
        try:
            statement = select(Communication).where(Communication.delivery_status == DeliveryStatus.FAILED)
            if mandate_id is not None:
                statement = statement.where(Communication.mandate_id == mandate_id)
            statement = statement.order_by(Communication.sent_at.desc()).offset(offset).limit(limit)
            return list(self.session.execute(statement).scalars().all())
        except SQLAlchemyError as exc:
            self._raise_database_error("get_delivery_failures", exc)
