"""API tests for /api/v1/observability and /api/v1/dev/workflows/run."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _seed_one_mandate(client: TestClient) -> str:
    mandate = client.post("/api/v1/mandates", json={"customer_id": "obs-cust", "mandate_reference": "OBS-REF-1", "amount": "500.00"}).json()
    attempt = client.post("/api/v1/payments", json={"mandate_id": mandate["id"]}).json()
    client.patch(f"/api/v1/payments/{attempt['id']}/failure", json={"bank_response_message": "insufficient_funds"})
    return mandate["id"]


def test_overview_is_empty_before_any_run(client: TestClient) -> None:
    response = client.get("/api/v1/observability/overview")
    assert response.status_code == 200
    assert response.json() == {
        "workflows_executed": 0,
        "successful_workflows": 0,
        "failed_workflows": 0,
        "average_execution_time_ms": 0.0,
        "average_ai_latency_ms": 0.0,
        "average_confidence": 0.0,
        "total_ai_calls": 0,
    }


def test_run_workflows_then_overview_and_list_reflect_real_execution(client: TestClient) -> None:
    _seed_one_mandate(client)

    run_response = client.post("/api/v1/dev/workflows/run", json={"limit": 10})
    assert run_response.status_code == 200
    body = run_response.json()
    assert body["attempted"] == 1
    assert body["succeeded"] == 1
    assert body["failed"] == 0

    overview = client.get("/api/v1/observability/overview").json()
    assert overview["workflows_executed"] == 1
    assert overview["successful_workflows"] == 1

    workflows = client.get("/api/v1/observability/workflows").json()
    assert len(workflows) == 1
    execution_id = workflows[0]["id"]
    assert workflows[0]["status"] == "completed"

    detail = client.get(f"/api/v1/observability/workflows/{execution_id}").json()
    assert len(detail["nodes"]) == 6
    assert [node["node_name"] for node in detail["nodes"]] == ["context", "decision", "communication", "escalation", "persistence", "observability"]

    provider = client.get("/api/v1/observability/provider").json()
    assert len(provider) == 1
    assert provider[0]["provider"] == "groq"

    errors = client.get("/api/v1/observability/errors").json()
    assert errors == []

    metrics = client.get("/api/v1/observability/metrics").json()
    assert metrics["average_workflow_duration_ms"] >= 0


def test_unknown_workflow_execution_returns_404(client: TestClient) -> None:
    response = client.get("/api/v1/observability/workflows/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
