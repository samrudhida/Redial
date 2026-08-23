"""Application-level exceptions that keep infrastructure details private."""


class RepositoryError(Exception):
    """Base exception for failures originating in the repository layer."""


class DatabaseError(RepositoryError):
    """Raised when a database operation cannot be completed safely."""


class NotFoundError(RepositoryError):
    """Raised when an operation requires a record that does not exist."""


class DuplicateRecordError(DatabaseError):
    """Raised when a write violates a database uniqueness constraint."""
