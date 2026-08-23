"""
app/config/settings.py
─────────────────────
Central configuration module for the Mandate Retry Sequencer.

Why pydantic-settings?
  - Pydantic v2 Settings validates environment variables at startup.
  - If a required var is missing, the app crashes immediately with a clear
    error — not silently at runtime when the value is first used.
  - Values are strongly typed (int, bool, etc.) — no string bugs.

How it works:
  - `Settings` reads from environment variables OR from a `.env` file.
  - A single `get_settings()` function is cached with `@lru_cache` so the
    disk / env is only read once, regardless of how many modules import it.

env_file path:
  - Set to "backend/.env" because uvicorn is launched from the project root:
      uvicorn backend.app.main:app --reload
  - pydantic-settings resolves env_file relative to the current working
    directory (project root), so "backend/.env" is correct here.
"""

from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    All application configuration lives here.
    Add new variables here as the project grows — never scatter os.getenv()
    calls throughout business logic.
    """

    # ── Application ──────────────────────────────────────────────────────
    APP_NAME: str = Field(default="Mandate Retry Sequencer", description="Human-readable app name")
    APP_VERSION: str = Field(default="0.1.0", description="SemVer app version")
    APP_ENV: str = Field(default="development", description="Environment: development | staging | production")
    DEBUG: bool = Field(default=True, description="Enable debug mode (disable in production!)")

    # ── API ───────────────────────────────────────────────────────────────
    API_PREFIX: str = Field(default="/api/v1", description="URL prefix for all versioned API routes")

    # ── Server ────────────────────────────────────────────────────────────
    HOST: str = Field(default="0.0.0.0", description="Bind host for Uvicorn")
    PORT: int = Field(default=8000, description="Bind port for Uvicorn")

    # ── Database ──────────────────────────────────────────────────────────
    # Driver: postgresql+psycopg2 (synchronous, production-safe for FastAPI)
    # No password = Homebrew macOS peer auth (safe for local dev only).
    # Override DATABASE_URL in backend/.env for staging/production.
    DATABASE_URL: str = Field(
        default="postgresql+psycopg2://samrudhidahiwelkar@localhost:5432/mandate_retry_db",
        description="PostgreSQL connection string (psycopg2 driver)"
    )
    DATABASE_POOL_SIZE: int = Field(default=10, description="SQLAlchemy connection pool size")
    DATABASE_MAX_OVERFLOW: int = Field(default=20, description="Max overflow connections above pool size")

    # ── CORS ──────────────────────────────────────────────────────────────
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"],
        description="Allowed CORS origins for the frontend"
    )

    # ── LLM / Groq ────────────────────────────────────────────────────────
    GROQ_API_KEY: str = Field(default="", description="Groq API key — set in .env, never hardcode")
    GROQ_MODEL: str = Field(default="llama3-8b-8192", description="Default Groq model ID")
    LLM_TEMPERATURE: float = Field(default=0.0, ge=0.0, le=2.0, description="LLM temperature (0.0 = deterministic)")
    LLM_TIMEOUT: float = Field(default=30.0, gt=0.0, description="LLM request timeout in seconds")
    MAX_RETRIES: int = Field(default=2, ge=0, description="Maximum retries for transient LLM failures")
    RETRY_BACKOFF: float = Field(default=0.5, ge=0.0, description="Initial transient failure backoff in seconds")

    # ── Razorpay ──────────────────────────────────────────────────────────
    RAZORPAY_KEY_ID: str = Field(default="", description="Razorpay API Key ID")
    RAZORPAY_KEY_SECRET: str = Field(default="", description="Razorpay API Key Secret")

    # ── Scheduler ─────────────────────────────────────────────────────────
    SCHEDULER_TIMEZONE: str = Field(default="Asia/Kolkata", description="Timezone for APScheduler jobs")

    # ── Logging ───────────────────────────────────────────────────────────
    LOG_LEVEL: str = Field(default="INFO", description="Python logging level: DEBUG | INFO | WARNING | ERROR")

    # ── Pydantic Settings config ──────────────────────────────────────────
    model_config = SettingsConfigDict(
        # "backend/.env" is relative to the CWD where uvicorn is launched
        # (the project root: mandate-retry-sequencer/).
        env_file="backend/.env",
        env_file_encoding="utf-8",
        case_sensitive=False,     # DATABASE_URL == database_url in env
        extra="ignore",           # Ignore unknown env vars (safe for CI/CD)
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Returns a cached singleton of Settings.

    Usage in any module:
        from backend.app.config.settings import get_settings
        settings = get_settings()
        print(settings.DATABASE_URL)

    The @lru_cache ensures the .env file is only read once at startup.
    In tests, call get_settings.cache_clear() to reset between test runs.
    """
    return Settings()
