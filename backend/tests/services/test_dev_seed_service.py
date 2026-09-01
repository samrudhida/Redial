"""Tests for the developer-only demo-data seed/delete service."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from backend.app.services.dev_seed_service import DEMO_REFERENCE_PREFIX, DevSeedService
from backend.app.services.mandate_service import MandateService


def test_seed_creates_the_requested_number_of_mandates(db_session: Session) -> None:
    service = DevSeedService(db_session)

    summary = service.seed(20)

    assert summary.mandates_created == 20
    assert len(MandateService(db_session).list_mandates(limit=100)) == 20


def test_seed_data_is_namespaced_with_demo_prefix(db_session: Session) -> None:
    service = DevSeedService(db_session)
    service.seed(20)

    mandates = MandateService(db_session).list_mandates(limit=100)

    assert all(mandate.mandate_reference.startswith(DEMO_REFERENCE_PREFIX) for mandate in mandates)
    assert all(mandate.customer_id.startswith("DEMO-CUST-") for mandate in mandates)


def test_seed_produces_related_records_across_every_entity(db_session: Session) -> None:
    service = DevSeedService(db_session)

    summary = service.seed(30)

    # Every entity type should be represented at least once at this sample size.
    assert summary.payment_attempts_created > 0
    assert summary.retry_schedules_created > 0
    assert summary.decisions_created > 0
    assert summary.communications_created > 0
    assert summary.escalations_created > 0


def test_seed_timestamps_stay_within_the_past_60_days(db_session: Session) -> None:
    service = DevSeedService(db_session)
    service.seed(20)

    mandates = MandateService(db_session).list_mandates(limit=100)
    # SQLite round-trips DateTime(timezone=True) as naive (unlike the real
    # Postgres database), so compare in naive UTC on both sides here.
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    cutoff = now - timedelta(days=61)  # small buffer for generation time

    assert all(cutoff <= mandate.created_at <= now for mandate in mandates)


def test_seed_produces_more_than_one_mandate_status(db_session: Session) -> None:
    """Confirms the mix-of-statuses requirement isn't accidentally collapsed to one value."""
    service = DevSeedService(db_session)
    service.seed(30)

    mandates = MandateService(db_session).list_mandates(limit=100)
    statuses = {mandate.status for mandate in mandates}

    assert len(statuses) > 1


def test_delete_removes_only_demo_data(db_session: Session) -> None:
    mandate_service = MandateService(db_session)
    real_mandate = mandate_service.register_mandate("real-customer", "REAL-REF-001", Decimal("500.00"))

    seed_service = DevSeedService(db_session)
    seed_service.seed(20)

    deleted_count = seed_service.delete_seed_data()

    assert deleted_count == 20
    remaining = mandate_service.list_mandates(limit=100)
    assert [m.mandate_reference for m in remaining] == [real_mandate.mandate_reference]


def test_delete_cascades_related_records(db_session: Session) -> None:
    from backend.app.services.communication_service import CommunicationService
    from backend.app.services.decision_service import DecisionService
    from backend.app.services.escalation_service import EscalationService
    from backend.app.services.payment_service import PaymentService
    from backend.app.services.retry_service import RetryService

    seed_service = DevSeedService(db_session)
    seed_service.seed(30)

    seed_service.delete_seed_data()

    assert PaymentService(db_session).payment_attempts.get_all(limit=1000) == []
    assert RetryService(db_session).retry_schedules.get_all(limit=1000) == []
    assert DecisionService(db_session).list_decisions(limit=1000) == []
    assert CommunicationService(db_session).list_communications(limit=1000) == []
    assert EscalationService(db_session).list_open_escalations(limit=1000) == []
    assert EscalationService(db_session).list_resolved_escalations(limit=1000) == []
