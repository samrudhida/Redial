"""Developer-only demo-data endpoints.

This router is only mounted when ``settings.APP_ENV == "development"`` (see
backend/app/api/router.py) — in any other environment these routes do not
exist in the app's routing table or OpenAPI schema at all. Each handler also
re-checks the environment directly as a defense-in-depth guard in case this
router is ever mounted from somewhere else.
"""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.app.api.dependencies import get_dev_seed_service
from backend.app.config.settings import get_settings
from backend.app.services.dev_seed_service import DevSeedService

router = APIRouter(prefix="/dev/seed", tags=["Developer"])


class SeedRequest(BaseModel):
    count: int = Field(default=150, ge=100, le=200, description="Number of demo mandates to generate")


class SeedSummaryResponse(BaseModel):
    mandates_created: int
    payment_attempts_created: int
    retry_schedules_created: int
    decisions_created: int
    communications_created: int
    escalations_created: int


class SeedDeleteResponse(BaseModel):
    mandates_deleted: int


def _require_development() -> None:
    if get_settings().APP_ENV != "development":
        raise HTTPException(status_code=404, detail="Not found")


@router.post("", response_model=SeedSummaryResponse, status_code=201, summary="Generate demo data (development only)")
def seed_demo_data(
    request: SeedRequest = Body(default_factory=SeedRequest),
    service: DevSeedService = Depends(get_dev_seed_service),
) -> SeedSummaryResponse:
    _require_development()
    summary = service.seed(request.count)
    return SeedSummaryResponse(
        mandates_created=summary.mandates_created,
        payment_attempts_created=summary.payment_attempts_created,
        retry_schedules_created=summary.retry_schedules_created,
        decisions_created=summary.decisions_created,
        communications_created=summary.communications_created,
        escalations_created=summary.escalations_created,
    )


@router.delete("", response_model=SeedDeleteResponse, summary="Delete demo data (development only)")
def delete_demo_data(service: DevSeedService = Depends(get_dev_seed_service)) -> SeedDeleteResponse:
    _require_development()
    deleted = service.delete_seed_data()
    return SeedDeleteResponse(mandates_deleted=deleted)
