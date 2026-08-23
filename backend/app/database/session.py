"""
app/database/session.py
───────────────────────
FastAPI database session dependency — the bridge between HTTP requests
and the SQLAlchemy connection pool.

How FastAPI dependency injection works here:
  1. A request arrives at a route handler.
  2. FastAPI calls `get_db()` because the handler declares:
         db: Session = Depends(get_db)
  3. `get_db()` creates a fresh Session from SessionLocal.
  4. The `yield` hands the session to the route handler.
  5. The route handler runs its logic (query, insert, update).
  6. FastAPI executes the `finally` block after the response is sent,
     closing the session and returning the connection to the pool.

Why `try / finally` instead of just `yield`?
  If the route handler raises an exception, code after a bare `yield`
  would NOT run. The `finally` block runs unconditionally — guaranteeing
  that every session is closed even when things go wrong.
  An unclosed session leaks a connection from the pool. Under load,
  this exhausts the pool and hangs all new requests.

Usage in a route handler (added in Step 5):
    from sqlalchemy.orm import Session
    from fastapi import Depends
    from backend.app.database.session import get_db

    @router.get("/mandates")
    def list_mandates(db: Session = Depends(get_db)):
        return db.execute(select(Mandate)).scalars().all()
"""

import logging
from typing import Generator

from sqlalchemy.orm import Session

from backend.app.database.database import SessionLocal

logger = logging.getLogger(__name__)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides a scoped database session.

    One session is created per request and guaranteed to be closed
    after the response is delivered, even if an exception was raised.

    Yields:
        Session: An active SQLAlchemy ORM session bound to the engine.
    """
    db: Session = SessionLocal()
    try:
        logger.debug("Database session opened.")
        yield db
    finally:
        db.close()
        logger.debug("Database session closed.")
