"""Cross-cutting application primitives."""

from backend.app.core.exceptions import DatabaseError, DuplicateRecordError, NotFoundError, RepositoryError

__all__ = ["DatabaseError", "DuplicateRecordError", "NotFoundError", "RepositoryError"]
