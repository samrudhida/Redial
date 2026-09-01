"""API tests for /api/v1/dashboard — the endpoints the frontend dashboard consumes.

Asserts the response is plain JSON-safe types (str for Decimal, str for enum
dict keys) so the frontend never has to special-case Decimal or enum
wire formats.
"""

from __future__ import annotations

from fastapi.testclient import TestClient


def _create_mandate(client: TestClient, reference: str = "REF-1", amount: str = "500.00") -> str:
    response = client.post(
        "/api/v1/mandates",
        json={"customer_id": "cust-1", "mandate_reference": reference, "amount": amount},
    )
    return response.json()["id"]


def test_summary_is_json_safe_and_correct(client: TestClient) -> None:
    mandate_id = _create_mandate(client)
    attempt = client.post("/api/v1/payments", json={"mandate_id": mandate_id}).json()
    client.patch(f"/api/v1/payments/{attempt['id']}/failure")
    retry_attempt = client.post("/api/v1/payments", json={"mandate_id": mandate_id}).json()
    client.patch(f"/api/v1/payments/{retry_attempt['id']}/success")
    client.post("/api/v1/escalations", json={"mandate_id": mandate_id, "reason": "review"})

    response = client.get("/api/v1/dashboard/summary")
    assert response.status_code == 200

    body = response.json()
    assert isinstance(body["revenue_recovered"], str)
    assert body["revenue_recovered"] == "500.00"
    assert body["open_escalations"] == 1
    assert set(body["mandate_counts_by_status"].keys()) <= {"active", "paused", "cancelled", "expired", "completed"}
    assert all(isinstance(key, str) for key in body["payment_attempt_counts_by_status"].keys())


def test_summary_recent_decision_limit_is_respected(client: TestClient) -> None:
    mandate_id = _create_mandate(client)
    for i in range(3):
        client.post(
            "/api/v1/decisions",
            json={"mandate_id": mandate_id, "decision_type": "retry_decision", "explanation": f"reason {i}", "confidence_score": 0.5},
        )

    response = client.get("/api/v1/dashboard/summary", params={"recent_decision_limit": 2})

    assert len(response.json()["recent_decisions"]) == 2


def test_retry_queue_and_escalations_subroutes(client: TestClient) -> None:
    mandate_id = _create_mandate(client)
    client.post(
        "/api/v1/retry-schedules",
        json={"mandate_id": mandate_id, "retry_strategy": "exponential_backoff", "recommended_time": "2026-08-26T10:00:00Z"},
    )
    client.post("/api/v1/escalations", json={"mandate_id": mandate_id, "reason": "review"})

    retry_queue = client.get("/api/v1/dashboard/retry-queue")
    escalations = client.get("/api/v1/dashboard/escalations")

    assert len(retry_queue.json()) == 1
    assert len(escalations.json()) == 1


def test_trend_endpoint_returns_json_safe_daily_points_covering_the_full_window(client: TestClient) -> None:
    mandate_id = _create_mandate(client)
    attempt = client.post("/api/v1/payments", json={"mandate_id": mandate_id}).json()
    client.patch(f"/api/v1/payments/{attempt['id']}/success")

    response = client.get("/api/v1/dashboard/trend", params={"days": 5})
    assert response.status_code == 200

    points = response.json()
    assert len(points) == 5
    assert all(isinstance(point["day"], str) for point in points)
    assert all(isinstance(point["collected_amount"], str) for point in points)

    today_point = points[-1]
    assert today_point["attempts_total"] == 1
    assert today_point["attempts_succeeded"] == 1
    assert today_point["collected_amount"] == "500.00"
