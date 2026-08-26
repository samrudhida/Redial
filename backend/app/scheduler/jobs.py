"""The retry-scheduler's periodic job: find due retries and run the real workflow for each.

Runs outside any HTTP request, so it opens and closes its own database
session rather than relying on FastAPI's request-scoped ``get_db``.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy.orm import Session

from backend.app.api.dependencies import resolve_ai_service
from backend.app.config.settings import get_settings
from backend.app.database.database import SessionLocal
from backend.app.services.retry_service import RetryService
from backend.app.services.workflow_runner_service import WorkflowRunnerService

logger = logging.getLogger(__name__)


@dataclass
class RetryBatchResult:
    """Outcome of one scheduler tick, for logging and tests."""

    attempted: int = 0
    succeeded: int = 0
    failed: int = 0


def run_due_retries(*, session_factory: Callable[[], Session] = SessionLocal) -> RetryBatchResult:
    """Re-run the AI/decision workflow for every mandate whose retry is due.

    One mandate's failure is logged and skipped rather than aborting the
    whole batch — a single broken mandate must never block every other
    due retry from being processed.
    """
    settings = get_settings()
    ai_service, fallback_reason = resolve_ai_service(settings)
    if fallback_reason is not None:
        logger.info("Retry scheduler running without AI enrichment: %s", fallback_reason)

    session = session_factory()
    try:
        due_schedules = RetryService(session).get_due_retries()
        result = RetryBatchResult(attempted=len(due_schedules))
        if not due_schedules:
            return result

        runner = WorkflowRunnerService(session, ai_service=ai_service)
        for schedule in due_schedules:
            mandate_id: uuid.UUID = schedule.mandate_id
            try:
                runner.run_for_mandate(mandate_id)
                result.succeeded += 1
            except Exception:
                logger.exception("Scheduled retry failed for mandate %s", mandate_id)
                result.failed += 1
        return result
    finally:
        session.close()
