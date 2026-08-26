"""Tests for the retry-scheduler job: finds due retries and runs the real workflow for each."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from backend.app.scheduler.jobs import run_due_retries
from backend.app.services.mandate_service import MandateService
from backend.app.services.payment_service import PaymentService
from backend.app.services.retry_service import RetryService
from backend.app.services.workflow_execution_service import WorkflowExecutionService
from backend.app.services.workflow_runner_service import WorkflowRunnerService


def _make_due_mandate(db_session: Session, reference: str):
    mandate_service = MandateService(db_session)
    payment_service = PaymentService(db_session)
    retry_service = RetryService(db_session)
    mandate = mandate_service.register_mandate(f"cust-{reference}", reference, Decimal("500.00"))
    attempt = payment_service.record_payment_attempt(mandate.id)
    payment_service.mark_payment_failure(attempt.id)
    schedule = retry_service.get_retry_schedule_for_mandate(mandate.id)
    assert schedule is not None
    retry_service.update_retry_schedule(schedule.id, recommended_time=datetime.now(timezone.utc) - timedelta(hours=1))
    return mandate


def test_run_due_retries_runs_the_workflow_for_every_due_mandate(db_session: Session) -> None:
    _make_due_mandate(db_session, "JOB-REF-1")
    _make_due_mandate(db_session, "JOB-REF-2")

    result = run_due_retries(session_factory=lambda: db_session)

    assert result.attempted == 2
    assert result.succeeded == 2
    assert result.failed == 0
    overview = WorkflowExecutionService(db_session).get_overview()
    assert overview.workflows_executed == 2


def test_run_due_retries_ignores_schedules_that_are_not_yet_due(db_session: Session) -> None:
    mandate_service = MandateService(db_session)
    payment_service = PaymentService(db_session)
    mandate_service.register_mandate("cust-not-due", "JOB-REF-NOT-DUE", Decimal("500.00"))
    mandate = mandate_service.list_mandates(customer_id="cust-not-due")[0]
    attempt = payment_service.record_payment_attempt(mandate.id)
    payment_service.mark_payment_failure(attempt.id)  # default recommended_time is ~24h out — not due yet

    result = run_due_retries(session_factory=lambda: db_session)

    assert result.attempted == 0


def test_run_due_retries_continues_past_a_single_mandate_failure(db_session: Session, monkeypatch) -> None:
    _make_due_mandate(db_session, "JOB-REF-OK")
    broken_mandate = _make_due_mandate(db_session, "JOB-REF-BROKEN")

    original = WorkflowRunnerService.run_for_mandate

    def flaky_run_for_mandate(self, mandate_id):
        if mandate_id == broken_mandate.id:
            raise RuntimeError("simulated failure")
        return original(self, mandate_id)

    monkeypatch.setattr(WorkflowRunnerService, "run_for_mandate", flaky_run_for_mandate)

    result = run_due_retries(session_factory=lambda: db_session)

    assert result.attempted == 2
    assert result.succeeded == 1
    assert result.failed == 1
