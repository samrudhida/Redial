"""API tests for /api/v1/escalations."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _create_mandate(client: TestClient) -> str:
    response = client.post(
        "/api/v1/mandates",
        json={"customer_id": "cust-1", "mandate_reference": "REF-1", "amount": "500.00"},
    )
    return response.json()["id"]


def test_create_list_and_resolve_escalation(client: TestClient) -> None:
    mandate_id = _create_mandate(client)

    created = client.post("/api/v1/escalations", json={"mandate_id": mandate_id, "reason": "Manual review needed"})
    assert created.status_code == 201
    escalation_id = created.json()["id"]

    open_list = client.get("/api/v1/escalations")
    assert len(open_list.json()) == 1

    resolved = client.patch(f"/api/v1/escalations/{escalation_id}/resolve")
    assert resolved.status_code == 200
    assert resolved.json()["resolved"] is True

    assert client.get("/api/v1/escalations").json() == []
    assert len(client.get("/api/v1/escalations", params={"resolved": True}).json()) == 1
