"""Docker container startup: wait for Postgres, then bring the schema to head.

Why this exists: only one Alembic migration exists in this repo
(``alembic/versions/8ace040fcca1_add_razorpay_integration.py``), and it
*adds* tables/columns on top of a base schema that was originally created via
``Base.metadata.create_all()`` during local development — it never captured
that base schema as a migration. Running `alembic upgrade head` alone against
a brand-new (empty) database would fail, since that migration's
`create_table("webhook_events")` references `payment_attempts`, which
wouldn't exist yet.

So, on a genuinely fresh database (no `alembic_version` table yet), this
script creates the full current schema from the ORM models directly, then
stamps Alembic's version table at "head" — recording that baseline as already
applied without re-running it. On every later restart, the database already
has `alembic_version`, so this just runs a normal `alembic upgrade head`,
which correctly applies any migrations added after this baseline.

This script does not touch application logic — it only prepares the schema
before backend/entrypoint.sh execs uvicorn.
"""

from __future__ import annotations

import logging
import time

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect
from sqlalchemy.exc import OperationalError

import backend.app.models  # noqa: F401 — populates Base.metadata before create_all/autogenerate
from backend.app.database.base import Base
from backend.app.database.database import engine

logging.basicConfig(level=logging.INFO, format="[%(levelname)-8s] %(name)s — %(message)s")
logger = logging.getLogger("backend.init_db")

ALEMBIC_INI_PATH = "/app/alembic.ini"


def wait_for_database(*, max_attempts: int = 30, delay_seconds: float = 2.0) -> None:
    """Block until Postgres accepts connections, or raise after max_attempts."""
    for attempt in range(1, max_attempts + 1):
        try:
            with engine.connect():
                logger.info("Database is accepting connections.")
                return
        except OperationalError:
            if attempt == max_attempts:
                logger.error("Database still unreachable after %d attempts — giving up.", max_attempts)
                raise
            logger.info("Database not ready yet (attempt %d/%d) — retrying in %.1fs...", attempt, max_attempts, delay_seconds)
            time.sleep(delay_seconds)


def ensure_schema_at_head() -> None:
    """Create the baseline schema and stamp Alembic on a fresh DB; otherwise just migrate."""
    alembic_cfg = Config(ALEMBIC_INI_PATH)
    inspector = inspect(engine)

    if inspector.has_table("alembic_version"):
        logger.info("alembic_version table found — applying any pending migrations.")
        command.upgrade(alembic_cfg, "head")
    else:
        logger.info("No alembic_version table — fresh database. Creating baseline schema from ORM models.")
        Base.metadata.create_all(bind=engine)
        command.stamp(alembic_cfg, "head")
        logger.info("Baseline schema created and stamped at head.")


def main() -> None:
    wait_for_database()
    ensure_schema_at_head()
    logger.info("Database ready.")


if __name__ == "__main__":
    main()
