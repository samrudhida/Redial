"""Workflow execution and per-node timeline ORM models.

These persist exactly what backend/app/workflow/state.py's WorkflowState
already tracks in memory during one graph run (WorkflowMetadata,
WorkflowHistoryEntry, FinalDecision, AITrace, WorkflowError) so the
observability API has a real, queryable history instead of anything
fabricated. See backend/app/services/workflow_execution_service.py for the
concrete PersistenceServiceProtocol implementation that writes these rows.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from backend.app.database.base import Base

if TYPE_CHECKING:
    pass


class WorkflowExecution(Base):
    """One end-to-end run of the recovery workflow for a single mandate."""

    __tablename__ = "workflow_executions"
    __table_args__ = (
        Index("ix_workflow_executions_mandate_started", "mandate_id", "started_at"),
        Index("ix_workflow_executions_status_started", "status", "started_at"),
    )

    # Reuses WorkflowState.metadata.execution_id as the primary key, so this
    # row's identity matches the identity LangGraph already assigned the run.
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    workflow_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    mandate_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("mandates.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    ai_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ai_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ai_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)

    retry_allowed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    retry_priority: Mapped[str | None] = mapped_column(String(20), nullable=True)
    communication_channel: Mapped[str | None] = mapped_column(String(20), nullable=True)
    escalation_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    # The node whose position in the (fixed, linear) graph sequence matches how
    # many history entries were recorded before failure — see
    # WorkflowRunnerService.run_for_mandate for how this is inferred.
    failed_node: Mapped[str | None] = mapped_column(String(50), nullable=True)

    nodes: Mapped[list[WorkflowExecutionNode]] = relationship(
        back_populates="execution", cascade="all, delete-orphan", passive_deletes=True,
        order_by="WorkflowExecutionNode.finished_at",
    )


class WorkflowExecutionNode(Base):
    """One entry in a workflow execution's node-by-node timeline."""

    __tablename__ = "workflow_execution_nodes"
    __table_args__ = (Index("ix_workflow_execution_nodes_execution_finished", "execution_id", "finished_at"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    execution_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workflow_executions.id", ondelete="CASCADE"), nullable=False, index=True)
    node_name: Mapped[str] = mapped_column(String(50), nullable=False)
    event: Mapped[str] = mapped_column(String(50), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    execution: Mapped[WorkflowExecution] = relationship(back_populates="nodes")
