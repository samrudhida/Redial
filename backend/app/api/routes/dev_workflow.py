"""Developer-only endpoint to actually run the real workflow graph.

Gated exactly like backend/app/api/routes/dev_seed.py — only mounted when
APP_ENV == "development" (see backend/app/api/router.py), with the same
defense-in-depth environment check inside the handler.
"""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.app.api.dependencies import get_mandate_service, get_workflow_runner_service
from backend.app.config.settings import get_settings
from backend.app.services.mandate_service import MandateService
from backend.app.services.workflow_runner_service import WorkflowRunnerService

router = APIRouter(prefix="/dev/workflows", tags=["Developer"])


class RunWorkflowsRequest(BaseModel):
    limit: int = Field(default=50, ge=1, le=200, description="Maximum number of mandates to run the workflow for")


class RunWorkflowsResponse(BaseModel):
    attempted: int
    succeeded: int
    failed: int


def _require_development() -> None:
    if get_settings().APP_ENV != "development":
        raise HTTPException(status_code=404, detail="Not found")


@router.post("/run", response_model=RunWorkflowsResponse, summary="Run the real workflow for existing mandates (development only)")
def run_workflows(
    request: RunWorkflowsRequest = Body(default_factory=RunWorkflowsRequest),
    mandate_service: MandateService = Depends(get_mandate_service),
    runner: WorkflowRunnerService = Depends(get_workflow_runner_service),
) -> RunWorkflowsResponse:
    _require_development()
    mandates = mandate_service.list_mandates(limit=request.limit)

    succeeded = 0
    failed = 0
    for mandate in mandates:
        try:
            runner.run_for_mandate(mandate.id)
            succeeded += 1
        except Exception:
            failed += 1

    return RunWorkflowsResponse(attempted=len(mandates), succeeded=succeeded, failed=failed)
