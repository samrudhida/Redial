"""Shared transaction and business-error primitives for application services."""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from typing import NoReturn, TypeVar

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.core.exceptions import DatabaseError, RepositoryError

ResultT = TypeVar("ResultT")

logger = logging.getLogger(__name__)


class ServiceError(Exception):
    """Base exception for validation and business-rule failures in services."""


class ValidationError(ServiceError):
    """Raised when caller-provided input violates a service validation rule."""


class InvalidStateError(ServiceError):
    """Raised when an entity cannot transition from its current business state."""


class BaseService:
    """Base class for services that coordinate repositories in one transaction.

    Services own transaction boundaries because a business operation can span
    multiple repositories. Repositories only stage and flush data changes;
    this class commits all changes together or rolls them back together.
    """

    def __init__(self, session: Session, *, repositories: Mapping[str, object] | None = None) -> None:
        self.session = session
        self.repositories = dict(repositories or {})

    def commit(self) -> None:
        """Commit the transaction owned by this service operation."""
        self.session.commit()

    def rollback(self) -> None:
        """Roll back the active transaction after a failed service operation."""
        self.session.rollback()

    def flush(self) -> None:
        """Flush staged changes without ending the caller-visible transaction."""
        self.session.flush()

    def _in_transaction(self, operation: str, action: Callable[[], ResultT]) -> ResultT:
        """Run ``action`` and atomically commit or roll back its repository work."""
        try:
            result = action()
            self.commit()
            return result
        except ServiceError:
            self.rollback()
            logger.info("Service validation or state rule rejected operation", extra={"operation": operation})
            raise
        except RepositoryError:
            self.rollback()
            logger.error("Repository failure in service operation", extra={"operation": operation}, exc_info=True)
            raise
        except SQLAlchemyError as exc:
            self.rollback()
            logger.error("Transaction commit failed", extra={"operation": operation}, exc_info=True)
            raise DatabaseError(f"Database error while completing {operation}") from None
        except Exception:
            self.rollback()
            logger.error("Unexpected service operation failure", extra={"operation": operation}, exc_info=True)
            raise

    @staticmethod
    def _require(condition: bool, message: str) -> None:
        """Raise a business validation error when a required condition is false."""
        if not condition:
            raise ValidationError(message)

    @staticmethod
    def _raise_invalid_state(message: str) -> NoReturn:
        """Raise a consistent invalid-state business exception."""
        raise InvalidStateError(message)
