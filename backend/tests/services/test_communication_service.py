"""Tests for CommunicationService read/list operations."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from backend.app.core.exceptions import NotFoundError
from backend.app.models.enums import CommunicationChannel
from backend.app.services.communication_service import CommunicationService
from backend.app.services.mandate_service import MandateService


@pytest.fixture()
def mandate_id(db_session: Session):
    return MandateService(db_session).register_mandate("cust-1", "REF-1", Decimal("500.00")).id


def test_get_communication_raises_not_found_for_unknown_id(db_session: Session) -> None:
    service = CommunicationService(db_session)

    with pytest.raises(NotFoundError):
        service.get_communication(uuid.uuid4())


def test_list_communications_filters_by_mandate(db_session: Session, mandate_id) -> None:
    service = CommunicationService(db_session)
    other_mandate_id = MandateService(db_session).register_mandate("cust-2", "REF-2", Decimal("100.00")).id
    service.record_sms(mandate_id, "hello")
    service.record_sms(other_mandate_id, "hello elsewhere")

    result = service.list_communications(mandate_id)

    assert len(result) == 1
    assert result[0].mandate_id == mandate_id


def test_list_communications_filters_by_channel(db_session: Session, mandate_id) -> None:
    service = CommunicationService(db_session)
    service.record_sms(mandate_id, "sms message")
    service.record_email(mandate_id, "email message")

    sms_only = service.list_communications(mandate_id, channel=CommunicationChannel.SMS)

    assert len(sms_only) == 1
    assert sms_only[0].channel is CommunicationChannel.SMS


def test_list_communications_without_mandate_is_ordered_newest_first(db_session: Session, mandate_id) -> None:
    service = CommunicationService(db_session)
    base = datetime(2026, 8, 28, tzinfo=timezone.utc)
    first = service.record_sms(mandate_id, "first")
    second = service.record_sms(mandate_id, "second")
    first.sent_at = base
    second.sent_at = base + timedelta(minutes=1)
    db_session.commit()

    result = service.list_communications(limit=2)

    assert [item.id for item in result] == [second.id, first.id]
