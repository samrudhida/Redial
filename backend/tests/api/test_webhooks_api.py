"""API tests for POST /api/v1/webhooks/razorpay — the real HTTP route.

Verifies the actual wiring (raw-body signature check, header reading,
persistence, status codes) rather than RazorpayService in isolation. Uses a
real HMAC signature computed with a known test secret, injected via a
dependency override — no real Razorpay credentials or network involved.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.api.dependencies import get_razorpay_service
from backend.app.main import app
from backend.app.services.mandate_service import MandateService
from backend.app.services.payment_service import PaymentService
from backend.app.services.razorpay_service import RazorpayService

_WEBHOOK_SECRET = b"test-webhook-secret"


class _RealSignatureFakeClient:
    """Implements verify_webhook_signature exactly like RazorpayClient, no network."""

    def verify_webhook_signature(self, *, raw_body: bytes, signature: str) -> bool:
        expected = hmac.new(_WEBHOOK_SECRET, raw_body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)


@pytest.fixture()
def razorpay_wired_client(client: TestClient, db_session: Session) -> TestClient:
    """Override get_razorpay_service for just this test to use the real signature-checking fake."""
    def _override() -> RazorpayService:
        return RazorpayService(db_session, _RealSignatureFakeClient(), payment_service=PaymentService(db_session))

    app.dependency_overrides[get_razorpay_service] = _override
    try:
        yield client
    finally:
        app.dependency_overrides.pop(get_razorpay_service, None)


def _sign(body: bytes) -> str:
    return hmac.new(_WEBHOOK_SECRET, body, hashlib.sha256).hexdigest()


def test_webhook_with_invalid_signature_returns_400(razorpay_wired_client: TestClient) -> None:
    body = json.dumps({"event": "payment.captured", "contains": ["payment"], "payload": {"payment": {"entity": {"id": "pay_x", "order_id": "order_x"}}}}).encode()

    response = razorpay_wired_client.post(
        "/api/v1/webhooks/razorpay",
        content=body,
        headers={"X-Razorpay-Signature": "not-a-real-signature", "Content-Type": "application/json"},
    )

    assert response.status_code == 400


def test_webhook_with_valid_signature_and_known_order_updates_the_attempt(razorpay_wired_client: TestClient, db_session: Session) -> None:
    mandate = MandateService(db_session).register_mandate("cust-1", "REF-1", Decimal("500.00"))
    payments = PaymentService(db_session)
    attempt = payments.record_payment_attempt(mandate.id, amount=Decimal("500.00"))
    payments.payment_attempts.update(attempt.id, razorpay_order_id="order_live_test")
    db_session.commit()

    body = json.dumps(
        {
            "event": "payment.captured",
            "contains": ["payment"],
            "payload": {"payment": {"entity": {"id": "pay_live_test", "order_id": "order_live_test"}}},
        }
    ).encode()

    response = razorpay_wired_client.post(
        "/api/v1/webhooks/razorpay",
        content=body,
        headers={"X-Razorpay-Signature": _sign(body), "Content-Type": "application/json"},
    )

    assert response.status_code == 200
    body_json = response.json()
    assert body_json["signature_valid"] is True
    assert body_json["processed"] is True

    refreshed = payments.get_attempt(attempt.id)
    assert refreshed.status.value == "succeeded"
    assert refreshed.razorpay_payment_id == "pay_live_test"
