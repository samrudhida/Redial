"""
app/utils/logging.py
────────────────────
Centralised logging configuration for the entire application.

Why a dedicated logging module?
  - Python's default logging setup is bare-bones.
  - We want consistent log format, level, and output across all modules.
  - A single call to `setup_logging()` in main.py bootstraps everything.
  - Individual modules just do: `logger = logging.getLogger(__name__)`
    and they inherit this configuration automatically.

Log format:
  [LEVEL]  YYYY-MM-DD HH:MM:SS  module_name — message
"""

import logging
import sys
from backend.app.config.settings import get_settings

settings = get_settings()


def setup_logging() -> None:
    """
    Configure the root logger for the entire application.
    Called once during app startup in main.py.

    Design decisions:
    - Stream to stdout (not stderr) so Docker / cloud log collectors pick it up cleanly.
    - Use %(name)s to show which module emitted the log — critical for debugging.
    - Silence noisy third-party loggers (sqlalchemy.engine, httpx) unless DEBUG.
    """
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    log_format = (
        "[%(levelname)-8s]  %(asctime)s  %(name)s — %(message)s"
    )
    date_format = "%Y-%m-%d %H:%M:%S"

    logging.basicConfig(
        level=log_level,
        format=log_format,
        datefmt=date_format,
        stream=sys.stdout,
    )

    # ── Silence chatty third-party loggers in production ─────────────────
    if not settings.DEBUG:
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    else:
        # In debug mode, show SQLAlchemy queries (helpful for development)
        logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)

    logger = logging.getLogger(__name__)
    logger.info(
        "Logging initialised | level=%s | env=%s",
        settings.LOG_LEVEL,
        settings.APP_ENV,
    )
