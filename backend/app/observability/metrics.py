"""Thread-safe, process-local AI execution metrics."""

from __future__ import annotations

from threading import Lock

_lock = Lock()
_latencies: list[float] = []
_successes = 0
_failures = 0


def record_latency(latency_ms: float) -> None:
    with _lock:
        _latencies.append(latency_ms)


def record_failure() -> None:
    global _failures
    with _lock:
        _failures += 1


def record_success() -> None:
    global _successes
    with _lock:
        _successes += 1


def average_latency() -> float:
    with _lock:
        return sum(_latencies) / len(_latencies) if _latencies else 0.0


def failure_rate() -> float:
    with _lock:
        total = _successes + _failures
        return _failures / total if total else 0.0


def failure_count() -> int:
    with _lock:
        return _failures