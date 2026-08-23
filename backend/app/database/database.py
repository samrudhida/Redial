"""
app/database/database.py
────────────────────────
SQLAlchemy engine and session factory — the core of the database layer.

Responsibility:
  This file owns two objects that everything else in the database layer
  depends on:
    1. `engine`        — the long-lived connection pool to PostgreSQL.
    2. `SessionLocal`  — a factory that stamps out new DB sessions on demand.

Why is this separate from session.py?
  - `database.py` is infrastructure (engine, pool, config).
  - `session.py` is a FastAPI integration concern (get_db dependency).
  Splitting them means test code can import `engine` or `SessionLocal`
  directly without pulling in FastAPI's Depends machinery.

SQLAlchemy 2.x style:
  We use `create_engine()` with `future=True` to opt into SQLAlchemy 2.x
  behaviour while the package version may still be 1.4.x in some envs.
  This ensures forward-compatibility.

Connection pool notes:
  - `pool_size`    : persistent connections kept open (reused across requests).
  - `max_overflow` : extra connections allowed above pool_size under load.
  - `pool_pre_ping`: sends a lightweight SELECT before every checkout to
                     detect stale connections (important after DB restarts).
  - `echo`         : prints every SQL statement — enable in DEBUG only.
                     Never enable in production (security + performance).
"""

import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# ─────────────────────────────────────────────────────────────────────────────
# Engine
#
# `create_engine` creates a connection pool — NOT a single connection.
# FastAPI's thread-based workers share this pool; SQLAlchemy is thread-safe.
#
# `future=True` activates SQLAlchemy 2.x Core / ORM behaviour:
#   - `session.execute(select(...))` instead of `session.query(...)`
#   - `text()` must be used for raw SQL strings
# ─────────────────────────────────────────────────────────────────────────────
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,       # Verify connection health before each checkout
    echo=settings.DEBUG,      # Log SQL only in DEBUG mode — never in prod
    future=True,              # SQLAlchemy 2.x compatibility mode
)

logger.debug(
    "SQLAlchemy engine created | pool_size=%d | max_overflow=%d | echo=%s",
    settings.DATABASE_POOL_SIZE,
    settings.DATABASE_MAX_OVERFLOW,
    settings.DEBUG,
)


# ─────────────────────────────────────────────────────────────────────────────
# SessionLocal
#
# `sessionmaker` is a factory class. Calling `SessionLocal()` creates a new
# Session object bound to our engine.
#
# autocommit=False  → transactions must be explicitly committed (safe default).
# autoflush=False   → don't auto-flush pending changes before every query;
#                     gives us explicit control over when SQL is sent to DB.
# bind=engine       → all sessions from this factory use our engine.
# ─────────────────────────────────────────────────────────────────────────────
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)
