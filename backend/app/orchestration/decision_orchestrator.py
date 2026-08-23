"""Coordinate deterministic decisions and provider-independent AI enrichment."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, Literal

from backend.app.decision_engine.context_builder import DecisionContext
from backend.app.decision_engine.decision_engine import DecisionResult
from backend.app.llm.ai_service import AIService
from backend.app.llm.schemas import AIResponse
from backend.app.orchestration.models import FinalDecision

DecisionType = Literal["retry_decision", "communication_generation", "escalation_analysis"]
DeterministicEvaluator = Callable[[DecisionContext], DecisionResult]


class DecisionOrchestrator:
    """Run deterministic policy first, then optionally add validated AI evidence.

    The evaluator is injected so this layer does not reach into or duplicate
    decision-engine policy. It should be a thin adapter around the engine's
    context evaluation in the application composition root.
    """

    def __init__(self, deterministic_evaluator: DeterministicEvaluator, ai_service: AIService | None = None) -> None:
        self._deterministic_evaluator = deterministic_evaluator
        self._ai_service = ai_service

    def orchestrate(self, context: DecisionContext, *, decision_type: DecisionType = "retry_decision") -> FinalDecision:
        """Return an AI-enriched decision, falling back on deterministic policy."""
        deterministic = self._deterministic_evaluator(context)
        trace_id = self._context_trace_id(context)
        if self._ai_service is None:
            return self._finalize(deterministic, ai_response=None, trace_id=trace_id, failure=None)

        try:
            ai_response = self._invoke_ai(context, deterministic, decision_type)
        except Exception as exc:
            return self._finalize(deterministic, ai_response=None, trace_id=trace_id, failure=exc)
        return self._finalize(deterministic, ai_response=ai_response, trace_id=trace_id, failure=None)

    def _invoke_ai(self, context: DecisionContext, deterministic: DecisionResult, decision_type: DecisionType) -> AIResponse:
        """Build only the selected AI workflow's context and call AIService."""
        ai_service = self._ai_service
        if ai_service is None:
            raise RuntimeError("AIService is required for AI orchestration")
        attempt = context.latest_payment_attempt
        payment_history = [attempt.model_dump(mode="json")] if attempt else []
        mandate_context = context.mandate.model_dump(mode="json")
        customer_profile = {
            "customer_id": context.mandate.customer_id,
            "mandate_status": context.mandate.status,
            "currency": context.mandate.currency,
        }
        if decision_type == "retry_decision":
            failure_reason = self._failure_reason(context)
            return ai_service.generate_retry_decision(
                payment_history=payment_history,
                failure_reason=failure_reason,
                retry_count=context.retry_schedule.retry_count if context.retry_schedule else 0,
                customer_profile=customer_profile,
            )
        if decision_type == "communication_generation":
            return ai_service.generate_communication_suggestion(
                channel=deterministic.communication.channel,
                customer_profile=customer_profile,
                mandate_context=mandate_context,
                communication_context={"history": [item.model_dump(mode="json") for item in context.communication_history]},
            )
        return ai_service.generate_escalation_decision(
            mandate_context=mandate_context,
            payment_history=payment_history,
            escalation_context={"deterministic_type": deterministic.escalation.escalation_type},
        )

    @staticmethod
    def _finalize(
        deterministic: DecisionResult,
        *,
        ai_response: AIResponse | None,
        trace_id: str | None,
        failure: Exception | None,
    ) -> FinalDecision:
        metadata: dict[str, Any] = {"deterministic": True}
        if ai_response is None:
            if failure is not None:
                metadata["ai_error"] = type(failure).__name__
            return FinalDecision(
                retry=deterministic.retry,
                communication=deterministic.communication,
                escalation=deterministic.escalation,
                confidence=0.0,
                reasoning=DecisionOrchestrator._fallback_reason(deterministic, failure),
                ai_used=False,
                trace_id=trace_id,
                metadata=metadata,
            )

        metadata.update({"ai_recommendation": ai_response.model_dump(mode="json"), "ai_metadata": ai_response.metadata})
        return FinalDecision(
            retry=deterministic.retry,
            communication=deterministic.communication,
            escalation=deterministic.escalation,
            confidence=ai_response.confidence,
            reasoning=f"{deterministic.retry.reasoning} AI enrichment: {ai_response.reasoning}",
            ai_used=True,
            trace_id=trace_id,
            metadata=metadata,
        )

    @staticmethod
    def _fallback_reason(deterministic: DecisionResult, failure: Exception | None) -> str:
        if failure is None:
            return deterministic.retry.reasoning
        return f"{deterministic.retry.reasoning} AI enrichment unavailable; deterministic recommendation retained."

    @staticmethod
    def _failure_reason(context: DecisionContext) -> str:
        attempt = context.latest_payment_attempt
        if attempt is None:
            return "No payment attempt has been recorded"
        return attempt.bank_response_message or attempt.decline_category or "No payment failure has been recorded"

    @staticmethod
    def _context_trace_id(context: DecisionContext) -> str | None:
        trace_id = context.additional_context.get("trace_id")
        return trace_id if isinstance(trace_id, str) else None