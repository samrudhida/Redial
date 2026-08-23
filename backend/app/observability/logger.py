"""Structured logging helpers for AI requests, responses, and failures."""

from __future__ import annotations

import logging
from typing import Any

_logger = logging.getLogger("backend.app.observability.ai")


def log_request(*, trace_id: str, prompt_name: str, **fields: Any) -> None:
    _logger.info(
        "ai_request trace_id=%s prompt_name=%s",
        trace_id,
        prompt_name,
        extra={"ai_event": "request", "trace_id": trace_id, "prompt_name": prompt_name, **fields},
    )


def log_response(*, trace_id: str, latency_ms: float, success: bool, **fields: Any) -> None:
    _logger.info(
        "ai_response trace_id=%s latency_ms=%.3f success=%s",
        trace_id,
        latency_ms,
        success,
        extra={"ai_event": "response", "trace_id": trace_id, "latency_ms": latency_ms, "success": success, **fields},
    )


def log_error(*, trace_id: str, error: BaseException | str, **fields: Any) -> None:
    _logger.error(
        "ai_error trace_id=%s error=%s",
        trace_id,
        error,
        extra={"ai_event": "error", "trace_id": trace_id, "error": str(error), **fields},
    )