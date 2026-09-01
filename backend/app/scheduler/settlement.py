"""Dev-mode job that settles stale pending/processing payment attempts.

Real production settlement comes from a Razorpay webhook. In this
development environment there is no live checkout completing test-mode
orders, so a freshly booked retry attempt would otherwise sit in `pending`
forever — meaning Recovery rate, Daily collections, and the trend charts
could never move no matter how much real retry activity happens. This job
simulates that missing gateway callback, only ever run when
APP_ENV == "development" (see backend/app/scheduler/scheduler.py).
"""

from __future__ import annotations

import logging
import random
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from backend.app.database.database import SessionLocal
from backend.app.services.dev_seed_service import SOFT_DECLINE_CATEGORIES
from backend.app.services.payment_service import PaymentService

logger = logging.getLogger(__name__)

DEFAULT_SETTLE_AFTER = timedelta(minutes=2)
DEFAULT_SUCCESS_RATE = 0.65


@dataclass
class SettlementBatchResult:
    """Outcome of one settlement tick, for logging and tests."""

    settled: int = 0
    succeeded: int = 0
    failed: int = 0


def settle_pending_payments(
    *,
    session_factory: Callable[[], Session] = SessionLocal,
    settle_after: timedelta = DEFAULT_SETTLE_AFTER,
    success_rate: float = DEFAULT_SUCCESS_RATE,
) -> SettlementBatchResult:
    """Resolve every payment attempt that's been unresolved for at least `settle_after`."""
    session = session_factory()
    try:
        payment_service = PaymentService(session)
        cutoff = datetime.now(timezone.utc) - settle_after
        stale_attempts = payment_service.list_unresolved_attempts(before=cutoff)
        result = SettlementBatchResult(settled=len(stale_attempts))
        for attempt in stale_attempts:
            try:
                if random.random() < success_rate:
                    payment_service.mark_payment_success(attempt.id)
                    result.succeeded += 1
                else:
                    category = random.choice(SOFT_DECLINE_CATEGORIES)
                    payment_service.mark_payment_failure(attempt.id, decline_category=category, bank_response_message=f"Declined: {category.value}")
                    result.failed += 1
            except Exception:
                logger.exception("Failed to settle payment attempt %s", attempt.id)
        return result
    finally:
        session.close()
