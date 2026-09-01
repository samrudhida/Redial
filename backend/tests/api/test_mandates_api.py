"""API tests for /api/v1/mandates: the list-endpoint fix and its filters."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _create_mandate(client: TestClient, *, customer_id: str, reference: str, amount: str = "500.00") -> dict:
    response = client.post(
        "/api/v1/mandates",
        json={"customer_id": customer_id, "mandate_reference": reference, "amount": amount},
    )
    assert response.status_code == 201
    return response.json()


def test_list_mandates_no_longer_returns_501(client: TestClient) -> None:
    _create_mandate(client, customer_id="cust-1", reference="REF-1")

    response = client.get("/api/v1/mandates")

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_list_mandates_filters_by_customer_id(client: TestClient) -> None:
    _create_mandate(client, customer_id="cust-1", reference="REF-1")
    _create_mandate(client, customer_id="cust-2", reference="REF-2")

    response = client.get("/api/v1/mandates", params={"customer_id": "cust-1"})

    body = response.json()
    assert len(body) == 1
    assert body[0]["customer_id"] == "cust-1"


def test_get_unknown_mandate_returns_normalized_404(client: TestClient) -> None:
    response = client.get("/api/v1/mandates/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404
    assert response.json() == {"error": "not_found", "detail": "Mandate not found"}


def test_pagination_limit_over_100_is_rejected(client: TestClient) -> None:
    response = client.get("/api/v1/mandates", params={"limit": 500})

    assert response.status_code == 422
    assert response.json()["error"] == "validation_error"


def test_negative_amount_is_rejected_with_422_not_500(client: TestClient) -> None:
    """Regression test: a Decimal Field(gt=0) failing validation used to 500
    because the raw Pydantic error (containing a Decimal in ``ctx``) was not
    JSON-encoded before being returned.
    """
    response = client.post(
        "/api/v1/mandates",
        json={"customer_id": "cust-1", "mandate_reference": "REF-1", "amount": "-5.00"},
    )

    assert response.status_code == 422
    assert response.json()["error"] == "validation_error"
