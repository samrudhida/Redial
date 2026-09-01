"""APScheduler wiring for the background retry job.

``_build_scheduler`` is the testable unit — it registers the job but never
starts it, so tests can inspect the registration without a real background
thread ever touching the database. ``start_scheduler``/``stop_scheduler``
are the thin process-lifecycle wrappers main.py calls.
"""

from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from backend.app.config.settings import Settings, get_settings
from backend.app.scheduler.jobs import run_due_retries
from backend.app.scheduler.settlement import settle_pending_payments

logger = logging.getLogger(__name__)

_RETRY_JOB_ID = "run_due_retries"
_SETTLEMENT_JOB_ID = "settle_pending_payments"
_scheduler: BackgroundScheduler | None = None


def _build_scheduler(settings: Settings) -> BackgroundScheduler:
    """Construct a scheduler with the due-retries job registered, but not started.

    The settlement job only ever runs in development — it simulates a payment
    gateway resolving stale pending attempts, which would be actively wrong to
    run against a real, live gateway (see backend/app/scheduler/settlement.py).
    """
    scheduler = BackgroundScheduler(timezone=settings.SCHEDULER_TIMEZONE)
    scheduler.add_job(
        run_due_retries,
        trigger=IntervalTrigger(seconds=settings.SCHEDULER_RETRY_INTERVAL_SECONDS),
        id=_RETRY_JOB_ID,
        max_instances=1,
        coalesce=True,
    )
    if settings.APP_ENV == "development":
        scheduler.add_job(
            settle_pending_payments,
            trigger=IntervalTrigger(seconds=settings.SCHEDULER_SETTLEMENT_INTERVAL_SECONDS),
            id=_SETTLEMENT_JOB_ID,
            max_instances=1,
            coalesce=True,
        )
    return scheduler


def start_scheduler() -> BackgroundScheduler:
    """Start the background scheduler once per process; safe to call more than once."""
    global _scheduler
    if _scheduler is not None:
        return _scheduler
    settings = get_settings()
    _scheduler = _build_scheduler(settings)
    _scheduler.start()
    logger.info("Retry scheduler started (interval=%ss)", settings.SCHEDULER_RETRY_INTERVAL_SECONDS)
    if settings.APP_ENV == "development":
        logger.info("Dev-mode settlement job started (interval=%ss)", settings.SCHEDULER_SETTLEMENT_INTERVAL_SECONDS)
    return _scheduler


def stop_scheduler() -> None:
    """Shut down the background scheduler if one is running; safe to call when it's not."""
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Retry scheduler stopped")
