"""In-memory traces for AI provider executions.

The recorder deliberately has no persistence or provider-specific dependencies.
Applications can read the recorded traces and export them to a dashboard or
analytics system at a later composition boundary.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from time import perf_counter
from typing import Any
from uuid import uuid4


def _preview(value: str | None, limit: int = 500) -> str | None:
    if value is None:
        return None
    return value if len(value) <= limit else f"{value[:limit]}..."


@dataclass
class AITrace:
    """Metadata captured for one AI request and response pair."""

    trace_id: str
    timestamp: datetime
    provider: str | None
    model: str | None
    prompt_name: str
    prompt_preview: str | None = None
    response_preview: str | None = None
    latency_ms: float | None = None
    success: bool | None = None
    confidence: float | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class AITraceRecorder:
    """Record AI execution metadata in a thread-safe in-memory collection."""

    def __init__(self, *, max_traces: int | None = None) -> None:
        self.max_traces = max_traces
        self._traces: list[AITrace] = []
        self._start_times: dict[str, float] = {}
        self._lock = Lock()

    @property
    def traces(self) -> list[AITrace]:
        """Return a snapshot so callers cannot mutate recorder state."""
        with self._lock:
            return list(self._traces)

    def start_trace(
        self,
        *,
        provider: str | None,
        model: str | None,
        prompt_name: str,
        prompt: str,
        metadata: dict[str, Any] | None = None,
    ) -> AITrace:
        trace = AITrace(
            trace_id=str(uuid4()),
            timestamp=datetime.now(timezone.utc),
            provider=provider,
            model=model,
            prompt_name=prompt_name,
            prompt_preview=_preview(prompt),
            metadata=dict(metadata or {}),
        )
        with self._lock:
            self._start_times[trace.trace_id] = perf_counter()
            self._traces.append(trace)
            self._trim_locked()
        return trace

    def finish_trace(
        self,
        trace: AITrace,
        *,
        response: str,
        confidence: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AITrace:
        with self._lock:
            trace.response_preview = _preview(response)
            trace.latency_ms = self._elapsed_ms_locked(trace.trace_id)
            trace.success = True
            trace.confidence = confidence
            if metadata:
                trace.metadata.update(metadata)
        return trace

    def record_failure(
        self,
        trace: AITrace,
        error: BaseException | str,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> AITrace:
        with self._lock:
            trace.latency_ms = self._elapsed_ms_locked(trace.trace_id)
            trace.success = False
            trace.error = str(error)
            if metadata:
                trace.metadata.update(metadata)
        return trace

    def _elapsed_ms_locked(self, trace_id: str) -> float:
        start_time = self._start_times.pop(trace_id, perf_counter())
        return round((perf_counter() - start_time) * 1000, 3)

    def _trim_locked(self) -> None:
        if self.max_traces is not None and self.max_traces > 0:
            del self._traces[:-self.max_traces]