"""Tests for DecisionService read/list operations."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from backend.app.core.exceptions import NotFoundError
from backend.app.services.decision_service import DecisionService
from backend.app.services.mandate_service import MandateService


@pytest.fixture()
def mandate_id(db_session: Session):
    return MandateService(db_session).register_mandate("cust-1", "REF-1", Decimal("500.00")).id


def test_get_decision_raises_not_found_for_unknown_id(db_session: Session) -> None:
    service = DecisionService(db_session)

    with pytest.raises(NotFoundError):
        service.get_decision(uuid.uuid4())


def test_list_decisions_filters_by_mandate(db_session: Session, mandate_id) -> None:
    service = DecisionService(db_session)
    other_mandate_id = MandateService(db_session).register_mandate("cust-2", "REF-2", Decimal("100.00")).id
    service.record_ai_decision(mandate_id, "retry_decision", "Soft decline", Decimal("0.9"))
    service.record_ai_decision(other_mandate_id, "retry_decision", "Soft decline elsewhere", Decimal("0.8"))

    result = service.list_decisions(mandate_id)

    assert len(result) == 1
    assert result[0].mandate_id == mandate_id


def test_list_decisions_without_mandate_returns_all(db_session: Session, mandate_id) -> None:
    service = DecisionService(db_session)
    service.record_ai_decision(mandate_id, "retry_decision", "Soft decline", Decimal("0.9"))
    service.record_ai_decision(mandate_id, "escalation_decision", "Cap reached", Decimal("0.99"))

    assert len(service.list_decisions()) == 2


def test_list_decisions_without_mandate_is_ordered_newest_first(db_session: Session, mandate_id) -> None:
    """Callers with no mandate filter (the dashboard's 'Recent AI decisions'
    panel, the AI Decisions page) expect the most recently recorded decisions
    first — not an arbitrary primary-key order that never reflects new activity.
    """
    service = DecisionService(db_session)
    base = datetime(2026, 8, 28, tzinfo=timezone.utc)
    first = service.record_ai_decision(mandate_id, "retry_decision", "First", Decimal("0.9"))
    second = service.record_ai_decision(mandate_id, "retry_decision", "Second", Decimal("0.9"))
    third = service.record_ai_decision(mandate_id, "retry_decision", "Third", Decimal("0.9"))
    first.created_at = base
    second.created_at = base + timedelta(minutes=1)
    third.created_at = base + timedelta(minutes=2)
    db_session.commit()

    result = service.list_decisions(limit=2)

    assert [item.id for item in result] == [third.id, second.id]
    assert first.id not in [item.id for item in result]
