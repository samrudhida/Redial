"""Typed, provider-neutral context assembly for decision workflows."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from backend.app.models.communication import Communication
from backend.app.models.decision_log import DecisionLog
from backend.app.models.mandate import Mandate
from backend.app.models.payment_attempt import PaymentAttempt
from backend.app.models.retry_schedule import RetrySchedule
from backend.app.services.decision_service import DecisionService
from backend.app.services.mandate_service import MandateService
from backend.app.services.payment_service import PaymentService


class MandateSnapshot(BaseModel):
    """Decision-relevant, non-sensitive representation of a payment mandate."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    customer_id: str
    mandate_reference: str
    amount: Decimal
    currency: str
    bank_name: str | None = None
    account_last4: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime


class PaymentAttemptSnapshot(BaseModel):
    """Decision-relevant representation of the latest payment attempt."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    attempt_number: int
    attempted_at: datetime
    amount: Decimal
    status: str
    bank_response_code: str | None = None
    bank_response_message: str | None = None
    decline_category: str | None = None
    next_retry_at: datetime | None = None


class RetryScheduleSnapshot(BaseModel):
    """Decision-relevant representation of the current retry plan."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    retry_strategy: str
    recommended_time: datetime
    actual_retry_time: datetime | None = None
    retry_count: int
    max_retries: int
    status: str


class DecisionHistoryItem(BaseModel):
    """Compact historical AI-decision record available to the decision engine."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    decision_type: str
    explanation: str
    confidence_score: Decimal
    created_at: datetime


class CommunicationHistoryItem(BaseModel):
    """Compact communication record used to avoid inappropriate channel choices."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    channel: str
    template_name: str | None = None
    sent_at: datetime
    delivery_status: str


class DecisionContext(BaseModel):
    """All structured facts considered by deterministic and future AI decisions."""

    model_config = ConfigDict(extra="forbid")

    mandate: MandateSnapshot
    latest_payment_attempt: PaymentAttemptSnapshot | None = None
    retry_schedule: RetryScheduleSnapshot | None = None
    decision_history: list[DecisionHistoryItem] = Field(default_factory=list)
    communication_history: list[CommunicationHistoryItem] = Field(default_factory=list)
    additional_context: dict[str, Any] = Field(default_factory=dict)


class ContextBuilder:
    """Assemble immutable decision context without any ORM query construction.

    Persistence reads are delegated to injected services. Callers may supply
    retry schedules and history collections when their workflow has already
    obtained them through service-level use cases.
    """

    def __init__(self, mandate_service: MandateService, payment_service: PaymentService, decision_service: DecisionService) -> None:
        self.mandate_service = mandate_service
        self.payment_service = payment_service
        self.decision_service = decision_service

    def build_context(self, mandate: Mandate, *, latest_payment_attempt: PaymentAttempt | None = None, retry_schedule: RetrySchedule | None = None, decision_history: Sequence[DecisionLog] = (), communication_history: Sequence[Communication] = (), additional_context: dict[str, Any] | None = None) -> DecisionContext:
        """Build a typed context from explicitly supplied domain records."""
        return DecisionContext(
            mandate=self._mandate_snapshot(mandate),
            latest_payment_attempt=self._attempt_snapshot(latest_payment_attempt) if latest_payment_attempt else None,
            retry_schedule=self._retry_schedule_snapshot(retry_schedule) if retry_schedule else None,
            decision_history=[self._decision_history_item(item) for item in decision_history],
            communication_history=[self._communication_history_item(item) for item in communication_history],
            additional_context=dict(additional_context or {}),
        )

    def build_for_mandate(self, mandate_id: uuid.UUID, *, retry_schedule: RetrySchedule | None = None, decision_history: Sequence[DecisionLog] = (), communication_history: Sequence[Communication] = (), additional_context: dict[str, Any] | None = None) -> DecisionContext:
        """Fetch available current records through services and assemble their context.

        Existing services expose the mandate, its latest attempt, and latest
        decision. Full histories and the current schedule are intentionally
        accepted as inputs until their dedicated service read use cases exist.
        """
        mandate = self.mandate_service.get_mandate(mandate_id)
        latest_attempt = self.payment_service.get_latest_attempt(mandate_id)
        latest_decision = self.decision_service.get_latest_decision(mandate_id)
        combined_decision_history = list(decision_history)
        if latest_decision is not None and all(item.id != latest_decision.id for item in combined_decision_history):
            combined_decision_history.append(latest_decision)
        return self.build_context(mandate, latest_payment_attempt=latest_attempt, retry_schedule=retry_schedule, decision_history=combined_decision_history, communication_history=communication_history, additional_context=additional_context)

    @staticmethod
    def _mandate_snapshot(mandate: Mandate) -> MandateSnapshot:
        return MandateSnapshot(id=str(mandate.id), customer_id=mandate.customer_id, mandate_reference=mandate.mandate_reference, amount=mandate.amount, currency=mandate.currency, bank_name=mandate.bank_name, account_last4=mandate.account_last4, status=mandate.status.value, created_at=mandate.created_at, updated_at=mandate.updated_at)

    @staticmethod
    def _attempt_snapshot(attempt: PaymentAttempt) -> PaymentAttemptSnapshot:
        return PaymentAttemptSnapshot(id=str(attempt.id), attempt_number=attempt.attempt_number, attempted_at=attempt.attempted_at, amount=attempt.amount, status=attempt.status.value, bank_response_code=attempt.bank_response_code, bank_response_message=attempt.bank_response_message, decline_category=attempt.decline_category.value if attempt.decline_category else None, next_retry_at=attempt.next_retry_at)

    @staticmethod
    def _retry_schedule_snapshot(schedule: RetrySchedule) -> RetryScheduleSnapshot:
        return RetryScheduleSnapshot(id=str(schedule.id), retry_strategy=schedule.retry_strategy, recommended_time=schedule.recommended_time, actual_retry_time=schedule.actual_retry_time, retry_count=schedule.retry_count, max_retries=schedule.max_retries, status=schedule.status.value)

    @staticmethod
    def _decision_history_item(decision: DecisionLog) -> DecisionHistoryItem:
        return DecisionHistoryItem(id=str(decision.id), decision_type=decision.decision_type, explanation=decision.explanation, confidence_score=decision.confidence_score, created_at=decision.created_at)

    @staticmethod
    def _communication_history_item(communication: Communication) -> CommunicationHistoryItem:
        return CommunicationHistoryItem(id=str(communication.id), channel=communication.channel.value, template_name=communication.template_name, sent_at=communication.sent_at, delivery_status=communication.delivery_status.value)
