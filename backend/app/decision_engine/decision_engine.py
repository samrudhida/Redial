"""Orchestrate typed context, deterministic policy, and optional AI enrichment."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any, Literal
import uuid

from pydantic import BaseModel, Field

from backend.app.decision_engine.communication_strategy import determine_communication_channel
from backend.app.decision_engine.context_builder import ContextBuilder, DecisionContext
from backend.app.decision_engine.escalation_strategy import determine_escalation
from backend.app.decision_engine.retry_strategy import calculate_retry_priority, calculate_retry_window, is_retry_allowed, remaining_retry_attempts
from backend.app.llm.ai_service import AIService
from backend.app.llm.response_validator import validate_retry_decision
from backend.app.llm.schemas import RetryDecision
from backend.app.models.communication import Communication
from backend.app.models.decision_log import DecisionLog
from backend.app.models.mandate import Mandate
from backend.app.models.payment_attempt import PaymentAttempt
from backend.app.models.retry_schedule import RetrySchedule


class RetryRecommendation(BaseModel):
    """Deterministic recommendation for whether and when another retry may occur."""

    allowed: bool
    priority: Literal["none", "normal", "high"]
    retry_window: datetime | None = None
    remaining_attempts: int = Field(ge=0)
    reasoning: str


class CommunicationRecommendation(BaseModel):
    """Deterministic recommendation for a customer communication channel."""

    channel: Literal["none", "sms", "email", "whatsapp"]
    recommended: bool
    reasoning: str


class EscalationRecommendation(BaseModel):
    """Deterministic recommendation for operational escalation routing."""

    escalation_type: Literal["none", "merchant", "support", "customer"]
    required: bool
    reasoning: str


class DecisionResult(BaseModel):
    """Single normalized outcome from deterministic policy and optional AI enrichment."""

    context: DecisionContext
    retry: RetryRecommendation
    communication: CommunicationRecommendation
    escalation: EscalationRecommendation
    ai_retry_decision: RetryDecision | None = None


class DecisionEngine:
    """Keep business intelligence separate from LLM provider mechanics.

    Strategies produce deterministic, testable baseline decisions. ``AIService``
    is injected solely as optional enrichment; it owns provider interaction,
    parsing, and validation, so replacing a provider never changes policy code.
    """

    def __init__(self, context_builder: ContextBuilder, ai_service: AIService | None = None) -> None:
        self.context_builder = context_builder
        self.ai_service = ai_service

    def evaluate(self, mandate: Mandate, *, latest_payment_attempt: PaymentAttempt | None = None, retry_schedule: RetrySchedule | None = None, decision_history: Sequence[DecisionLog] = (), communication_history: Sequence[Communication] = (), additional_context: Mapping[str, Any] | None = None, include_ai_decision: bool = False) -> DecisionResult:
        """Build context and return deterministic recommendations with optional AI input."""
        context = self.context_builder.build_context(mandate, latest_payment_attempt=latest_payment_attempt, retry_schedule=retry_schedule, decision_history=decision_history, communication_history=communication_history, additional_context=dict(additional_context or {}))
        result = self._build_result(context)
        if include_ai_decision:
            result.ai_retry_decision = self._generate_ai_retry_decision(context)
        return result

    def evaluate_for_mandate(self, mandate_id: uuid.UUID, *, retry_schedule: RetrySchedule | None = None, decision_history: Sequence[DecisionLog] = (), communication_history: Sequence[Communication] = (), additional_context: Mapping[str, Any] | None = None, include_ai_decision: bool = False) -> DecisionResult:
        """Build available context through injected services before evaluating a mandate."""
        context = self.context_builder.build_for_mandate(mandate_id, retry_schedule=retry_schedule, decision_history=decision_history, communication_history=communication_history, additional_context=dict(additional_context or {}))
        result = self._build_result(context)
        if include_ai_decision:
            result.ai_retry_decision = self._generate_ai_retry_decision(context)
        return result

    def _build_result(self, context: DecisionContext) -> DecisionResult:
        allowed = is_retry_allowed(context)
        retry = RetryRecommendation(allowed=allowed, priority=calculate_retry_priority(context), retry_window=calculate_retry_window(context), remaining_attempts=remaining_retry_attempts(context), reasoning=self._retry_reasoning(context, allowed))
        channel = determine_communication_channel(context)
        communication = CommunicationRecommendation(channel=channel, recommended=channel != "none", reasoning=f"Channel selected by deterministic communication policy: {channel}.")
        escalation_type = determine_escalation(context)
        escalation = EscalationRecommendation(escalation_type=escalation_type, required=escalation_type != "none", reasoning=f"Escalation selected by deterministic escalation policy: {escalation_type}.")
        return DecisionResult(context=context, retry=retry, communication=communication, escalation=escalation)

    def _generate_ai_retry_decision(self, context: DecisionContext) -> RetryDecision:
        """Request optional AI enrichment through the injected, provider-neutral AI service."""
        if self.ai_service is None:
            raise NotImplementedError("AI enrichment requires an injected AIService")
        attempt = context.latest_payment_attempt
        payment_history = [attempt.model_dump(mode="json")] if attempt else []
        failure_reason = "No payment attempt has been recorded"
        if attempt is not None:
            failure_reason = attempt.bank_response_message or attempt.decline_category or "No payment failure has been recorded"
        decision = self.ai_service.generate_retry_decision(payment_history=payment_history, failure_reason=failure_reason, retry_count=context.retry_schedule.retry_count if context.retry_schedule else 0, customer_profile={"customer_id": context.mandate.customer_id, "mandate_status": context.mandate.status, "currency": context.mandate.currency})
        return validate_retry_decision(decision)

    @staticmethod
    def _retry_reasoning(context: DecisionContext, allowed: bool) -> str:
        if allowed:
            return "The mandate and retry schedule allow another deterministic retry."
        if context.retry_schedule is None:
            return "No retry schedule is available for this mandate."
        return "Mandate state, retry schedule state, payment outcome, or retry capacity prevents another retry."
