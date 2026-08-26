"""Store the communication recommendation and actually send it when one is picked."""

from __future__ import annotations

import uuid
from typing import Protocol

from backend.app.decision_engine.context_builder import MandateSnapshot, PaymentAttemptSnapshot
from backend.app.workflow.state import WorkflowState


class CommunicationServiceProtocol(Protocol):
    """Minimal dependency contract required by this node."""

    def record_sms(self, mandate_id: uuid.UUID, message: str, *, template_name: str | None = None) -> object:
        raise NotImplementedError

    def record_email(self, mandate_id: uuid.UUID, message: str, *, template_name: str | None = None) -> object:
        raise NotImplementedError

    def record_whatsapp(self, mandate_id: uuid.UUID, message: str, *, template_name: str | None = None) -> object:
        raise NotImplementedError


def run(state: WorkflowState, *, communication_service: CommunicationServiceProtocol | None = None) -> WorkflowState:
    """Store the already-selected communication recommendation and act on it.

    Uses a simple deterministic template rather than an AI-generated message —
    this keeps the workflow to the one Groq call it already makes for the
    retry decision, instead of a second call per run.
    """
    if state.final_decision is None:
        raise ValueError("WorkflowState.final_decision is required")
    plan = state.final_decision.communication
    state.communication_plan = plan

    if plan.recommended and plan.channel != "none" and communication_service is not None and state.decision_context is not None:
        mandate = state.decision_context.mandate
        message = _build_message(mandate, state.decision_context.latest_payment_attempt)
        _send(communication_service, plan.channel, uuid.UUID(mandate.id), message)

    state.advance_step("communication", status="communication_ready")
    state.add_history("communication", "completed")
    return state


def _send(communication_service: CommunicationServiceProtocol, channel: str, mandate_id: uuid.UUID, message: str) -> None:
    if channel == "sms":
        communication_service.record_sms(mandate_id, message)
    elif channel == "email":
        communication_service.record_email(mandate_id, message)
    elif channel == "whatsapp":
        communication_service.record_whatsapp(mandate_id, message)


def _build_message(mandate: MandateSnapshot, latest_attempt: PaymentAttemptSnapshot | None) -> str:
    reason_suffix = f" ({latest_attempt.bank_response_message})" if latest_attempt and latest_attempt.bank_response_message else ""
    return (
        f"Hi, we noticed your recent payment of {mandate.currency} {mandate.amount} for mandate "
        f"{mandate.mandate_reference} could not be processed{reason_suffix}. We'll automatically retry shortly."
    )
