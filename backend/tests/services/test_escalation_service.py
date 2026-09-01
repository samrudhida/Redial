"""Tests for EscalationService read/list/count operations."""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from backend.app.core.exceptions import NotFoundError
from backend.app.services.escalation_service import EscalationService
from backend.app.services.mandate_service import MandateService


@pytest.fixture()
def mandate_id(db_session: Session):
    return MandateService(db_session).register_mandate("cust-1", "REF-1", Decimal("500.00")).id


def test_get_escalation_raises_not_found_for_unknown_id(db_session: Session) -> None:
    service = EscalationService(db_session)

    with pytest.raises(NotFoundError):
        service.get_escalation(uuid.uuid4())


def test_open_vs_resolved_lists_and_open_count(db_session: Session, mandate_id) -> None:
    service = EscalationService(db_session)
    open_one = service.create_escalation(mandate_id, "Needs review")
    resolved_one = service.create_escalation(mandate_id, "Already handled")
    service.resolve_escalation(resolved_one.id)

    open_list = service.list_open_escalations()
    resolved_list = service.list_resolved_escalations()

    assert [e.id for e in open_list] == [open_one.id]
    assert [e.id for e in resolved_list] == [resolved_one.id]
    assert service.count_open_escalations() == 1
