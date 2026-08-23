"""Template-backed utilities for constructing provider-neutral LLM prompts."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

from backend.app.prompts.manager import PromptManager, prompt_manager


def build_retry_prompt(*, payment_history: Sequence[Mapping[str, Any]], failure_reason: str, retry_count: int, customer_profile: Mapping[str, Any], manager: PromptManager | None = None) -> str:
    """Build a retry-decision prompt from structured payment and customer inputs."""
    return _render_template(
        "retry_decision",
        {
            "payment_history": [dict(item) for item in payment_history],
            "failure_reason": failure_reason,
            "retry_count": retry_count,
            "customer_profile": dict(customer_profile),
        }, manager,
    )


def build_communication_prompt(*, channel: str, customer_profile: Mapping[str, Any], mandate_context: Mapping[str, Any], communication_context: Mapping[str, Any] | None = None, manager: PromptManager | None = None) -> str:
    """Build a customer-message prompt from channel and structured context."""
    return _render_template(
        "communication_generation",
        {
            "channel": channel,
            "customer_profile": dict(customer_profile),
            "mandate_context": dict(mandate_context),
            "communication_context": dict(communication_context or {}),
        }, manager,
    )


def build_escalation_prompt(*, mandate_context: Mapping[str, Any], payment_history: Sequence[Mapping[str, Any]], escalation_context: Mapping[str, Any] | None = None, manager: PromptManager | None = None) -> str:
    """Build an escalation-analysis prompt from structured case information."""
    return _render_template(
        "escalation_analysis",
        {
            "mandate_context": dict(mandate_context),
            "payment_history": [dict(item) for item in payment_history],
            "escalation_context": dict(escalation_context or {}),
        }, manager,
    )


def _render_template(template_name: str, context: Mapping[str, Any], manager: PromptManager | None) -> str:
    """Render a template through an injectable prompt manager and JSON context."""
    serialized_context = json.dumps(context, ensure_ascii=False, default=str, indent=2)
    return (manager or prompt_manager).render_prompt(template_name, context=serialized_context)
