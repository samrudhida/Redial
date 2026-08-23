"""Provider-independent interface for future LLM adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseLLM(ABC):
    """Contract implemented by all synchronous LLM provider adapters.

    Provider-specific concerns such as SDK clients, authentication, retries,
    and model parameters belong in subclasses. Callers interact only with
    this interface and therefore do not depend on a particular LLM vendor.
    """

    @abstractmethod
    def generate(self, prompt: str, *, system_prompt: str | None = None, **options: Any) -> str:
        """Generate a raw text response for a fully rendered prompt."""

    @abstractmethod
    def health_check(self) -> bool:
        """Return whether the provider is reachable and ready to serve requests."""

    @abstractmethod
    def get_model_name(self) -> str:
        """Return the provider's configured model identifier for observability."""
