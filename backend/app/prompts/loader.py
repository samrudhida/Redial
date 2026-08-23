"""Thread-safe, disk-backed loading for prompt templates."""

from __future__ import annotations

import logging
from pathlib import Path
from threading import RLock

logger = logging.getLogger(__name__)


class PromptError(RuntimeError):
    """Base exception for prompt-template loading and rendering failures."""


class PromptNotFoundError(PromptError):
    """Raised when a requested prompt template does not exist on disk."""


class PromptLoadError(PromptError):
    """Raised when an existing prompt template cannot be read as UTF-8 text."""


class PromptLoader:
    """Load UTF-8 prompt templates from a fixed directory with in-memory caching.

    ``base_directory`` is injectable so tests can use an isolated temporary
    directory. An ``RLock`` protects both cache reads and cache invalidation
    when the same loader is used by concurrent request handlers.
    """

    def __init__(self, base_directory: Path | str | None = None) -> None:
        self.base_directory = Path(base_directory) if base_directory is not None else Path(__file__).resolve().parent
        self._cache: dict[str, str] = {}
        self._lock = RLock()

    def load_prompt(self, name: str) -> str:
        """Return a cached prompt template, loading it from disk on first use."""
        normalized_name = self.normalize_name(name)
        with self._lock:
            cached_template = self._cache.get(normalized_name)
            if cached_template is not None:
                return cached_template
            template = self._read_prompt(normalized_name)
            self._cache[normalized_name] = template
            return template

    def reload_prompt(self, name: str) -> str:
        """Force a disk read and replace the cached template for ``name``."""
        normalized_name = self.normalize_name(name)
        with self._lock:
            template = self._read_prompt(normalized_name)
            self._cache[normalized_name] = template
            logger.info("Prompt template reloaded", extra={"prompt_name": normalized_name})
            return template

    def list_prompts(self) -> list[str]:
        """Return available template names without the ``.txt`` suffix."""
        try:
            return sorted(path.stem for path in self.base_directory.glob("*.txt") if path.is_file())
        except OSError as exc:
            logger.error("Unable to list prompt templates", extra={"prompt_directory": str(self.base_directory)}, exc_info=True)
            raise PromptLoadError("Unable to list prompt templates") from exc

    def _read_prompt(self, name: str) -> str:
        path = self._resolve_prompt_path(name)
        if not path.is_file():
            raise PromptNotFoundError(f"Prompt template '{name}' was not found")
        try:
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            logger.error("Prompt template is not valid UTF-8", extra={"prompt_name": name}, exc_info=True)
            raise PromptLoadError(f"Prompt template '{name}' is not valid UTF-8") from exc
        except OSError as exc:
            logger.error("Unable to read prompt template", extra={"prompt_name": name}, exc_info=True)
            raise PromptLoadError(f"Unable to read prompt template '{name}'") from exc

    def _resolve_prompt_path(self, name: str) -> Path:
        """Resolve a normalized name while preventing directory traversal."""
        base_path = self.base_directory.resolve()
        path = (base_path / f"{name}.txt").resolve()
        if path.parent != base_path:
            raise PromptError("Prompt name must resolve within the prompt directory")
        return path

    @staticmethod
    def normalize_name(name: str) -> str:
        """Normalize a bare or ``.txt`` template name and reject unsafe paths."""
        normalized_name = name.strip()
        if normalized_name.endswith(".txt"):
            normalized_name = normalized_name[:-4]
        if not normalized_name or Path(normalized_name).name != normalized_name or normalized_name in {".", ".."}:
            raise PromptError("Prompt name must be a non-empty file name without path components")
        return normalized_name
