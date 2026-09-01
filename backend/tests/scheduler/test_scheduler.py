"""Tests for APScheduler job registration — never starts a real scheduler (see test_jobs.py for job behavior)."""

from __future__ import annotations

from backend.app.config.settings import get_settings
from backend.app.scheduler import scheduler as scheduler_module
from backend.app.scheduler.jobs import run_due_retries
from backend.app.scheduler.settlement import settle_pending_payments


def test_build_scheduler_registers_the_due_retries_job_at_the_configured_interval() -> None:
    settings = get_settings().model_copy(update={"SCHEDULER_RETRY_INTERVAL_SECONDS": 45})

    scheduler = scheduler_module._build_scheduler(settings)

    job = scheduler.get_job(scheduler_module._RETRY_JOB_ID)
    assert job is not None
    assert job.func is run_due_retries
    assert job.trigger.interval.total_seconds() == 45


def test_build_scheduler_registers_the_settlement_job_in_development(monkeypatch) -> None:
    settings = get_settings().model_copy(update={"APP_ENV": "development", "SCHEDULER_SETTLEMENT_INTERVAL_SECONDS": 30})

    scheduler = scheduler_module._build_scheduler(settings)

    job = scheduler.get_job(scheduler_module._SETTLEMENT_JOB_ID)
    assert job is not None
    assert job.func is settle_pending_payments
    assert job.trigger.interval.total_seconds() == 30


def test_build_scheduler_does_not_register_the_settlement_job_outside_development() -> None:
    settings = get_settings().model_copy(update={"APP_ENV": "production"})

    scheduler = scheduler_module._build_scheduler(settings)

    assert scheduler.get_job(scheduler_module._SETTLEMENT_JOB_ID) is None


def test_stop_scheduler_is_safe_to_call_when_nothing_is_running() -> None:
    scheduler_module._scheduler = None

    scheduler_module.stop_scheduler()  # must not raise
