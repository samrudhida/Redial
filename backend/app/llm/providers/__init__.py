"""LLM provider adapters and their registry registrations."""

from backend.app.llm.providers.groq_provider import (
    AuthenticationError,
    GroqLLM,
    ProviderError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    RateLimitError,
)
from backend.app.llm.registry import registry

registry.register_provider("groq", GroqLLM, make_default=True)

__all__ = [
    "AuthenticationError",
    "GroqLLM",
    "ProviderError",
    "ProviderTimeoutError",
    "ProviderUnavailableError",
    "RateLimitError",
]