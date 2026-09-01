"""Central registration point for the public API routers."""

from fastapi import APIRouter

from backend.app.api.routes import (
    communications,
    dashboard,
    decisions,
    dev_seed,
    dev_workflow,
    escalations,
    health,
    mandates,
    observability,
    payments,
    retry_schedules,
    webhooks,
    workflow,
)
from backend.app.config.settings import get_settings

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(workflow.router, prefix="/api/v1")
api_router.include_router(mandates.router, prefix="/api/v1")
api_router.include_router(payments.router, prefix="/api/v1")
api_router.include_router(retry_schedules.router, prefix="/api/v1")
api_router.include_router(communications.router, prefix="/api/v1")
api_router.include_router(decisions.router, prefix="/api/v1")
api_router.include_router(escalations.router, prefix="/api/v1")
api_router.include_router(dashboard.router, prefix="/api/v1")
api_router.include_router(observability.router, prefix="/api/v1")
api_router.include_router(webhooks.router, prefix="/api/v1")

# Developer-only endpoints — mounted only in development, so they never exist
# in the routing table (or OpenAPI schema) outside it.
if get_settings().APP_ENV == "development":
    api_router.include_router(dev_seed.router, prefix="/api/v1")
    api_router.include_router(dev_workflow.router, prefix="/api/v1")