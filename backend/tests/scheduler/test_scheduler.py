"""Tests for APScheduler job registration — never starts a real scheduler (see test_jobs.py for job behavior)."""

from __future__ import annotations

from backend.app.config.settings import get_settings
from backend.app.scheduler import scheduler as scheduler_module
from backend.app.scheduler.jobs import run_due_retries


def test_build_scheduler_registers_the_due_retries_job_at_the_configured_interval() -> None:
    settings = get_settings().model_copy(update={"SCHEDULER_RETRY_INTERVAL_SECONDS": 45})

    scheduler = scheduler_module._build_scheduler(settings)

    job = scheduler.get_job(scheduler_module._RETRY_JOB_ID)
    assert job is not None
    assert job.func is run_due_retries
    assert job.trigger.interval.total_seconds() == 45


def test_stop_scheduler_is_safe_to_call_when_nothing_is_running() -> None:
    scheduler_module._scheduler = None

    scheduler_module.stop_scheduler()  # must not raise
