"""Official Groq SDK adapter for the provider-independent LLM interface."""

from __future__ import annotations

import logging
from time import perf_counter, sleep
from typing import Any
from uuid import uuid4

from groq import (
    APIConnectionError as GroqAPIConnectionError,
    APIStatusError as GroqAPIStatusError,
    APITimeoutError as GroqAPITimeoutError,
    AuthenticationError as GroqAuthenticationError,
    Groq,
    RateLimitError as GroqRateLimitError,
)
from groq.types.chat import ChatCompletionMessageParam

from backend.app.config.settings import Settings, get_settings
from backend.app.llm.base_llm import BaseLLM
from backend.app.observability.logger import log_error, log_request, log_response

logger = logging.getLogger(__name__)


class ProviderError(Exception):
    """Base class for provider-neutral LLM failures."""


class ProviderUnavailableError(ProviderError):
    """The provider could not serve the request."""


class ProviderTimeoutError(ProviderUnavailableError):
    """The provider request exceeded its configured timeout."""


class AuthenticationError(ProviderError):
    """The provider rejected the configured credentials."""


class RateLimitError(ProviderError):
    """The provider rate limit was reached after retries were exhausted."""


class GroqLLM(BaseLLM):
    """Synchronous, thread-safe Groq adapter with bounded transient retries."""

    provider = "groq"

    def __init__(self, settings: Settings | None = None, client: Any | None = None) -> None:
        self.settings = settings or get_settings()
        self._model = self.settings.GROQ_MODEL
        self._client = client
        if self._client is None:
            if not self.settings.GROQ_API_KEY:
                raise AuthenticationError("GROQ_API_KEY is not configured")
            try:
                self._client = Groq(
                    api_key=self.settings.GROQ_API_KEY,
                    timeout=self.settings.LLM_TIMEOUT,
                    max_retries=0,
                )
            except GroqAuthenticationError as exc:
                raise AuthenticationError("Groq authentication failed") from exc
            except Exception as exc:
                raise ProviderUnavailableError("Unable to initialise the Groq client") from exc

    def generate(self, prompt: str, *, system_prompt: str | None = None, **options: Any) -> str:
        """Generate text, translating SDK errors and retrying transient failures."""
        trace_id = str(uuid4())
        started_at = perf_counter()
        client = self._client
        if client is None:
            raise ProviderUnavailableError("Groq client is not configured")
        messages: list[ChatCompletionMessageParam] = []
        if system_prompt is not None:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        request_options = {"model": self._model, "temperature": self.settings.LLM_TEMPERATURE, **options}
        log_request(trace_id=trace_id, prompt_name="groq.generate", provider="groq", model=self._model)

        for attempt in range(self.settings.MAX_RETRIES + 1):
            try:
                response = client.chat.completions.create(messages=messages, **request_options)
                content = response.choices[0].message.content
                if not isinstance(content, str):
                    raise ProviderUnavailableError("Groq returned an empty response")
                latency_ms = (perf_counter() - started_at) * 1000
                log_response(
                    trace_id=trace_id,
                    latency_ms=latency_ms,
                    success=True,
                    provider="groq",
                    model=self._model,
                    retries=attempt,
                )
                return content
            except GroqAuthenticationError as exc:
                log_error(trace_id=trace_id, error="Groq authentication failed", provider="groq", model=self._model)
                raise AuthenticationError("Groq authentication failed") from exc
            except GroqAPITimeoutError as exc:
                if attempt < self.settings.MAX_RETRIES:
                    self._backoff(attempt)
                    continue
                self._log_failure(trace_id, started_at, attempt, exc)
                raise ProviderTimeoutError("Groq request timed out") from exc
            except (GroqAPIConnectionError, GroqRateLimitError, GroqAPIStatusError) as exc:
                if self._is_transient(exc) and attempt < self.settings.MAX_RETRIES:
                    self._backoff(attempt)
                    continue
                self._log_failure(trace_id, started_at, attempt, exc)
                if isinstance(exc, GroqRateLimitError):
                    raise RateLimitError("Groq rate limit exceeded") from exc
                raise ProviderUnavailableError("Groq is temporarily unavailable") from exc
            except ProviderError:
                self._log_failure(trace_id, started_at, attempt, "empty response")
                raise
            except Exception as exc:
                self._log_failure(trace_id, started_at, attempt, exc)
                raise ProviderUnavailableError("Groq request failed") from exc

        raise ProviderUnavailableError("Groq request failed")

    def health_check(self) -> bool:
        """Check reachability and authentication without propagating failures."""
        try:
            client = self._client
            if client is None:
                return False
            client.models.list()
            return True
        except Exception as exc:
            logger.warning("Groq health check failed: %s", type(exc).__name__)
            return False

    def get_model_name(self) -> str:
        return self._model

    def _backoff(self, attempt: int) -> None:
        delay = self.settings.RETRY_BACKOFF * (2**attempt)
        if delay:
            sleep(delay)

    @staticmethod
    def _is_transient(error: BaseException) -> bool:
        if isinstance(error, (GroqAPIConnectionError, GroqRateLimitError)):
            return True
        return isinstance(error, GroqAPIStatusError) and error.status_code in {408, 429, 500, 502, 503, 504}

    @staticmethod
    def _log_failure(trace_id: str, started_at: float, retries: int, error: BaseException | str) -> None:
        log_error(
            trace_id=trace_id,
            error=error,
            provider="groq",
            latency_ms=(perf_counter() - started_at) * 1000,
            retries=retries,
        )