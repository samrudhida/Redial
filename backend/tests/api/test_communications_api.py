"""API tests for /api/v1/communications."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _create_mandate(client: TestClient) -> str:
    response = client.post(
        "/api/v1/mandates",
        json={"customer_id": "cust-1", "mandate_reference": "REF-1", "amount": "500.00"},
    )
    return response.json()["id"]


def test_record_sms_and_update_delivery_status(client: TestClient) -> None:
    mandate_id = _create_mandate(client)

    created = client.post("/api/v1/communications/sms", json={"mandate_id": mandate_id, "message": "Payment failed"})
    assert created.status_code == 201
    communication_id = created.json()["id"]

    updated = client.patch(f"/api/v1/communications/{communication_id}/delivery-status", json={"delivery_status": "delivered"})
    assert updated.status_code == 200
    assert updated.json()["delivery_status"] == "delivered"


def test_unsupported_channel_returns_normalized_422(client: TestClient) -> None:
    mandate_id = _create_mandate(client)

    response = client.post("/api/v1/communications/push", json={"mandate_id": mandate_id, "message": "x"})

    assert response.status_code == 422
    assert response.json() == {"error": "validation_error", "detail": "Unsupported communication channel"}


def test_list_filters_by_channel(client: TestClient) -> None:
    mandate_id = _create_mandate(client)
    client.post("/api/v1/communications/sms", json={"mandate_id": mandate_id, "message": "sms"})
    client.post("/api/v1/communications/email", json={"mandate_id": mandate_id, "message": "email"})

    sms_only = client.get("/api/v1/communications", params={"mandate_id": mandate_id, "channel": "sms"})

    assert len(sms_only.json()) == 1
    assert sms_only.json()[0]["channel"] == "sms"
