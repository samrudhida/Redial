"""Tests for RetryService read/list operations."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from backend.app.core.exceptions import NotFoundError
from backend.app.services.mandate_service import MandateService
from backend.app.services.retry_service import RetryService


@pytest.fixture()
def mandate_id(db_session: Session):
    return MandateService(db_session).register_mandate("cust-1", "REF-1", Decimal("500.00")).id


def test_get_retry_schedule_raises_not_found_for_unknown_id(db_session: Session) -> None:
    service = RetryService(db_session)

    with pytest.raises(NotFoundError):
        service.get_retry_schedule(uuid.uuid4())


def test_get_retry_schedule_for_mandate_returns_none_when_absent(db_session: Session, mandate_id) -> None:
    service = RetryService(db_session)

    assert service.get_retry_schedule_for_mandate(mandate_id) is None


def test_get_retry_schedule_for_mandate_returns_the_one_schedule(db_session: Session, mandate_id) -> None:
    service = RetryService(db_session)
    created = service.create_retry_schedule(mandate_id, "exponential_backoff", datetime.now(timezone.utc))

    found = service.get_retry_schedule_for_mandate(mandate_id)

    assert found is not None
    assert found.id == created.id


def test_list_pending_retries_and_count_agree(db_session: Session, mandate_id) -> None:
    service = RetryService(db_session)
    service.create_retry_schedule(mandate_id, "exponential_backoff", datetime.now(timezone.utc))

    assert len(service.list_pending_retries()) == 1
    assert service.count_pending_retries() == 1
