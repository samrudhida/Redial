"""Workflow execution endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from backend.app.api.dependencies import get_workflow
from backend.app.workflow.graph import WorkflowGraph
from backend.app.workflow.state import WorkflowState

router = APIRouter(prefix="/workflow", tags=["Workflow"])


class WorkflowRequest(BaseModel):
    """Validated workflow input containing the shared state object."""

    state: WorkflowState


class WorkflowResponse(BaseModel):
    """Serialized result returned after graph execution."""

    state: WorkflowState


@router.post("/run", response_model=WorkflowResponse, summary="Run recovery workflow")
def run_workflow(request: WorkflowRequest, workflow: WorkflowGraph = Depends(get_workflow)) -> WorkflowResponse:
    """Invoke the injected compiled workflow without adding business logic."""
    return WorkflowResponse(state=workflow.invoke(request.state))