"""Orchestration service for prompts, future providers, parsing, and validation."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from backend.app.llm.base_llm import BaseLLM
from backend.app.llm.prompt_builder import build_communication_prompt, build_escalation_prompt, build_retry_prompt
from backend.app.llm.response_parser import parse_communication_response, parse_escalation_response, parse_retry_response
from backend.app.llm.response_validator import validate_communication_suggestion, validate_escalation_decision, validate_retry_decision
from backend.app.llm.schemas import CommunicationSuggestion, EscalationDecision, RetryDecision
from backend.app.observability.ai_trace import AITraceRecorder
from backend.app.observability.logger import log_error, log_request, log_response
from backend.app.observability.metrics import record_failure, record_latency, record_success


class AIService:
    """Coordinate the provider-neutral structured-output pipeline.

    A future composition root injects a ``BaseLLM`` adapter. Until then, the
    public generation methods intentionally fail fast instead of performing
    inference or importing a provider SDK.
    """

    def __init__(self, llm: BaseLLM | None = None, recorder: AITraceRecorder | None = None) -> None:
        self.llm = llm
        self.recorder = recorder

    def generate_retry_decision(self, *, payment_history: Sequence[Mapping[str, Any]], failure_reason: str, retry_count: int, customer_profile: Mapping[str, Any]) -> RetryDecision:
        """Build, generate, parse, and validate a structured retry decision."""
        prompt = build_retry_prompt(payment_history=payment_history, failure_reason=failure_reason, retry_count=retry_count, customer_profile=customer_profile)
        return validate_retry_decision(parse_retry_response(self._generate(prompt, prompt_name="retry_decision")))

    def generate_communication_suggestion(self, *, channel: str, customer_profile: Mapping[str, Any], mandate_context: Mapping[str, Any], communication_context: Mapping[str, Any] | None = None) -> CommunicationSuggestion:
        """Build, generate, parse, and validate a customer communication suggestion."""
        prompt = build_communication_prompt(channel=channel, customer_profile=customer_profile, mandate_context=mandate_context, communication_context=communication_context)
        return validate_communication_suggestion(parse_communication_response(self._generate(prompt, prompt_name="communication_generation")))

    def generate_escalation_decision(self, *, mandate_context: Mapping[str, Any], payment_history: Sequence[Mapping[str, Any]], escalation_context: Mapping[str, Any] | None = None) -> EscalationDecision:
        """Build, generate, parse, and validate a structured escalation decision."""
        prompt = build_escalation_prompt(mandate_context=mandate_context, payment_history=payment_history, escalation_context=escalation_context)
        return validate_escalation_decision(parse_escalation_response(self._generate(prompt, prompt_name="escalation_analysis")))

    def _generate(self, prompt: str, *, prompt_name: str) -> str:
        """Delegate generation to an injected provider or fail until one is supplied."""
        provider = getattr(self.llm, "provider", None) if self.llm else None
        model = self.llm.get_model_name() if self.llm else None
        recorder = self.recorder
        trace = recorder.start_trace(
            provider=provider,
            model=model,
            prompt_name=prompt_name,
            prompt=prompt,
        ) if recorder else None
        if trace:
            log_request(trace_id=trace.trace_id, prompt_name=prompt_name, provider=provider, model=model)
        try:
            if self.llm is None:
                raise NotImplementedError("No LLM provider is configured; inject a BaseLLM implementation")
            response = self.llm.generate(prompt)
        except Exception as exc:
            if trace is not None and recorder is not None:
                failed_trace = recorder.record_failure(trace, exc)
                record_latency(failed_trace.latency_ms or 0.0)
                record_failure()
                log_error(trace_id=trace.trace_id, error=exc)
            raise
        if trace is not None and recorder is not None:
            finished_trace = recorder.finish_trace(trace, response=response)
            record_latency(finished_trace.latency_ms or 0.0)
            record_success()
            log_response(trace_id=trace.trace_id, latency_ms=finished_trace.latency_ms or 0.0, success=True)
        return response
