"""Tests for DashboardService, the cross-service aggregation used by the dashboard.

Mirrors the scenario from the manual SQLite smoke test performed during
development: one mandate recovers on a second attempt (counts as recovered
revenue), a second mandate succeeds on the first attempt (must NOT count),
plus a pending retry and an open escalation.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from backend.app.services.communication_service import CommunicationService
from backend.app.services.dashboard_service import DashboardService
from backend.app.services.decision_service import DecisionService
from backend.app.services.escalation_service import EscalationService
from backend.app.services.mandate_service import MandateService
from backend.app.services.payment_service import PaymentService
from backend.app.services.retry_service import RetryService


def _build_dashboard(db_session: Session) -> DashboardService:
    return DashboardService(
        mandate_service=MandateService(db_session),
        payment_service=PaymentService(db_session),
        retry_service=RetryService(db_session),
        escalation_service=EscalationService(db_session),
        decision_service=DecisionService(db_session),
        communication_service=CommunicationService(db_session),
    )


def test_dashboard_summary_aggregates_across_services(db_session: Session) -> None:
    mandate_svc = MandateService(db_session)
    payment_svc = PaymentService(db_session)
    retry_svc = RetryService(db_session)
    decision_svc = DecisionService(db_session)
    escalation_svc = EscalationService(db_session)
    communication_svc = CommunicationService(db_session)

    recovered_mandate = mandate_svc.register_mandate("cust-1", "REF-1", Decimal("500.00"))
    first_try_mandate = mandate_svc.register_mandate("cust-2", "REF-2", Decimal("750.00"))

    failed = payment_svc.record_payment_attempt(recovered_mandate.id, amount=Decimal("500.00"))
    payment_svc.mark_payment_failure(failed.id)
    recovered = payment_svc.record_payment_attempt(recovered_mandate.id, amount=Decimal("500.00"))
    payment_svc.mark_payment_success(recovered.id)

    first_try = payment_svc.record_payment_attempt(first_try_mandate.id, amount=Decimal("750.00"))
    payment_svc.mark_payment_success(first_try.id)

    retry_svc.create_retry_schedule(first_try_mandate.id, "exponential_backoff", datetime.now(timezone.utc))
    communication_svc.record_sms(recovered_mandate.id, "Payment recovered")
    decision_svc.record_ai_decision(recovered_mandate.id, "retry_decision", "Soft decline, retried", Decimal("0.92"))
    escalation_svc.create_escalation(first_try_mandate.id, "Manual review needed")

    summary = _build_dashboard(db_session).get_summary()

    assert summary.revenue_recovered == Decimal("500.00")
    assert summary.pending_retries == 1
    assert summary.open_escalations == 1
    assert len(summary.recent_decisions) == 1
    assert sum(summary.mandate_counts_by_status.values()) == 2


def test_dashboard_retry_queue_and_open_escalations_delegate_correctly(db_session: Session) -> None:
    mandate_svc = MandateService(db_session)
    retry_svc = RetryService(db_session)
    escalation_svc = EscalationService(db_session)

    mandate = mandate_svc.register_mandate("cust-1", "REF-1", Decimal("500.00"))
    schedule = retry_svc.create_retry_schedule(mandate.id, "exponential_backoff", datetime.now(timezone.utc))
    escalation = escalation_svc.create_escalation(mandate.id, "Manual review needed")

    dashboard = _build_dashboard(db_session)

    assert [item.id for item in dashboard.get_retry_queue()] == [schedule.id]
    assert [item.id for item in dashboard.get_open_escalations()] == [escalation.id]


def test_dashboard_trend_reflects_real_attempts_and_zero_fills_other_days(db_session: Session) -> None:
    mandate_svc = MandateService(db_session)
    payment_svc = PaymentService(db_session)

    mandate = mandate_svc.register_mandate("cust-1", "REF-1", Decimal("500.00"))
    today = datetime.now(timezone.utc)

    failed = payment_svc.record_payment_attempt(mandate.id, amount=Decimal("500.00"), attempted_at=today)
    payment_svc.mark_payment_failure(failed.id)
    recovered = payment_svc.record_payment_attempt(mandate.id, amount=Decimal("500.00"), attempted_at=today)
    payment_svc.mark_payment_success(recovered.id)

    trend = _build_dashboard(db_session).get_trend(days=3)

    assert len(trend) == 3
    assert [point.day for point in trend] == sorted(point.day for point in trend)

    today_point = trend[-1]
    assert today_point.day == today.date()
    assert today_point.attempts_total == 2
    assert today_point.attempts_succeeded == 1
    assert today_point.attempts_failed == 1
    assert today_point.collected_amount == Decimal("500.00")
    assert today_point.recovered_amount == Decimal("500.00")

    empty_point = trend[0]
    assert empty_point.attempts_total == 0
    assert empty_point.collected_amount == Decimal("0")
    assert empty_point.recovered_amount == Decimal("0")


def test_dashboard_recent_activity_merges_decisions_and_communications_newest_first(db_session: Session) -> None:
    mandate_svc = MandateService(db_session)
    decision_svc = DecisionService(db_session)
    communication_svc = CommunicationService(db_session)

    mandate = mandate_svc.register_mandate("cust-1", "REF-1", Decimal("500.00"))
    base = datetime(2026, 8, 28, tzinfo=timezone.utc)

    decision = decision_svc.record_ai_decision(mandate.id, "retry_decision", "Soft decline, retry scheduled", Decimal("0.9"))
    decision.created_at = base
    communication = communication_svc.record_sms(mandate.id, "We will retry your payment shortly")
    communication.sent_at = base + timedelta(minutes=1)
    db_session.commit()

    activity = _build_dashboard(db_session).get_recent_activity(limit=10)

    assert len(activity) == 2
    assert activity[0].event_type == "communication"
    assert activity[0].mandate_id == mandate.id
    assert activity[0].timestamp == communication.sent_at
    assert activity[1].event_type == "decision"
    assert activity[1].timestamp == decision.created_at
