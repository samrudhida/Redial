"""Tests that the real workflow graph actually runs and persists real history."""

from __future__ import annotations

import json
import uuid
from decimal import Decimal

from sqlalchemy.orm import Session

from backend.app.llm.ai_service import AIService
from backend.app.llm.base_llm import BaseLLM
from backend.app.models.enums import DeclineCategory, EscalationLevel, RetryStatus
from backend.app.services.communication_service import CommunicationService
from backend.app.services.decision_service import DecisionService
from backend.app.services.escalation_service import EscalationService
from backend.app.services.mandate_service import MandateService
from backend.app.services.payment_service import PaymentService
from backend.app.services.retry_service import RetryService
from backend.app.services.workflow_execution_service import NODE_SEQUENCE, WorkflowExecutionService
from backend.app.services.workflow_runner_service import WorkflowRunnerService


class _FakeLLM(BaseLLM):
    """Deterministic BaseLLM double so the AI-enabled path needs no network access."""

    provider = "fake"

    def generate(self, prompt: str, *, system_prompt: str | None = None, **options: object) -> str:
        return json.dumps(
            {
                "decision": "retry_recommended",
                "confidence": 0.87,
                "reasoning": "Fake AI reasoning for test purposes.",
                "recommended_action": "retry_in_24h",
            }
        )

    def health_check(self) -> bool:
        return True

    def get_model_name(self) -> str:
        return "fake-model"


def _make_mandate_with_failed_attempt(db_session: Session):
    mandate_service = MandateService(db_session)
    payment_service = PaymentService(db_session)
    mandate = mandate_service.register_mandate("workflow-cust-1", "WORKFLOW-REF-1", Decimal("500.00"))
    attempt = payment_service.record_payment_attempt(mandate.id)
    payment_service.mark_payment_failure(attempt.id, bank_response_message="insufficient_funds")
    return mandate


def _make_mandate_with_bank_unavailable_failure(db_session: Session):
    mandate_service = MandateService(db_session)
    payment_service = PaymentService(db_session)
    mandate = mandate_service.register_mandate("workflow-cust-2", "WORKFLOW-REF-2", Decimal("500.00"))
    attempt = payment_service.record_payment_attempt(mandate.id)
    payment_service.mark_payment_failure(attempt.id, decline_category=DeclineCategory.BANK_UNAVAILABLE, bank_response_message="bank unavailable")
    return mandate


def test_run_for_mandate_executes_every_node_in_order(db_session: Session) -> None:
    mandate = _make_mandate_with_failed_attempt(db_session)
    runner = WorkflowRunnerService(db_session)

    state = runner.run_for_mandate(mandate.id)

    assert state.final_decision is not None
    assert [entry.step for entry in state.history] == NODE_SEQUENCE


def test_run_for_mandate_persists_a_real_execution_row(db_session: Session) -> None:
    mandate = _make_mandate_with_failed_attempt(db_session)
    runner = WorkflowRunnerService(db_session)

    state = runner.run_for_mandate(mandate.id)

    execution_service = WorkflowExecutionService(db_session)
    detail = execution_service.get_execution_detail(uuid.UUID(state.metadata.execution_id))

    assert detail.summary.mandate_id == mandate.id
    assert detail.summary.status == "completed"
    assert len(detail.nodes) == len(NODE_SEQUENCE)
    assert [node.node_name for node in detail.nodes] == NODE_SEQUENCE
    assert all(node.duration_ms >= 0 for node in detail.nodes)


def test_run_for_mandate_deterministic_only_when_no_ai_provider_configured(db_session: Session) -> None:
    mandate = _make_mandate_with_failed_attempt(db_session)
    runner = WorkflowRunnerService(db_session)

    state = runner.run_for_mandate(mandate.id)

    assert state.final_decision is not None
    assert state.final_decision.ai_used is False
    assert state.final_decision.confidence == 0.0


def test_overview_reflects_real_runs(db_session: Session) -> None:
    mandate = _make_mandate_with_failed_attempt(db_session)
    runner = WorkflowRunnerService(db_session)
    runner.run_for_mandate(mandate.id)

    overview = WorkflowExecutionService(db_session).get_overview()

    assert overview.workflows_executed == 1
    assert overview.successful_workflows == 1
    assert overview.failed_workflows == 0
    assert overview.average_execution_time_ms >= 0
    assert overview.total_ai_calls == 0  # honest: no AI provider is configured in this environment


def test_run_for_mandate_uses_ai_when_ai_service_is_injected(db_session: Session) -> None:
    mandate = _make_mandate_with_failed_attempt(db_session)
    runner = WorkflowRunnerService(db_session, ai_service=AIService(llm=_FakeLLM()))

    state = runner.run_for_mandate(mandate.id)

    assert state.final_decision is not None
    assert state.final_decision.ai_used is True
    assert state.final_decision.confidence == 0.87
    assert "Fake AI reasoning for test purposes." in state.final_decision.reasoning

    decision_service = DecisionService(db_session)
    latest = decision_service.get_latest_decision(mandate.id)
    assert latest is not None
    assert latest.decision_type == "retry_decision"
    assert latest.confidence_score == Decimal("0.87")
    assert latest.explanation == state.final_decision.reasoning


def test_metrics_report_real_per_node_durations(db_session: Session) -> None:
    mandate = _make_mandate_with_failed_attempt(db_session)
    runner = WorkflowRunnerService(db_session)
    runner.run_for_mandate(mandate.id)

    metrics = WorkflowExecutionService(db_session).get_metrics()

    assert metrics.average_workflow_duration_ms >= 0
    assert metrics.average_node_duration_ms >= 0
    assert metrics.database_persistence_latency_ms >= 0


def test_run_for_mandate_cancels_the_schedule_when_the_mandate_is_no_longer_active(db_session: Session) -> None:
    mandate = _make_mandate_with_failed_attempt(db_session)
    MandateService(db_session).pause_mandate(mandate.id)

    runner = WorkflowRunnerService(db_session)
    state = runner.run_for_mandate(mandate.id)

    assert state.final_decision is not None
    assert state.final_decision.retry.allowed is False
    schedule = RetryService(db_session).get_retry_schedule_for_mandate(mandate.id)
    assert schedule is not None
    assert schedule.status == RetryStatus.CANCELLED


def test_run_for_mandate_resolves_a_stale_pending_schedule_after_the_payment_already_succeeded(db_session: Session) -> None:
    mandate = _make_mandate_with_failed_attempt(db_session)
    payment_service = PaymentService(db_session)
    retry_service = RetryService(db_session)
    recovered = payment_service.record_payment_attempt(mandate.id)
    payment_service.mark_payment_success(recovered.id)
    schedule = retry_service.get_retry_schedule_for_mandate(mandate.id)
    assert schedule is not None
    # Simulate legacy data left dangling from before mark_payment_success resolved schedules.
    retry_service.update_retry_schedule(schedule.id, status=RetryStatus.PENDING)

    runner = WorkflowRunnerService(db_session)
    runner.run_for_mandate(mandate.id)

    resolved = retry_service.get_retry_schedule_for_mandate(mandate.id)
    assert resolved is not None
    assert resolved.status == RetryStatus.EXECUTED


def test_run_for_mandate_books_a_new_retry_attempt_and_advances_the_schedule(db_session: Session) -> None:
    mandate = _make_mandate_with_failed_attempt(db_session)
    payment_service = PaymentService(db_session)
    retry_service = RetryService(db_session)
    schedule_before = retry_service.get_retry_schedule_for_mandate(mandate.id)
    assert schedule_before is not None
    # Snapshot plain values — `schedule_before` and any later read share the
    # same session identity map, so the ORM object itself would reflect the
    # post-run mutation too, making a stale-object comparison meaningless.
    retry_count_before = schedule_before.retry_count
    recommended_time_before = schedule_before.recommended_time
    attempts_before = len(payment_service.list_attempts(mandate.id))

    runner = WorkflowRunnerService(db_session)
    state = runner.run_for_mandate(mandate.id)

    assert state.final_decision is not None
    assert state.final_decision.retry.allowed is True
    assert len(payment_service.list_attempts(mandate.id)) == attempts_before + 1

    schedule_after = retry_service.get_retry_schedule_for_mandate(mandate.id)
    assert schedule_after is not None
    assert schedule_after.retry_count == retry_count_before + 1
    assert schedule_after.status == RetryStatus.PENDING
    assert schedule_after.recommended_time > recommended_time_before


def test_run_for_mandate_exhausts_the_schedule_on_the_final_allowed_retry(db_session: Session) -> None:
    mandate = _make_mandate_with_failed_attempt(db_session)
    retry_service = RetryService(db_session)
    schedule = retry_service.get_retry_schedule_for_mandate(mandate.id)
    assert schedule is not None
    retry_service.update_retry_schedule(schedule.id, retry_count=2, max_retries=3)  # one retry left

    runner = WorkflowRunnerService(db_session)
    runner.run_for_mandate(mandate.id)

    schedule_after = retry_service.get_retry_schedule_for_mandate(mandate.id)
    assert schedule_after is not None
    assert schedule_after.retry_count == 3
    assert schedule_after.status == RetryStatus.EXHAUSTED


def test_run_for_mandate_sends_a_real_communication_when_recommended(db_session: Session) -> None:
    mandate = _make_mandate_with_failed_attempt(db_session)
    runner = WorkflowRunnerService(db_session)

    state = runner.run_for_mandate(mandate.id)

    assert state.final_decision is not None
    assert state.final_decision.communication.recommended is True
    communications = CommunicationService(db_session).list_communications(mandate.id)
    assert len(communications) == 1
    assert communications[0].channel.value == state.final_decision.communication.channel


def test_run_for_mandate_creates_a_real_escalation_when_required(db_session: Session) -> None:
    mandate = _make_mandate_with_bank_unavailable_failure(db_session)
    runner = WorkflowRunnerService(db_session)

    state = runner.run_for_mandate(mandate.id)

    assert state.final_decision is not None
    assert state.final_decision.escalation.required is True
    escalations = EscalationService(db_session).list_open_escalations(mandate.id)
    assert len(escalations) == 1
    assert escalations[0].escalation_level == EscalationLevel.LEVEL_2


def test_run_for_mandate_does_not_duplicate_an_already_open_escalation(db_session: Session) -> None:
    mandate_service = MandateService(db_session)
    payment_service = PaymentService(db_session)
    retry_service = RetryService(db_session)
    mandate = mandate_service.register_mandate("workflow-cust-3", "WORKFLOW-REF-3", Decimal("500.00"))
    attempt = payment_service.record_payment_attempt(mandate.id)
    payment_service.mark_payment_failure(attempt.id, decline_category=DeclineCategory.ACCOUNT_CLOSED, bank_response_message="account closed")
    schedule = retry_service.get_retry_schedule_for_mandate(mandate.id)
    assert schedule is not None
    # Exhaust retry capacity (without flipping status) so the same failed attempt
    # stays "latest" across both runs and the escalation-required decision repeats.
    retry_service.update_retry_schedule(schedule.id, retry_count=3, max_retries=3)
    runner = WorkflowRunnerService(db_session)
    first_state = runner.run_for_mandate(mandate.id)
    assert first_state.final_decision is not None
    assert first_state.final_decision.retry.allowed is False
    assert first_state.final_decision.escalation.required is True

    second_state = runner.run_for_mandate(mandate.id)

    assert second_state.final_decision is not None
    assert second_state.final_decision.escalation.required is True
    escalations = EscalationService(db_session).list_open_escalations(mandate.id)
    assert len(escalations) == 1
