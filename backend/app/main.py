"""
app/main.py
───────────
Application entry point for the Mandate Retry Sequencer backend.

This file is the ONLY place where:
  1. The FastAPI app instance is created.
  2. Middleware (CORS, etc.) is registered.
  3. Routers are included.
  4. Startup / shutdown lifecycle events are wired up.

Everything else (business logic, DB setup, scheduler) is delegated
to its own module and called from here — keeping this file thin and
easy to read at a glance.
"""

import logging

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ── Internal imports ──────────────────────────────────────────────────────────
from backend.app.api.dependencies import resolve_ai_service, resolve_razorpay_client
from backend.app.api.exception_handlers import register_exception_handlers
from backend.app.api.router import api_router
from backend.app.config.settings import get_settings
from backend.app.scheduler.scheduler import start_scheduler, stop_scheduler
from backend.app.utils.logging import setup_logging

# ── Bootstrap logging FIRST, before any other import uses getLogger() ─────────
setup_logging()

logger = logging.getLogger(__name__)
settings = get_settings()


# ─────────────────────────────────────────────────────────────────────────────
# Lifespan context manager (FastAPI's modern way of doing startup/shutdown)
#
# Why lifespan instead of @app.on_event("startup")?
#   - @app.on_event is deprecated in FastAPI 0.95+.
#   - asynccontextmanager gives a clean try/finally pattern:
#       code before `yield` → startup
#       code after  `yield` → shutdown
# ─────────────────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.

    STARTUP  (before yield):
      - Connect to the database
      - Start the APScheduler background scheduler
      - Warm up any LLM connections

    SHUTDOWN (after yield):
      - Gracefully stop the scheduler
      - Close DB connection pool
    """
    # ── STARTUP ──────────────────────────────────────────────────────────────
    logger.info("═" * 60)
    logger.info("  %s v%s starting up...", settings.APP_NAME, settings.APP_VERSION)
    logger.info("  Environment : %s", settings.APP_ENV)
    logger.info("  API Prefix  : %s", settings.API_PREFIX)
    logger.info("  Debug Mode  : %s", settings.DEBUG)
    logger.info("═" * 60)

    ai_service, fallback_reason = resolve_ai_service(settings)
    if ai_service is not None:
        logger.info("  AI decisions: enabled (provider=%s, model=%s)", settings.LLM_PROVIDER, ai_service.llm.get_model_name())
    else:
        logger.info("  AI decisions: disabled (reason=%s)", fallback_reason)

    razorpay_client, razorpay_fallback_reason = resolve_razorpay_client(settings)
    if razorpay_client is not None:
        logger.info("  Razorpay: enabled (Test/Live Mode determined by key prefix, key_id=%s...)", settings.RAZORPAY_KEY_ID[:12])
    else:
        logger.info("  Razorpay: disabled — running in demo mode (reason=%s)", razorpay_fallback_reason)

    # TODO (Step 2): Initialise database connection pool
    # from app.database.session import init_db
    # await init_db()

    start_scheduler()
    logger.info("  Retry scheduler: started (interval=%ss)", settings.SCHEDULER_RETRY_INTERVAL_SECONDS)

    logger.info("Application startup complete. Ready to serve requests.")

    yield  # ← Application runs here (handles requests)

    # ── SHUTDOWN ─────────────────────────────────────────────────────────────
    logger.info("Application shutting down...")

    stop_scheduler()

    # TODO (Step 2): Dispose DB connection pool
    # from app.database.session import close_db
    # await close_db()

    logger.info("Shutdown complete. Goodbye.")


# ─────────────────────────────────────────────────────────────────────────────
# FastAPI Application Instance
#
# All metadata here feeds the auto-generated OpenAPI docs at /docs
# ─────────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "AI-powered mandate retry sequencer that intelligently retries "
        "failed payment mandates using LangGraph agents and Razorpay APIs. "
        "Built for the Razorpay AI Buildathon 2026."
    ),
    version=settings.APP_VERSION,
    docs_url="/docs",           # Swagger UI
    redoc_url="/redoc",         # ReDoc UI
    openapi_url="/openapi.json",
    lifespan=lifespan,          # Wire up our lifecycle manager
)


# ─────────────────────────────────────────────────────────────────────────────
# CORS Middleware
#
# Why CORS?
#   Browsers block requests from http://localhost:3000 (React/Next.js)
#   to http://localhost:8000 (our API) unless the server explicitly allows it.
#
# In production:
#   Replace localhost origins with your actual deployed frontend URL.
#   NEVER use allow_origins=["*"] in production — it allows any website
#   to make authenticated requests on behalf of your users.
# ─────────────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,   # e.g. ["http://localhost:3000"]
    allow_credentials=True,                # Allow cookies / auth headers
    allow_methods=["*"],                   # GET, POST, PUT, DELETE, etc.
    allow_headers=["*"],                   # Content-Type, Authorization, etc.
)

app.include_router(api_router)
register_exception_handlers(app)


# ─────────────────────────────────────────────────────────────────────────────
# API Router Placeholder
#
# When you build new feature routers (e.g., mandates, payments),
# include them here:
#
#   from app.api.v1.mandates import router as mandates_router
#   app.include_router(mandates_router, prefix=settings.API_PREFIX)
#
# Keeping all router registrations in one place makes it easy to see
# the entire URL surface area of the API at a glance.
# ─────────────────────────────────────────────────────────────────────────────


# ─────────────────────────────────────────────────────────────────────────────
# Core Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.get(
    "/",
    tags=["Root"],
    summary="Root endpoint",
    description="Returns a welcome message confirming the API is reachable.",
)
async def root() -> dict:
    """
    Root endpoint — sanity check that the server is running.
    Useful for quick smoke tests after deployment.
    """
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV,
        "docs": "/docs",
    }


# API routes and exception handlers are registered above during app creation.
__all__ = ["app"]





