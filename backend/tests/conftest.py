"""Shared pytest fixtures: an isolated in-memory database per test.

Every test gets a fresh SQLite schema (built from the real SQLAlchemy models,
not a hand-maintained copy) so tests never depend on execution order or leak
state into one another. The FastAPI ``get_db`` dependency is overridden to
hand out that same session, so ``client`` fixtures exercise the real
dependency-injected services against the real repository/service stack —
only the database engine underneath is swapped out.

``get_razorpay_client`` and ``get_ai_service`` are also overridden to always
return ``None``, regardless of what's in backend/.env. Without this, any API
test that records a payment attempt or triggers the workflow engine (e.g.
via the Razorpay webhook route) would make a real network call to Razorpay's
Test Mode API and/or Groq using whatever real credentials happen to be
configured locally — slow, flaky under no network, and it litters real
third-party accounts with throwaway test data on every test run.
Provider-specific behavior is covered by its own dedicated tests using an
explicit fake/injected client instead.
"""

from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.api.dependencies import get_ai_service, get_razorpay_client
from backend.app.database.base import Base
from backend.app.database.session import get_db
from backend.app.main import app

# Import every model so its table is registered on Base.metadata before create_all.
from backend.app.models import (  # noqa: F401
    communication,
    decision_log,
    escalation,
    mandate,
    payment_attempt,
    retry_schedule,
    webhook_event,
    workflow_execution,
)


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    """Yield a Session bound to a fresh in-memory SQLite schema for one test."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # SQLite ignores foreign key constraints (including ON DELETE CASCADE)
    # unless explicitly enabled per connection — without this, cascade
    # deletes that work correctly against the real Postgres database would
    # silently no-op in tests.
    event.listen(engine, "connect", lambda dbapi_connection, _: dbapi_connection.execute("PRAGMA foreign_keys=ON"))
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Yield a TestClient whose ``get_db`` dependency resolves to ``db_session``."""

    def _override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_razorpay_client] = lambda: None
    app.dependency_overrides[get_ai_service] = lambda: None
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_razorpay_client, None)
        app.dependency_overrides.pop(get_ai_service, None)
