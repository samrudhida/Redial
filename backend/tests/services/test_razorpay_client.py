"""Tests for RazorpayClient — credential handling and signature verification.

No network calls: order/payment API methods are exercised at the
RazorpayService level with a fake client instead. This file covers the two
pieces of real logic RazorpayClient owns itself — auth guarding and HMAC
signature verification — neither of which needs the network.
"""

from __future__ import annotations

import hashlib
import hmac

import pytest

from backend.app.config.settings import Settings
from backend.app.payments.razorpay_client import RazorpayAuthenticationError, RazorpayClient


def _settings(**overrides) -> Settings:
    base = {
        "RAZORPAY_KEY_ID": "rzp_test_fake",
        "RAZORPAY_KEY_SECRET": "fake_secret",
        "RAZORPAY_WEBHOOK_SECRET": "fake_webhook_secret",
    }
    base.update(overrides)
    return Settings(**base)


def test_missing_key_id_raises_authentication_error() -> None:
    with pytest.raises(RazorpayAuthenticationError):
        RazorpayClient(settings=_settings(RAZORPAY_KEY_ID=""))


def test_missing_key_secret_raises_authentication_error() -> None:
    with pytest.raises(RazorpayAuthenticationError):
        RazorpayClient(settings=_settings(RAZORPAY_KEY_SECRET=""))


def test_verify_webhook_signature_accepts_a_correctly_signed_payload() -> None:
    client = RazorpayClient(settings=_settings())
    raw_body = b'{"event": "payment.captured"}'
    signature = hmac.new(b"fake_webhook_secret", raw_body, hashlib.sha256).hexdigest()

    assert client.verify_webhook_signature(raw_body=raw_body, signature=signature) is True


def test_verify_webhook_signature_rejects_a_tampered_payload() -> None:
    client = RazorpayClient(settings=_settings())
    raw_body = b'{"event": "payment.captured"}'
    signature = hmac.new(b"fake_webhook_secret", raw_body, hashlib.sha256).hexdigest()

    tampered_body = b'{"event": "payment.failed"}'

    assert client.verify_webhook_signature(raw_body=tampered_body, signature=signature) is False


def test_verify_webhook_signature_rejects_wrong_secret() -> None:
    client = RazorpayClient(settings=_settings())
    raw_body = b'{"event": "payment.captured"}'
    signature = hmac.new(b"a_different_secret", raw_body, hashlib.sha256).hexdigest()

    assert client.verify_webhook_signature(raw_body=raw_body, signature=signature) is False


def test_verify_webhook_signature_returns_false_when_no_webhook_secret_configured() -> None:
    client = RazorpayClient(settings=_settings(RAZORPAY_WEBHOOK_SECRET=""))
    raw_body = b'{"event": "payment.captured"}'

    assert client.verify_webhook_signature(raw_body=raw_body, signature="anything") is False
