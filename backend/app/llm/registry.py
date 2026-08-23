"""Registry for constructing configured LLM providers without vendor coupling."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from backend.app.llm.base_llm import BaseLLM

ProviderFactory = Callable[..., BaseLLM]


class LLMRegistry:
    """Store named provider factories and resolve the configured default.

    The registry deliberately has no built-in providers. A composition root
    can register an adapter later, then switch provider names through
    configuration without changing services, prompts, or response handling.
    """

    def __init__(self) -> None:
        self._providers: dict[str, ProviderFactory] = {}
        self._default_provider: str | None = None

    def register_provider(self, name: str, factory: ProviderFactory, *, make_default: bool = False) -> None:
        """Register a provider factory under a normalized non-empty name."""
        normalized_name = self._normalize_name(name)
        if normalized_name in self._providers:
            raise ValueError(f"LLM provider '{normalized_name}' is already registered")
        self._providers[normalized_name] = factory
        if make_default or self._default_provider is None:
            self._default_provider = normalized_name

    def set_default_provider(self, name: str) -> None:
        """Select a previously registered provider as the default provider."""
        normalized_name = self._normalize_name(name)
        if normalized_name not in self._providers:
            raise LookupError(f"LLM provider '{normalized_name}' is not registered")
        self._default_provider = normalized_name

    def get_provider(self, name: str | None = None, **factory_options: Any) -> BaseLLM:
        """Construct and return the named or default provider instance."""
        provider_name = self._normalize_name(name) if name is not None else self._default_provider
        if provider_name is None:
            raise LookupError("No LLM provider has been registered")
        try:
            factory = self._providers[provider_name]
        except KeyError as exc:
            raise LookupError(f"LLM provider '{provider_name}' is not registered") from exc
        return factory(**factory_options)

    @staticmethod
    def _normalize_name(name: str) -> str:
        normalized_name = name.strip().lower()
        if not normalized_name:
            raise ValueError("LLM provider name cannot be empty")
        return normalized_name


registry = LLMRegistry()
"""Application registry singleton; providers are registered by composition code later."""
