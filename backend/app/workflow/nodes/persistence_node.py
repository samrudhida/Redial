"""Execute the retry decision (when allowed), then persist through an injected adapter."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Protocol

from backend.app.models.enums import RetryStatus
from backend.app.workflow.state import WorkflowState

_BASE_RETRY_DELAY = timedelta(hours=24)


class PersistenceServiceProtocol(Protocol):
    """Minimal service-layer contract for one workflow persistence operation."""

    def persist_workflow(self, state: WorkflowState) -> None:
        """Persist the supplied state and commit once."""


class PaymentServiceProtocol(Protocol):
    """Minimal dependency contract for booking the next retry attempt."""

    def record_payment_attempt(self, mandate_id: uuid.UUID) -> object:
        raise NotImplementedError


class RetryServiceProtocol(Protocol):
    """Minimal dependency contract for advancing the retry schedule."""

    def update_retry_schedule(
        self,
        retry_schedule_id: uuid.UUID,
        *,
        retry_strategy: str | None = None,
        recommended_time: datetime | None = None,
        actual_retry_time: datetime | None = None,
        retry_count: int | None = None,
        max_retries: int | None = None,
        status: RetryStatus | None = None,
    ) -> object:
        raise NotImplementedError


def run(
    state: WorkflowState,
    *,
    service: PersistenceServiceProtocol,
    payment_service: PaymentServiceProtocol | None = None,
    retry_service: RetryServiceProtocol | None = None,
) -> WorkflowState:
    """Execute the retry decision, then persist through the injected service — never through a repository."""
    _execute_retry_if_allowed(state, payment_service=payment_service, retry_service=retry_service)
    service.persist_workflow(state)
    state.advance_step("persistence", status="persisted")
    state.add_history("persistence", "completed")
    return state


def _execute_retry_if_allowed(
    state: WorkflowState,
    *,
    payment_service: PaymentServiceProtocol | None,
    retry_service: RetryServiceProtocol | None,
) -> None:
    if state.final_decision is None or state.decision_context is None:
        return
    retry = state.final_decision.retry
    schedule = state.decision_context.retry_schedule
    if not retry.allowed or schedule is None or payment_service is None or retry_service is None:
        return

    mandate_id = uuid.UUID(state.decision_context.mandate.id)
    payment_service.record_payment_attempt(mandate_id)

    new_retry_count = schedule.retry_count + 1
    now = datetime.now(timezone.utc)
    if new_retry_count >= schedule.max_retries:
        retry_service.update_retry_schedule(uuid.UUID(schedule.id), retry_count=new_retry_count, status=RetryStatus.EXHAUSTED, actual_retry_time=now)
        return

    next_delay = _BASE_RETRY_DELAY * (2**new_retry_count)
    retry_service.update_retry_schedule(uuid.UUID(schedule.id), retry_count=new_retry_count, actual_retry_time=now, recommended_time=now + next_delay)
