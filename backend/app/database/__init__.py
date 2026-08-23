"""
app/database/
─────────────
Database layer for the Mandate Retry Sequencer.

Module layout:
  base.py     — DeclarativeBase that all ORM models inherit from.
  database.py — SQLAlchemy engine + SessionLocal factory.
  session.py  — get_db() FastAPI dependency (yields a Session per request).

Import hierarchy (no circular dependencies):
  settings.py → (no internal deps)
  base.py     → (no internal deps)
  database.py → settings.py
  session.py  → database.py
  models/*    → base.py
  routes/*    → session.py
"""
