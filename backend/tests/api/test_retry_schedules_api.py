"""API tests for /api/v1/retry-schedules."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _create_mandate(client: TestClient, reference: str = "REF-1") -> str:
    response = client.post(
        "/api/v1/mandates",
        json={"customer_id": "cust-1", "mandate_reference": reference, "amount": "500.00"},
    )
    return response.json()["id"]


def test_create_and_get_retry_schedule(client: TestClient) -> None:
    mandate_id = _create_mandate(client)

    created = client.post(
        "/api/v1/retry-schedules",
        json={"mandate_id": mandate_id, "retry_strategy": "exponential_backoff", "recommended_time": "2026-08-26T10:00:00Z"},
    )
    assert created.status_code == 201
    schedule_id = created.json()["id"]

    fetched = client.get(f"/api/v1/retry-schedules/{schedule_id}")
    assert fetched.status_code == 200
    assert fetched.json()["mandate_id"] == mandate_id


def test_get_by_mandate_missing_returns_normalized_404(client: TestClient) -> None:
    mandate_id = _create_mandate(client)

    response = client.get(f"/api/v1/retry-schedules/mandate/{mandate_id}")

    assert response.status_code == 404
    assert response.json() == {"error": "not_found", "detail": "No retry schedule exists for this mandate"}


def test_update_retry_schedule_status(client: TestClient) -> None:
    mandate_id = _create_mandate(client)
    schedule_id = client.post(
        "/api/v1/retry-schedules",
        json={"mandate_id": mandate_id, "retry_strategy": "exponential_backoff", "recommended_time": "2026-08-26T10:00:00Z"},
    ).json()["id"]

    updated = client.patch(f"/api/v1/retry-schedules/{schedule_id}", json={"retry_count": 1})

    assert updated.status_code == 200
    assert updated.json()["retry_count"] == 1


def test_list_pending_retries(client: TestClient) -> None:
    mandate_id = _create_mandate(client)
    client.post(
        "/api/v1/retry-schedules",
        json={"mandate_id": mandate_id, "retry_strategy": "exponential_backoff", "recommended_time": "2026-08-26T10:00:00Z"},
    )

    response = client.get("/api/v1/retry-schedules")

    assert response.status_code == 200
    assert len(response.json()) == 1
