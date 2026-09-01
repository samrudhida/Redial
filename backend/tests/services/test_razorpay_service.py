"""Tests for RazorpayService — webhook verification, persistence, and effects.

Uses a fake client that only implements verify_webhook_signature (the one
piece RazorpayService actually calls) — no network, no real credentials.
"""

from __future__ import annotations

import json
from decimal import Decimal

from sqlalchemy.orm import Session

from backend.app.models.enums import PaymentStatus
from backend.app.services.mandate_service import MandateService
from backend.app.services.payment_service import PaymentService
from backend.app.services.razorpay_service import RazorpayService


class _FakeSignatureClient:
    """Only verify_webhook_signature is exercised by RazorpayService — nothing else."""

    def __init__(self, *, valid: bool) -> None:
        self.valid = valid

    def verify_webhook_signature(self, *, raw_body: bytes, signature: str) -> bool:
        return self.valid


def _captured_payload(order_id: str, payment_id: str = "pay_captured1") -> bytes:
    return json.dumps(
        {
            "event": "payment.captured",
            "contains": ["payment"],
            "payload": {"payment": {"entity": {"id": payment_id, "order_id": order_id, "status": "captured"}}},
        }
    ).encode("utf-8")


def _failed_payload(order_id: str, payment_id: str = "pay_failed1") -> bytes:
    return json.dumps(
        {
            "event": "payment.failed",
            "contains": ["payment"],
            "payload": {
                "payment": {
                    "entity": {
                        "id": payment_id,
                        "order_id": order_id,
                        "status": "failed",
                        "error_code": "BAD_REQUEST_ERROR",
                        "error_description": "Payment failed due to insufficient funds.",
                    }
                }
            },
        }
    ).encode("utf-8")


def _make_attempt_with_order(db_session: Session, order_id: str):
    mandate = MandateService(db_session).register_mandate("cust-1", "REF-1", Decimal("500.00"))
    payments = PaymentService(db_session)
    attempt = payments.record_payment_attempt(mandate.id, amount=Decimal("500.00"))
    payments.payment_attempts.update(attempt.id, razorpay_order_id=order_id)
    db_session.commit()
    return mandate, attempt


def test_invalid_signature_is_persisted_but_not_applied(db_session: Session) -> None:
    mandate, attempt = _make_attempt_with_order(db_session, "order_1")
    service = RazorpayService(db_session, _FakeSignatureClient(valid=False))

    event = service.process_webhook(raw_body=_captured_payload("order_1"), signature="doesnt-matter")

    assert event.signature_valid is False
    assert event.processing_error == "Signature verification failed"
    assert event.mandate_id is None
    refreshed = PaymentService(db_session).get_attempt(attempt.id)
    assert refreshed.status == PaymentStatus.PENDING


def test_valid_captured_event_marks_the_attempt_succeeded(db_session: Session) -> None:
    mandate, attempt = _make_attempt_with_order(db_session, "order_2")
    service = RazorpayService(db_session, _FakeSignatureClient(valid=True))

    event = service.process_webhook(raw_body=_captured_payload("order_2", "pay_abc"), signature="valid")

    assert event.signature_valid is True
    assert event.processing_error is None
    assert event.mandate_id == mandate.id
    refreshed = PaymentService(db_session).get_attempt(attempt.id)
    assert refreshed.status == PaymentStatus.SUCCEEDED
    assert refreshed.razorpay_payment_id == "pay_abc"


def test_valid_failed_event_marks_the_attempt_failed_with_reason(db_session: Session) -> None:
    mandate, attempt = _make_attempt_with_order(db_session, "order_3")
    service = RazorpayService(db_session, _FakeSignatureClient(valid=True))

    event = service.process_webhook(raw_body=_failed_payload("order_3"), signature="valid")

    assert event.processing_error is None
    refreshed = PaymentService(db_session).get_attempt(attempt.id)
    assert refreshed.status == PaymentStatus.FAILED
    assert refreshed.bank_response_message == "Payment failed due to insufficient funds."


def test_unresolvable_order_id_is_persisted_with_an_error_but_does_not_raise(db_session: Session) -> None:
    service = RazorpayService(db_session, _FakeSignatureClient(valid=True))

    event = service.process_webhook(raw_body=_captured_payload("order_does_not_exist"), signature="valid")

    assert event.signature_valid is True
    assert event.mandate_id is None
    assert "No payment attempt found" in (event.processing_error or "")


def test_duplicate_delivery_of_the_same_event_is_a_no_op(db_session: Session) -> None:
    mandate, attempt = _make_attempt_with_order(db_session, "order_4")
    service = RazorpayService(db_session, _FakeSignatureClient(valid=True))
    payload = _captured_payload("order_4", "pay_dup")

    first = service.process_webhook(raw_body=payload, signature="valid")
    second = service.process_webhook(raw_body=payload, signature="valid")

    assert first.id == second.id  # redelivery resolves to the same persisted row, not a duplicate


def test_no_configured_client_treats_every_signature_as_invalid(db_session: Session) -> None:
    mandate, attempt = _make_attempt_with_order(db_session, "order_5")
    service = RazorpayService(db_session, None)  # Razorpay not configured — demo mode

    event = service.process_webhook(raw_body=_captured_payload("order_5"), signature="whatever")

    assert event.signature_valid is False
    refreshed = PaymentService(db_session).get_attempt(attempt.id)
    assert refreshed.status == PaymentStatus.PENDING
