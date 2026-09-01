"""API tests for /api/v1/decisions."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _create_mandate(client: TestClient) -> str:
    response = client.post(
        "/api/v1/mandates",
        json={"customer_id": "cust-1", "mandate_reference": "REF-1", "amount": "500.00"},
    )
    return response.json()["id"]


def test_record_and_list_decision(client: TestClient) -> None:
    mandate_id = _create_mandate(client)

    created = client.post(
        "/api/v1/decisions",
        json={"mandate_id": mandate_id, "decision_type": "retry_decision", "explanation": "Soft decline", "confidence_score": 0.92},
    )
    assert created.status_code == 201

    listed = client.get("/api/v1/decisions", params={"mandate_id": mandate_id})
    assert len(listed.json()) == 1


def test_confidence_score_out_of_range_returns_422_not_500(client: TestClient) -> None:
    """Regression test for the Decimal-in-validation-error 500 discovered during
    manual HTTP testing: a Decimal Field(le=1) constraint failing must still
    produce a JSON-encodable 422, not raise TypeError inside the response encoder.
    """
    mandate_id = _create_mandate(client)

    response = client.post(
        "/api/v1/decisions",
        json={"mandate_id": mandate_id, "decision_type": "x", "explanation": "x", "confidence_score": 1.5},
    )

    assert response.status_code == 422
    assert response.json()["error"] == "validation_error"
