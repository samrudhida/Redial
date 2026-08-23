"""
backend/test_db.py
──────────────────
Standalone database connectivity test.

Purpose:
  A quick smoke test to verify PostgreSQL is reachable and the
  DATABASE_URL in backend/.env is correct BEFORE starting the server.

  Run this early in the setup process — it's much easier to debug
  a connection issue here (plain Python, clear error) than inside a
  running FastAPI app with multiple layers of abstraction.

Usage:
  From the project root (mandate-retry-sequencer/):
    python backend/test_db.py

What it tests:
  1. Settings load correctly from backend/.env.
  2. SQLAlchemy engine is created without errors.
  3. A real TCP connection is opened to PostgreSQL.
  4. `SELECT 1` executes successfully (minimal query, always succeeds).

This is NOT a pytest test — no test framework dependency.
It is a dev-time utility script.
"""

import sys
import os

# ── Path fix ──────────────────────────────────────────────────────────────────
# When run as `python backend/test_db.py`, Python adds the *script's directory*
# (backend/) to sys.path, NOT the project root. That means `import backend.app`
# fails because Python looks inside backend/ for a `backend/` package.
#
# Fix: explicitly insert the project root (two levels up from this file)
# into sys.path[0] so `backend.app.*` imports resolve correctly.
#
# When run as `python -m backend.test_db` this block is harmless (project root
# is already on sys.path by Python's module runner).
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from sqlalchemy import text

from backend.app.config.settings import get_settings
from backend.app.database.database import engine


def test_connection() -> None:
    settings = get_settings()

    print("─" * 50)
    print("  Mandate Retry Sequencer — DB Connectivity Test")
    print("─" * 50)
    print(f"  DATABASE_URL : {settings.DATABASE_URL}")
    print(f"  APP_ENV      : {settings.APP_ENV}")
    print("─" * 50)

    try:
        # `engine.connect()` checks out a real connection from the pool.
        # `text()` is required in SQLAlchemy 2.x for raw SQL strings.
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            row = result.fetchone()

        assert row is not None and row[0] == 1, "SELECT 1 returned unexpected result"

        print()
        print("  ✅ Database Connected Successfully")
        print(f"     Connected to: mandate_retry_db")
        print()

    except Exception as exc:
        print()
        print("  ❌ Database Connection FAILED")
        print(f"     Error: {exc}")
        print()
        print("  Troubleshooting tips:")
        print("    1. Is PostgreSQL running?  → brew services list | grep postgresql")
        print("    2. Is DATABASE_URL correct in backend/.env?")
        print("    3. Does the database exist? → psql postgres -c '\\l'")
        print()
        sys.exit(1)


if __name__ == "__main__":
    test_connection()
