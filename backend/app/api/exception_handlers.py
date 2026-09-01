"""Consistent HTTP translation for application and validation failures."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from backend.app.core.exceptions import DatabaseError, DuplicateRecordError, NotFoundError
from backend.app.services.base_service import InvalidStateError, ServiceError, ValidationError

_ERROR_SLUGS_BY_STATUS = {400: "validation_error", 404: "not_found", 409: "conflict", 422: "validation_error"}


def register_exception_handlers(app: FastAPI) -> None:
    """Register stable JSON responses without exposing infrastructure details."""
    app.add_exception_handler(RequestValidationError, request_validation_handler)
    app.add_exception_handler(ValidationError, validation_handler)
    app.add_exception_handler(InvalidStateError, validation_handler)
    app.add_exception_handler(NotFoundError, not_found_handler)
    app.add_exception_handler(DuplicateRecordError, database_handler)
    app.add_exception_handler(DatabaseError, database_handler)
    app.add_exception_handler(ServiceError, service_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_handler)


async def request_validation_handler(request: Request, exc: Exception) -> JSONResponse:
    """Encode Pydantic's raw error list before returning it.

    ``exc.errors()`` can embed non-JSON-safe values (e.g. a ``Decimal`` bound
    inside ``ctx`` for a ``Field(le=...)`` constraint on a Decimal field), so
    this must go through ``jsonable_encoder`` rather than straight to
    ``JSONResponse``, which only calls the stdlib ``json.dumps``.
    """
    detail = jsonable_encoder(exc.errors()) if isinstance(exc, RequestValidationError) else str(exc)
    return JSONResponse(status_code=422, content={"error": "validation_error", "detail": detail})


async def validation_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=400, content={"error": "validation_error", "detail": str(exc)})


async def not_found_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=404, content={"error": "not_found", "detail": str(exc)})


async def database_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=409 if isinstance(exc, DuplicateRecordError) else 500, content={"error": "database_error", "detail": str(exc)})


async def service_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=400, content={"error": "service_error", "detail": str(exc)})


async def http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Normalize routes that raise ``HTTPException`` directly to the same envelope
    used by domain exceptions, so every error response has the same {error, detail} shape.
    """
    status_code = exc.status_code if isinstance(exc, HTTPException) else 500
    detail = exc.detail if isinstance(exc, HTTPException) else str(exc)
    error_slug = _ERROR_SLUGS_BY_STATUS.get(status_code, "http_error")
    return JSONResponse(status_code=status_code, content={"error": error_slug, "detail": detail})


async def unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=500, content={"error": "internal_server_error", "detail": "An unexpected error occurred"})