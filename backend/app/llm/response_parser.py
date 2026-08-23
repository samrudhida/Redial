"""Parse raw provider output into validated Pydantic response objects."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from backend.app.llm.schemas import CommunicationSuggestion, EscalationDecision, RetryDecision

ResponseT = TypeVar("ResponseT", bound=BaseModel)


class AIResponseParseError(ValueError):
    """Raised when a raw LLM response is not valid JSON for its target schema."""


def parse_retry_response(raw_response: str | Mapping[str, Any]) -> RetryDecision:
    """Parse a provider response into a validated retry decision."""
    return _parse_response(raw_response, RetryDecision)


def parse_communication_response(raw_response: str | Mapping[str, Any]) -> CommunicationSuggestion:
    """Parse a provider response into a validated communication suggestion."""
    return _parse_response(raw_response, CommunicationSuggestion)


def parse_escalation_response(raw_response: str | Mapping[str, Any]) -> EscalationDecision:
    """Parse a provider response into a validated escalation recommendation."""
    return _parse_response(raw_response, EscalationDecision)


def _parse_response(raw_response: str | Mapping[str, Any], schema: type[ResponseT]) -> ResponseT:
    """Decode JSON or mapping input and validate it with the requested schema."""
    payload = _decode_response(raw_response)
    try:
        return schema.model_validate(payload)
    except ValidationError as exc:
        raise AIResponseParseError(f"Invalid {schema.__name__} response: {exc}") from exc


def _decode_response(raw_response: str | Mapping[str, Any]) -> dict[str, Any]:
    """Decode a JSON object, accepting an optional Markdown JSON code fence."""
    if isinstance(raw_response, Mapping):
        return dict(raw_response)
    if not isinstance(raw_response, str) or not raw_response.strip():
        raise AIResponseParseError("LLM response must be a non-empty JSON object or mapping")

    content = raw_response.strip()
    if content.startswith("```") and content.endswith("```"):
        content = content.split("\n", 1)[1] if "\n" in content else ""
        content = content.rsplit("```", 1)[0].strip()
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        raise AIResponseParseError("LLM response is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise AIResponseParseError("LLM response JSON must be an object")
    return payload
