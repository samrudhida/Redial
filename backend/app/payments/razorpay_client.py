"""Thin httpx-based Razorpay adapter — no official SDK, matching this codebase's
existing style of hand-rolled provider clients (see backend/app/llm/providers/groq_provider.py).

Test Mode and Live Mode share the exact same API base URL; the key pair
(rzp_test_... vs rzp_live_...) is what determines which mode a request runs in.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
from decimal import Decimal
from time import perf_counter, sleep
from typing import Any
from uuid import uuid4

import httpx

from backend.app.config.settings import Settings, get_settings

logger = logging.getLogger(__name__)


class RazorpayError(Exception):
    """Base class for provider-neutral Razorpay failures."""


class RazorpayUnavailableError(RazorpayError):
    """Razorpay could not serve the request (network failure, 5xx, or exhausted retries)."""


class RazorpayTimeoutError(RazorpayUnavailableError):
    """The Razorpay request exceeded its configured timeout."""


class RazorpayAuthenticationError(RazorpayError):
    """Razorpay rejected the configured API key pair."""


class RazorpayRateLimitError(RazorpayError):
    """Razorpay's rate limit was reached after retries were exhausted."""


class RazorpayNotFoundError(RazorpayError):
    """The requested Razorpay resource (order, payment, ...) does not exist."""


class RazorpayInvalidRequestError(RazorpayError):
    """Razorpay rejected the request as malformed (4xx other than auth/rate-limit/not-found)."""


class RazorpayClient:
    """Synchronous, thread-safe Razorpay adapter with bounded transient retries."""

    provider = "razorpay"

    def __init__(self, settings: Settings | None = None, client: httpx.Client | None = None) -> None:
        self.settings = settings or get_settings()
        if not self.settings.RAZORPAY_KEY_ID or not self.settings.RAZORPAY_KEY_SECRET:
            raise RazorpayAuthenticationError("RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET are not configured")
        self._client = client or httpx.Client(
            base_url=self.settings.RAZORPAY_BASE_URL,
            auth=(self.settings.RAZORPAY_KEY_ID, self.settings.RAZORPAY_KEY_SECRET),
            timeout=self.settings.RAZORPAY_TIMEOUT,
        )

    def create_order(self, *, amount: Decimal, currency: str, receipt: str, notes: dict[str, str] | None = None) -> dict[str, Any]:
        """Create a Razorpay Order for one payment attempt.

        Amount is converted from rupees (this app's unit) to the integer
        smallest-currency-unit Razorpay requires (paise for INR).
        """
        amount_subunits = int((amount * 100).to_integral_value())
        body = {"amount": amount_subunits, "currency": currency, "receipt": receipt, "payment_capture": 1}
        if notes:
            body["notes"] = notes
        return self._request("POST", "/orders", json=body, operation="create_order")

    def fetch_payment(self, payment_id: str) -> dict[str, Any]:
        """Fetch a payment's current state directly from Razorpay (not from our own cache)."""
        return self._request("GET", f"/payments/{payment_id}", operation="fetch_payment")

    def verify_webhook_signature(self, *, raw_body: bytes, signature: str) -> bool:
        """Verify the X-Razorpay-Signature header against the raw request body.

        Uses the raw bytes, not a re-serialized/parsed body — Razorpay signs
        the exact bytes it sent, and re-serializing JSON can change byte-for-byte
        formatting (key order, spacing) even when the parsed content is identical.
        """
        if not self.settings.RAZORPAY_WEBHOOK_SECRET:
            return False
        expected = hmac.new(self.settings.RAZORPAY_WEBHOOK_SECRET.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

    def health_check(self) -> bool:
        """Check reachability and authentication without propagating failures."""
        try:
            self._request("GET", "/orders", params={"count": 1}, operation="health_check")
            return True
        except RazorpayError as exc:
            logger.warning("Razorpay health check failed: %s", type(exc).__name__)
            return False

    def _request(self, method: str, path: str, *, operation: str, json: dict[str, Any] | None = None, params: dict[str, Any] | None = None) -> dict[str, Any]:
        trace_id = str(uuid4())
        started_at = perf_counter()

        for attempt in range(self.settings.MAX_RETRIES + 1):
            try:
                response = self._client.request(method, path, json=json, params=params)
            except httpx.TimeoutException as exc:
                if attempt < self.settings.MAX_RETRIES:
                    self._backoff(attempt)
                    continue
                self._log_failure(trace_id, operation, started_at, attempt, exc)
                raise RazorpayTimeoutError(f"Razorpay request timed out during {operation}") from exc
            except httpx.HTTPError as exc:
                if attempt < self.settings.MAX_RETRIES:
                    self._backoff(attempt)
                    continue
                self._log_failure(trace_id, operation, started_at, attempt, exc)
                raise RazorpayUnavailableError(f"Razorpay is temporarily unavailable during {operation}") from exc

            if response.status_code < 300:
                self._log_success(trace_id, operation, started_at, attempt)
                return response.json()

            if response.status_code in (429, 500, 502, 503, 504) and attempt < self.settings.MAX_RETRIES:
                self._backoff(attempt)
                continue

            self._log_failure(trace_id, operation, started_at, attempt, f"HTTP {response.status_code}")
            self._raise_for_status(response, operation)

        raise RazorpayUnavailableError(f"Razorpay request failed during {operation}")

    @staticmethod
    def _raise_for_status(response: httpx.Response, operation: str) -> None:
        description = RazorpayClient._error_description(response)
        if response.status_code == 401:
            raise RazorpayAuthenticationError(f"Razorpay authentication failed during {operation}: {description}")
        if response.status_code == 404:
            raise RazorpayNotFoundError(f"Razorpay resource not found during {operation}: {description}")
        if response.status_code == 429:
            raise RazorpayRateLimitError(f"Razorpay rate limit exceeded during {operation}: {description}")
        if response.status_code >= 500:
            raise RazorpayUnavailableError(f"Razorpay is temporarily unavailable during {operation}: {description}")
        raise RazorpayInvalidRequestError(f"Razorpay rejected the request during {operation}: {description}")

    @staticmethod
    def _error_description(response: httpx.Response) -> str:
        try:
            payload = response.json()
            return str(payload.get("error", {}).get("description") or payload)
        except ValueError:
            return response.text or f"HTTP {response.status_code}"

    def _backoff(self, attempt: int) -> None:
        delay = self.settings.RETRY_BACKOFF * (2**attempt)
        if delay:
            sleep(delay)

    @staticmethod
    def _log_success(trace_id: str, operation: str, started_at: float, retries: int) -> None:
        logger.info(
            "Razorpay request succeeded",
            extra={"trace_id": trace_id, "operation": operation, "latency_ms": (perf_counter() - started_at) * 1000, "retries": retries},
        )

    @staticmethod
    def _log_failure(trace_id: str, operation: str, started_at: float, retries: int, error: BaseException | str) -> None:
        logger.error(
            "Razorpay request failed",
            extra={"trace_id": trace_id, "operation": operation, "latency_ms": (perf_counter() - started_at) * 1000, "retries": retries, "error": str(error)},
        )
