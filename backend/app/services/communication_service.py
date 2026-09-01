"""Business operations for recording customer notifications."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from backend.app.core.exceptions import NotFoundError
from backend.app.models.communication import Communication
from backend.app.models.enums import CommunicationChannel, DeliveryStatus
from backend.app.repositories.communication_repository import CommunicationRepository
from backend.app.services.base_service import BaseService


class CommunicationService(BaseService):
    """Records channel-specific communications and delivery-status changes."""

    def __init__(self, session: Session, communication_repository: CommunicationRepository | None = None) -> None:
        self.communications = communication_repository or CommunicationRepository(session)
        super().__init__(session, repositories={"communications": self.communications})

    def record_sms(self, mandate_id: uuid.UUID, message: str, *, template_name: str | None = None) -> Communication:
        """Persist an SMS notification queued for delivery."""
        return self._record(mandate_id, CommunicationChannel.SMS, message, template_name)

    def record_email(self, mandate_id: uuid.UUID, message: str, *, template_name: str | None = None) -> Communication:
        """Persist an email notification queued for delivery."""
        return self._record(mandate_id, CommunicationChannel.EMAIL, message, template_name)

    def record_whatsapp(self, mandate_id: uuid.UUID, message: str, *, template_name: str | None = None) -> Communication:
        """Persist a WhatsApp notification queued for delivery."""
        return self._record(mandate_id, CommunicationChannel.WHATSAPP, message, template_name)

    def get_communication(self, communication_id: uuid.UUID) -> Communication:
        """Return a communication record or raise a domain-level not-found exception."""
        communication = self.communications.get_by_id(communication_id)
        if communication is None:
            raise NotFoundError("Communication not found")
        return communication

    def list_communications(self, mandate_id: uuid.UUID | None = None, *, channel: CommunicationChannel | None = None, offset: int = 0, limit: int = 100) -> list[Communication]:
        """Return communications, optionally filtered to one mandate and/or channel."""
        if channel is not None:
            return self.communications.get_by_channel(channel, mandate_id, offset=offset, limit=limit)
        if mandate_id is not None:
            return self.communications.get_by_mandate(mandate_id, offset=offset, limit=limit)
        return self.communications.list_recent(offset=offset, limit=limit)

    def update_delivery_status(self, communication_id: uuid.UUID, delivery_status: DeliveryStatus) -> Communication:
        """Update a persisted notification's delivery outcome."""
        def action() -> Communication:
            if self.communications.get_by_id(communication_id) is None:
                raise NotFoundError("Communication not found")
            updated = self.communications.update(communication_id, delivery_status=delivery_status)
            if updated is None:
                raise NotFoundError("Communication not found")
            return updated

        return self._in_transaction("update_delivery_status", action)

    def _record(self, mandate_id: uuid.UUID, channel: CommunicationChannel, message: str, template_name: str | None) -> Communication:
        self._require(bool(message.strip()), "message is required")
        return self._in_transaction(f"record_{channel.value}", lambda: self.communications.create(mandate_id=mandate_id, channel=channel, message=message, template_name=template_name, delivery_status=DeliveryStatus.PENDING))
