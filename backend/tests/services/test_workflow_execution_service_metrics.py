"""Tests for AI-latency figures reported by WorkflowExecutionService.

record_latency()/average_latency() in backend.app.observability.metrics are
populated for real on every live AIService call (see llm/ai_service.py) —
these tests confirm that real, already-recorded data actually reaches the
observability API responses instead of being reported as a hardcoded 0.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from backend.app.models.workflow_execution import WorkflowExecution
from backend.app.observability import metrics as ai_metrics
from backend.app.services.mandate_service import MandateService
from backend.app.services.workflow_execution_service import WorkflowExecutionService


def _execution(mandate_id: uuid.UUID, *, ai_used: bool, confidence: str) -> WorkflowExecution:
    now = datetime.now(timezone.utc)
    return WorkflowExecution(
        id=uuid.uuid4(),
        workflow_id="wf-1",
        mandate_id=mandate_id,
        status="completed",
        started_at=now,
        finished_at=now,
        ai_used=ai_used,
        confidence=Decimal(confidence),
    )


def test_overview_average_confidence_only_counts_ai_enriched_executions(db_session: Session) -> None:
    """Deterministic-only runs are always persisted with a confidence of 0.0 as a
    documented placeholder (no AI was involved to have any confidence at all) —
    that placeholder must not drag down the average confidence of runs where AI
    actually ran, the same way GET /observability/provider already gets right.
    """
    mandate_id = MandateService(db_session).register_mandate("cust-1", "REF-1", Decimal("500.00")).id
    db_session.add(_execution(mandate_id, ai_used=True, confidence="0.90"))
    db_session.add(_execution(mandate_id, ai_used=False, confidence="0.00"))
    db_session.add(_execution(mandate_id, ai_used=False, confidence="0.00"))
    db_session.commit()

    overview = WorkflowExecutionService(db_session).get_overview()

    assert overview.average_confidence == 0.9


def test_overview_reports_the_real_recorded_average_ai_latency(db_session: Session) -> None:
    ai_metrics._latencies.clear()
    ai_metrics.record_latency(120.0)
    ai_metrics.record_latency(80.0)

    overview = WorkflowExecutionService(db_session).get_overview()

    assert overview.average_ai_latency_ms == 100.0


def test_metrics_reports_the_real_recorded_average_ai_latency(db_session: Session) -> None:
    ai_metrics._latencies.clear()
    ai_metrics.record_latency(50.0)

    metrics = WorkflowExecutionService(db_session).get_metrics()

    assert metrics.ai_latency_ms == 50.0


def test_provider_health_reports_the_real_recorded_failure_count(db_session: Session) -> None:
    """record_failure() fires on every real Groq call that raises (e.g. a 429
    rate-limit) — Provider Health must surface that instead of a hardcoded 0,
    or a provider that is actually failing looks silently healthy.
    """
    ai_metrics._failures = 0
    ai_metrics.record_failure()
    ai_metrics.record_failure()

    providers = WorkflowExecutionService(db_session).get_provider_health()

    assert providers[0].failures == 2
