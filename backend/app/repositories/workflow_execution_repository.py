"""Data access queries for workflow execution history."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from backend.app.models.workflow_execution import WorkflowExecution
from backend.app.repositories.base_repository import BaseRepository


class WorkflowExecutionRepository(BaseRepository[WorkflowExecution]):
    """Repository for workflow execution records and their node timelines."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, WorkflowExecution)

    def list_recent(self, *, offset: int = 0, limit: int = 100) -> list[WorkflowExecution]:
        """Return executions newest-first."""
        self._validate_pagination(offset, limit)
        try:
            statement = select(WorkflowExecution).order_by(WorkflowExecution.started_at.desc()).offset(offset).limit(limit)
            return list(self.session.execute(statement).scalars().all())
        except SQLAlchemyError as exc:
            self._raise_database_error("list_recent", exc)

    def list_failed(self, *, offset: int = 0, limit: int = 100) -> list[WorkflowExecution]:
        """Return failed executions newest-first."""
        self._validate_pagination(offset, limit)
        try:
            statement = (
                select(WorkflowExecution)
                .where(WorkflowExecution.status == "failed")
                .order_by(WorkflowExecution.started_at.desc())
                .offset(offset)
                .limit(limit)
            )
            return list(self.session.execute(statement).scalars().all())
        except SQLAlchemyError as exc:
            self._raise_database_error("list_failed", exc)

    def get_with_nodes(self, execution_id: uuid.UUID) -> WorkflowExecution | None:
        """Return one execution with its node timeline eagerly loaded."""
        try:
            statement = select(WorkflowExecution).where(WorkflowExecution.id == execution_id).options(selectinload(WorkflowExecution.nodes))
            return self.session.execute(statement).scalar_one_or_none()
        except SQLAlchemyError as exc:
            self._raise_database_error("get_with_nodes", exc)

    def list_all_for_aggregation(self) -> list[WorkflowExecution]:
        """Return every execution — used by the service layer to compute
        overview/provider/metrics aggregates in Python rather than with
        dialect-specific SQL (data volumes here are small by design).
        """
        try:
            statement = select(WorkflowExecution)
            return list(self.session.execute(statement).scalars().all())
        except SQLAlchemyError as exc:
            self._raise_database_error("list_all_for_aggregation", exc)
