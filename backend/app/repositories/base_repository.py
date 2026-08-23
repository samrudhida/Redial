"""Reusable synchronous SQLAlchemy 2.x repository primitives."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any, Generic, NoReturn, TypeVar

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.core.exceptions import DatabaseError, DuplicateRecordError
from backend.app.database.base import Base

ModelT = TypeVar("ModelT", bound=Base)

logger = logging.getLogger(__name__)


class BaseRepository(Generic[ModelT]):
    """Common persistence operations for one SQLAlchemy mapped model.

    The repository receives a request- or unit-of-work-scoped ``Session``.
    It flushes writes so database constraints are checked, but it never
    commits or rolls back. The service layer owns transaction boundaries,
    allowing multiple repository calls to succeed or fail atomically.
    """

    def __init__(self, session: Session, model: type[ModelT]) -> None:
        self.session = session
        self.model = model

    def create(self, **values: Any) -> ModelT:
        """Create, flush, and return a model instance without committing.

        ``values`` must map to model column names. ``flush()`` assigns database
        generated values and exposes write errors, while keeping transaction
        ownership with the caller.
        """
        try:
            entity = self.model(**values)
            self.session.add(entity)
            self.session.flush()
            return entity
        except SQLAlchemyError as exc:
            self._raise_database_error("create", exc)

    def get_by_id(self, entity_id: Any) -> ModelT | None:
        """Return one entity by primary key, or ``None`` when it does not exist."""
        try:
            statement = select(self.model).where(self.model.id == entity_id)  # type: ignore[attr-defined]
            return self.session.execute(statement).scalar_one_or_none()
        except SQLAlchemyError as exc:
            self._raise_database_error("get_by_id", exc)

    def get_all(self, *, offset: int = 0, limit: int = 100) -> list[ModelT]:
        """Return a paginated, primary-key-ordered collection of entities."""
        self._validate_pagination(offset, limit)
        try:
            statement = select(self.model).order_by(self.model.id).offset(offset).limit(limit)  # type: ignore[attr-defined]
            return list(self.session.execute(statement).scalars().all())
        except SQLAlchemyError as exc:
            self._raise_database_error("get_all", exc)

    def update(self, entity_id: Any, **values: Any) -> ModelT | None:
        """Apply validated column values to an entity and return it, if present.

        Unknown or relationship attributes are rejected before any write. An
        empty update returns the existing entity without issuing a flush.
        """
        self._validate_update_values(values)
        entity = self.get_by_id(entity_id)
        if entity is None:
            return None
        if not values:
            return entity

        try:
            for field, value in values.items():
                setattr(entity, field, value)
            self.session.flush()
            return entity
        except SQLAlchemyError as exc:
            self._raise_database_error("update", exc, entity_id=entity_id)

    def delete(self, entity_id: Any) -> bool:
        """Delete an entity by primary key and report whether a row was removed."""
        entity = self.get_by_id(entity_id)
        if entity is None:
            return False

        try:
            self.session.delete(entity)
            self.session.flush()
            return True
        except SQLAlchemyError as exc:
            self._raise_database_error("delete", exc, entity_id=entity_id)

    def exists(self, entity_id: Any) -> bool:
        """Return whether an entity with the supplied primary key exists."""
        try:
            statement = select(self.model.id).where(self.model.id == entity_id).limit(1)  # type: ignore[attr-defined]
            return self.session.execute(statement).scalar_one_or_none() is not None
        except SQLAlchemyError as exc:
            self._raise_database_error("exists", exc)

    def _raise_database_error(
        self,
        operation: str,
        error: SQLAlchemyError,
        *,
        entity_id: Any | None = None,
    ) -> NoReturn:
        """Log an infrastructure failure and raise an application exception.

        A failed flush leaves SQLAlchemy's transaction in a failed state. The
        service layer must roll back the session before continuing or returning
        an error response.
        """
        logger.error(
            "Repository database operation failed",
            extra={"model": self.model.__name__, "operation": operation, "entity_id": entity_id},
            exc_info=True,
        )
        if self._is_unique_violation(error):
            raise DuplicateRecordError(f"Duplicate {self.model.__name__} record during {operation}") from None
        raise DatabaseError(f"Database error while performing {operation} on {self.model.__name__}") from None

    @staticmethod
    def _is_unique_violation(error: SQLAlchemyError) -> bool:
        """Identify portable and PostgreSQL uniqueness-constraint failures."""
        if not isinstance(error, IntegrityError):
            return False
        pgcode = getattr(error.orig, "pgcode", None)
        return pgcode == "23505" or "unique constraint" in str(error.orig).lower()

    def _validate_update_values(self, values: Mapping[str, Any]) -> None:
        """Ensure generic updates affect only mapped table columns."""
        unknown_columns = set(values).difference(self.model.__table__.columns.keys())
        if unknown_columns:
            names = ", ".join(sorted(unknown_columns))
            raise ValueError(f"Unknown or non-column fields for {self.model.__name__}: {names}")

    @staticmethod
    def _validate_pagination(offset: int, limit: int) -> None:
        """Reject invalid pagination before sending a statement to the database."""
        if offset < 0:
            raise ValueError("offset must be greater than or equal to zero")
        if limit <= 0:
            raise ValueError("limit must be greater than zero")
