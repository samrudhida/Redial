"""API tests for /api/v1/payments."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _create_mandate(client: TestClient) -> str:
    response = client.post(
        "/api/v1/mandates",
        json={"customer_id": "cust-1", "mandate_reference": "REF-1", "amount": "500.00"},
    )
    return response.json()["id"]


def test_record_then_mark_failure_then_success(client: TestClient) -> None:
    mandate_id = _create_mandate(client)

    attempt = client.post("/api/v1/payments", json={"mandate_id": mandate_id}).json()
    failed = client.patch(f"/api/v1/payments/{attempt['id']}/failure", json={"decline_category": "insufficient_funds"})
    assert failed.status_code == 200
    assert failed.json()["status"] == "failed"

    retry = client.post("/api/v1/payments", json={"mandate_id": mandate_id}).json()
    succeeded = client.patch(f"/api/v1/payments/{retry['id']}/success")
    assert succeeded.status_code == 200
    assert succeeded.json()["status"] == "succeeded"


def test_list_requires_mandate_id_query_param(client: TestClient) -> None:
    response = client.get("/api/v1/payments")

    assert response.status_code == 422
    assert response.json()["error"] == "validation_error"


def test_list_filters_by_status(client: TestClient) -> None:
    mandate_id = _create_mandate(client)
    attempt = client.post("/api/v1/payments", json={"mandate_id": mandate_id}).json()
    failure_response = client.patch(f"/api/v1/payments/{attempt['id']}/failure", json={})
    assert failure_response.status_code == 200
    client.post("/api/v1/payments", json={"mandate_id": mandate_id})

    failed_only = client.get("/api/v1/payments", params={"mandate_id": mandate_id, "status": "failed"})

    assert len(failed_only.json()) == 1
