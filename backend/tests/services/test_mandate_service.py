"""Tests for MandateService.list_mandates and count_by_status."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from backend.app.models.enums import MandateStatus
from backend.app.services.mandate_service import MandateService


def _make_mandate(service: MandateService, *, customer_id: str, reference: str, amount: str = "500.00"):
    return service.register_mandate(customer_id, reference, Decimal(amount))


def test_list_mandates_returns_all_by_default(db_session: Session) -> None:
    service = MandateService(db_session)
    _make_mandate(service, customer_id="cust-1", reference="REF-1")
    _make_mandate(service, customer_id="cust-2", reference="REF-2")

    assert len(service.list_mandates()) == 2


def test_list_mandates_filters_by_customer_id(db_session: Session) -> None:
    service = MandateService(db_session)
    _make_mandate(service, customer_id="cust-1", reference="REF-1")
    _make_mandate(service, customer_id="cust-2", reference="REF-2")

    result = service.list_mandates(customer_id="cust-1")

    assert len(result) == 1
    assert result[0].customer_id == "cust-1"


def test_list_mandates_filters_by_status(db_session: Session) -> None:
    service = MandateService(db_session)
    paused = _make_mandate(service, customer_id="cust-1", reference="REF-1")
    _make_mandate(service, customer_id="cust-2", reference="REF-2")
    service.pause_mandate(paused.id)

    active = service.list_mandates(status=MandateStatus.ACTIVE)
    paused_list = service.list_mandates(status=MandateStatus.PAUSED)

    assert len(active) == 1
    assert len(paused_list) == 1
    assert paused_list[0].id == paused.id


def test_list_mandates_respects_pagination(db_session: Session) -> None:
    service = MandateService(db_session)
    for i in range(5):
        _make_mandate(service, customer_id=f"cust-{i}", reference=f"REF-{i}")

    page = service.list_mandates(offset=2, limit=2)

    assert len(page) == 2


def test_count_by_status_groups_correctly(db_session: Session) -> None:
    service = MandateService(db_session)
    m1 = _make_mandate(service, customer_id="cust-1", reference="REF-1")
    _make_mandate(service, customer_id="cust-2", reference="REF-2")
    service.cancel_mandate(m1.id)

    counts = service.count_by_status()

    assert counts[MandateStatus.CANCELLED] == 1
    assert counts[MandateStatus.ACTIVE] == 1
