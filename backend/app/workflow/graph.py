"""Reusable LangGraph workflow facade.

This module owns graph execution mechanics only. Existing nodes remain the
owners of validation, decisions, persistence delegation, and observability.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from typing import Any

from backend.app.workflow.state import WorkflowState


class WorkflowGraph:
    """Delegate synchronous, asynchronous, and streaming calls to a graph."""

    def __init__(self, compiled_graph: Any) -> None:
        self._compiled_graph = compiled_graph

    def invoke(self, state: WorkflowState) -> WorkflowState:
        """Run the graph once and return a validated workflow state."""
        result = self._compiled_graph.invoke(state)
        return WorkflowState.model_validate(result)

    async def ainvoke(self, state: WorkflowState) -> WorkflowState:
        """Run the graph asynchronously and return a validated workflow state."""
        result = await self._compiled_graph.ainvoke(state)
        return WorkflowState.model_validate(result)

    def stream(self, state: WorkflowState) -> Iterator[WorkflowState]:
        """Yield validated state snapshots emitted by the compiled graph."""
        for result in self._compiled_graph.stream(state):
            yield self._validate_stream_result(result)

    async def astream(self, state: WorkflowState) -> AsyncIterator[WorkflowState]:
        """Asynchronously yield validated state snapshots from the graph."""
        async for result in self._compiled_graph.astream(state):
            yield self._validate_stream_result(result)

    @staticmethod
    def _validate_stream_result(result: Any) -> WorkflowState:
        """Unwrap LangGraph's node-keyed stream update before validation."""
        if isinstance(result, dict) and len(result) == 1:
            value = next(iter(result.values()))
            if isinstance(value, dict) and "metadata" in value:
                return WorkflowState.model_validate(value)
        return WorkflowState.model_validate(result)
