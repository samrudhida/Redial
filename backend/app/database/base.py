"""
app/database/base.py
────────────────────
Declarative base class for all SQLAlchemy ORM models.

Why a dedicated base.py?
  All ORM models must inherit from the same `Base` object so SQLAlchemy
  can track them together in its metadata registry. This matters for:
    - Alembic migrations (autogenerate compares Base.metadata vs the DB)
    - `Base.metadata.create_all(engine)` in tests (creates all tables at once)

Why keep Base in its own file (not in models/ or database.py)?
  Circular import prevention. Here is the import chain:

      session.py → database.py → (needs engine only)
      models/mandate.py → base.py → (needs Base only)
      alembic/env.py → base.py → (needs metadata only)

  If Base lived inside models/, models would import from themselves.
  If Base lived in database.py, models would import from database.py,
  creating a cycle: database.py → models → database.py.

  Keeping Base isolated breaks this cycle completely.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    Base class for all ORM models in this project.

    Every database table will be defined as a subclass:

        from backend.app.database.base import Base

        class Mandate(Base):
            __tablename__ = "mandates"
            id: Mapped[int] = mapped_column(primary_key=True)
            ...

    SQLAlchemy 2.x DeclarativeBase automatically provides:
      - `__tablename__` enforcement
      - `metadata` (the collection of all Table objects)
      - `registry` (for relationship resolution)
      - Full type annotation support via Mapped[] and mapped_column()
    """
    pass
