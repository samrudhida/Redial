"""FastAPI dependency providers for request-scoped services and workflows."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Protocol

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.config.settings import Settings, get_settings
from backend.app.database.session import get_db
from backend.app.llm.ai_service import AIService
from backend.app.llm.providers import ProviderError
from backend.app.llm.registry import registry
from backend.app.observability.ai_trace import AITraceRecorder
from backend.app.payments.razorpay_client import RazorpayClient, RazorpayError
from backend.app.services.communication_service import CommunicationService
from backend.app.services.dashboard_service import DashboardService
from backend.app.services.decision_service import DecisionService
from backend.app.services.dev_seed_service import DevSeedService
from backend.app.services.escalation_service import EscalationService
from backend.app.services.mandate_service import MandateService
from backend.app.services.payment_service import PaymentService
from backend.app.services.razorpay_service import RazorpayService
from backend.app.services.retry_service import RetryService
from backend.app.services.workflow_execution_service import WorkflowExecutionService
from backend.app.services.workflow_runner_service import WorkflowRunnerService
from backend.app.workflow.builder import WorkflowBuilder
from backend.app.workflow.graph import WorkflowGraph

logger = logging.getLogger(__name__)


class WorkflowDependencies(Protocol):
    """Application composition contract required to construct a workflow."""

    decision_orchestrator: object
    persistence_adapter: object


def get_mandate_service(db: Session = Depends(get_db)) -> MandateService:
    """Provide one mandate service backed by the request database session."""
    return MandateService(db)


def resolve_razorpay_client(settings: Settings) -> tuple[RazorpayClient | None, str | None]:
    """Build a RazorpayClient when credentials are configured, or report why it fell back.

    Returns (client, fallback_reason). Never raises: missing credentials or
    any construction failure fall back to (None, reason) so every caller
    keeps working in demo mode — payment attempts are simulated exactly as
    before, and webhook signatures are treated as unverifiable rather than
    crashing the endpoint.
    """
    if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
        return None, "RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET are not configured"
    try:
        return RazorpayClient(settings=settings), None
    except RazorpayError as exc:
        return None, f"Razorpay client could not be constructed: {exc}"
    except Exception as exc:  # noqa: BLE001 - Razorpay must never take the app down
        return None, f"Unexpected error constructing the Razorpay client: {exc}"


def get_razorpay_client(settings: Settings = Depends(get_settings)) -> RazorpayClient | None:
    """Build the configured RazorpayClient when available, or None to keep demo-mode behavior."""
    client, reason = resolve_razorpay_client(settings)
    if reason is not None:
        logger.warning("Razorpay disabled; continuing in demo mode: %s", reason)
    return client


def get_payment_service(db: Session = Depends(get_db), razorpay_client: RazorpayClient | None = Depends(get_razorpay_client)) -> PaymentService:
    """Provide one payment service backed by the request database session."""
    return PaymentService(db, razorpay_client=razorpay_client)


def get_razorpay_service(db: Session = Depends(get_db), razorpay_client: RazorpayClient | None = Depends(get_razorpay_client)) -> RazorpayService:
    """Provide one Razorpay webhook-ingestion service backed by the request database session."""
    return RazorpayService(db, razorpay_client, payment_service=PaymentService(db, razorpay_client=razorpay_client))


def get_retry_service(db: Session = Depends(get_db)) -> RetryService:
    """Provide one retry service backed by the request database session."""
    return RetryService(db)


def get_communication_service(db: Session = Depends(get_db)) -> CommunicationService:
    """Provide one communication service backed by the request database session."""
    return CommunicationService(db)


def get_decision_service(db: Session = Depends(get_db)) -> DecisionService:
    """Provide one decision service backed by the request database session."""
    return DecisionService(db)


def get_escalation_service(db: Session = Depends(get_db)) -> EscalationService:
    """Provide one escalation service backed by the request database session."""
    return EscalationService(db)


def get_dashboard_service(db: Session = Depends(get_db)) -> DashboardService:
    """Provide one dashboard aggregation service backed by the request database session."""
    return DashboardService(
        mandate_service=MandateService(db),
        payment_service=PaymentService(db),
        retry_service=RetryService(db),
        escalation_service=EscalationService(db),
        decision_service=DecisionService(db),
        communication_service=CommunicationService(db),
    )


def get_dev_seed_service(db: Session = Depends(get_db)) -> DevSeedService:
    """Provide one developer-only demo-data seeding service backed by the request database session."""
    return DevSeedService(db)


def get_workflow_execution_service(db: Session = Depends(get_db)) -> WorkflowExecutionService:
    """Provide one workflow-execution observability service backed by the request database session."""
    return WorkflowExecutionService(db)


def resolve_ai_service(settings: Settings) -> tuple[AIService | None, str | None]:
    """Resolve the configured provider through the registry, or report why it fell back.

    Returns (ai_service, fallback_reason). Never raises: an unregistered
    provider name, a construction failure (e.g. missing/invalid key), or any
    other error all fall back to (None, reason) so the workflow continues on
    deterministic policy alone.
    """
    try:
        llm = registry.get_provider(settings.LLM_PROVIDER, settings=settings)
    except LookupError:
        return None, f"LLM provider '{settings.LLM_PROVIDER}' is not registered"
    except ProviderError as exc:
        return None, f"LLM provider '{settings.LLM_PROVIDER}' could not be constructed: {exc}"
    except Exception as exc:  # noqa: BLE001 - AI must never take the workflow down
        return None, f"Unexpected error constructing LLM provider '{settings.LLM_PROVIDER}': {exc}"
    return AIService(llm=llm, recorder=AITraceRecorder()), None


def get_ai_service(settings: Settings = Depends(get_settings)) -> AIService | None:
    """Build the configured AIService when available, or None to keep deterministic-only behavior."""
    ai_service, reason = resolve_ai_service(settings)
    if reason is not None:
        logger.warning("AI disabled; falling back to deterministic-only decisions: %s", reason)
    return ai_service


def get_workflow_runner_service(db: Session = Depends(get_db), ai_service: AIService | None = Depends(get_ai_service)) -> WorkflowRunnerService:
    """Provide one workflow-runner service (the real, wired workflow graph) backed by the request database session."""
    return WorkflowRunnerService(db, ai_service=ai_service)


def get_workflow() -> WorkflowGraph:
    """Resolve a configured workflow or report missing composition wiring."""
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Workflow dependencies are not configured in the application composition root",
    )


def workflow_dependency_factory(
    *,
    decision_orchestrator: object,
    persistence_adapter: object,
    observability_adapter: object | None = None,
) -> Callable[[], WorkflowGraph]:
    """Create a FastAPI-compatible workflow dependency for an app composition root."""
    builder = WorkflowBuilder(
        decision_orchestrator=decision_orchestrator,  # type: ignore[arg-type]
        persistence_adapter=persistence_adapter,  # type: ignore[arg-type]
        observability_adapter=observability_adapter,  # type: ignore[arg-type]
    )
    workflow = builder.build()
    return lambda: workflow