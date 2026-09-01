"""API tests for /api/v1/dev/seed."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_seed_and_delete_round_trip(client: TestClient) -> None:
    created = client.post("/api/v1/dev/seed", json={"count": 100})
    assert created.status_code == 201
    body = created.json()
    assert body["mandates_created"] == 100
    assert body["payment_attempts_created"] > 0

    listed = client.get("/api/v1/mandates", params={"limit": 100})
    assert len(listed.json()) == 100

    deleted = client.delete("/api/v1/dev/seed")
    assert deleted.status_code == 200
    assert deleted.json() == {"mandates_deleted": 100}

    listed_after = client.get("/api/v1/mandates", params={"limit": 100})
    assert listed_after.json() == []


def test_seed_count_is_bounded_to_100_200(client: TestClient) -> None:
    too_few = client.post("/api/v1/dev/seed", json={"count": 5})
    assert too_few.status_code == 422

    too_many = client.post("/api/v1/dev/seed", json={"count": 500})
    assert too_many.status_code == 422


def test_seed_never_touches_real_mandates(client: TestClient) -> None:
    real = client.post("/api/v1/mandates", json={"customer_id": "real-cust", "mandate_reference": "REAL-001", "amount": "750.00"})
    assert real.status_code == 201

    client.post("/api/v1/dev/seed", json={"count": 100})
    client.delete("/api/v1/dev/seed")

    remaining = client.get("/api/v1/mandates", params={"limit": 100}).json()
    assert [m["mandate_reference"] for m in remaining] == ["REAL-001"]
