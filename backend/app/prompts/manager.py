"""High-level, thread-safe prompt retrieval and rendering interface."""

from __future__ import annotations

import logging
from string import Template
from threading import RLock
from typing import Any

from backend.app.prompts.loader import PromptLoader

logger = logging.getLogger(__name__)


class PromptRenderError(ValueError):
    """Raised when values required by a prompt template are missing or invalid."""


class PromptManager:
    """Retrieve, render, and reload prompt templates through a ``PromptLoader``.

    The manager keeps its own cache so rendering does not repeatedly traverse
    the loader. A loader can be injected in tests or replaced with another
    storage-backed implementation later without changing prompt consumers.
    """

    def __init__(self, loader: PromptLoader | None = None) -> None:
        self.loader = loader or PromptLoader()
        self._cache: dict[str, str] = {}
        self._lock = RLock()

    def get_prompt(self, name: str) -> str:
        """Return an unrendered template by name, loading and caching it as needed."""
        normalized_name = self.loader.normalize_name(name)
        with self._lock:
            cached_template = self._cache.get(normalized_name)
            if cached_template is not None:
                return cached_template
            template = self.loader.load_prompt(normalized_name)
            self._cache[normalized_name] = template
            return template

    def render_prompt(self, prompt_name: str, **kwargs: Any) -> str:
        """Render a template with the supplied named values using strict substitution."""
        template = self.get_prompt(prompt_name)
        try:
            return Template(template).substitute(**kwargs)
        except (KeyError, ValueError) as exc:
            logger.error("Unable to render prompt template", extra={"prompt_name": prompt_name, "provided_keys": sorted(kwargs)}, exc_info=True)
            raise PromptRenderError(f"Unable to render prompt '{prompt_name}': {exc}") from exc

    def reload_prompt(self, name: str) -> str:
        """Force a template reload from disk and update the manager cache."""
        normalized_name = self.loader.normalize_name(name)
        template = self.loader.reload_prompt(normalized_name)
        with self._lock:
            self._cache[normalized_name] = template
        return template

    def list_prompts(self) -> list[str]:
        """Return all template names currently available from the loader."""
        return self.loader.list_prompts()


prompt_manager = PromptManager()
"""Default application prompt manager used by prompt-building utilities."""
