"""Business operations for recording and resolving payment attempts."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from backend.app.core.exceptions import NotFoundError
from backend.app.models.enums import DeclineCategory, PaymentStatus, RetryStatus
from backend.app.models.mandate import Mandate
from backend.app.models.payment_attempt import PaymentAttempt
from backend.app.payments.razorpay_client import RazorpayClient, RazorpayError
from backend.app.repositories.mandate_repository import MandateRepository
from backend.app.repositories.payment_attempt_repository import DailyPaymentTrend, PaymentAttemptRepository
from backend.app.repositories.retry_schedule_repository import RetryScheduleRepository
from backend.app.services.base_service import BaseService, InvalidStateError

logger = logging.getLogger(__name__)

_DEFAULT_RETRY_STRATEGY = "exponential_backoff"
_DEFAULT_MAX_RETRIES = 3
_DEFAULT_INITIAL_RETRY_DELAY = timedelta(hours=24)
_TERMINAL_RETRY_STATUSES = {RetryStatus.EXECUTED, RetryStatus.EXHAUSTED, RetryStatus.CANCELLED, RetryStatus.SKIPPED}


class PaymentService(BaseService):
    """Coordinates mandate eligibility with payment-attempt lifecycle changes."""

    def __init__(
        self,
        session: Session,
        payment_attempt_repository: PaymentAttemptRepository | None = None,
        mandate_repository: MandateRepository | None = None,
        retry_schedule_repository: RetryScheduleRepository | None = None,
        razorpay_client: RazorpayClient | None = None,
    ) -> None:
        self.payment_attempts = payment_attempt_repository or PaymentAttemptRepository(session)
        self.mandates = mandate_repository or MandateRepository(session)
        self.retry_schedules = retry_schedule_repository or RetryScheduleRepository(session)
        self.razorpay_client = razorpay_client
        super().__init__(session, repositories={"payment_attempts": self.payment_attempts, "mandates": self.mandates, "retry_schedules": self.retry_schedules})

    def record_payment_attempt(self, mandate_id: uuid.UUID, *, amount: Decimal | None = None, attempted_at: datetime | None = None, bank_response_code: str | None = None, bank_response_message: str | None = None, ai_reasoning: str | None = None) -> PaymentAttempt:
        """Record the next pending collection attempt for an active mandate.

        When Razorpay is configured, this also creates a real Test/Live Mode
        Order for the attempt (best-effort: a Razorpay failure here still
        leaves a valid, simulated attempt — it just has no real order behind
        it, exactly like running with no Razorpay credentials at all).
        """
        def action() -> PaymentAttempt:
            mandate = self._require_active_mandate(mandate_id)
            attempt_amount = amount if amount is not None else mandate.amount
            self._require(attempt_amount > Decimal("0"), "attempt amount must be positive")
            latest = self.payment_attempts.get_latest_attempt(mandate_id)
            attempt_number = (latest.attempt_number if latest else 0) + 1
            values: dict[str, object] = {"mandate_id": mandate_id, "attempt_number": attempt_number, "amount": attempt_amount, "status": PaymentStatus.PENDING, "bank_response_code": bank_response_code, "bank_response_message": bank_response_message, "ai_reasoning": ai_reasoning}
            if attempted_at is not None:
                values["attempted_at"] = attempted_at
            attempt = self.payment_attempts.create(**values)

            if self.razorpay_client is not None:
                order_id = self._create_razorpay_order(attempt, currency=mandate.currency)
                if order_id is not None:
                    attempt = self.payment_attempts.update(attempt.id, razorpay_order_id=order_id) or attempt
            return attempt

        return self._in_transaction("record_payment_attempt", action)

    def mark_payment_success(self, payment_attempt_id: uuid.UUID, *, razorpay_payment_id: str | None = None) -> PaymentAttempt:
        """Mark a non-terminal payment attempt as successful, clear retry timing, and resolve any active retry schedule."""
        def action() -> PaymentAttempt:
            updated = self._apply_outcome(payment_attempt_id, PaymentStatus.SUCCEEDED, next_retry_at=None, razorpay_payment_id=razorpay_payment_id)
            self._resolve_active_retry_schedule(updated.mandate_id)
            return updated

        return self._in_transaction("mark_payment_success", action)

    def _resolve_active_retry_schedule(self, mandate_id: uuid.UUID) -> None:
        """Close out a mandate's retry cycle once a payment finally succeeds.

        Without this, a schedule that only ever gets touched on failure would
        stay ``pending`` forever after the retry that fixed it — showing up
        in the queue as though nothing had happened, the same symptom this
        whole change exists to fix.
        """
        schedule = self.retry_schedules.get_by_mandate(mandate_id)
        if schedule is not None and schedule.status not in _TERMINAL_RETRY_STATUSES:
            self.retry_schedules.update(schedule.id, status=RetryStatus.EXECUTED, actual_retry_time=datetime.now(timezone.utc))

    def mark_payment_failure(self, payment_attempt_id: uuid.UUID, *, decline_category: DeclineCategory | None = None, bank_response_code: str | None = None, bank_response_message: str | None = None, ai_reasoning: str | None = None, next_retry_at: datetime | None = None, razorpay_payment_id: str | None = None) -> PaymentAttempt:
        """Mark a non-successful payment attempt as failed and ensure an active retry schedule exists.

        Without this, a failure recorded outside the manual retry-schedule API
        (e.g. a real Razorpay webhook) would never get picked up by the
        background retry scheduler — nothing else in the system creates the
        first RetrySchedule row for a mandate.
        """
        def action() -> PaymentAttempt:
            updated = self._apply_outcome(
                payment_attempt_id,
                PaymentStatus.FAILED,
                decline_category=decline_category,
                bank_response_code=bank_response_code,
                bank_response_message=bank_response_message,
                ai_reasoning=ai_reasoning,
                next_retry_at=next_retry_at,
                razorpay_payment_id=razorpay_payment_id,
            )
            self._ensure_active_retry_schedule(updated.mandate_id, next_retry_at=next_retry_at)
            return updated

        return self._in_transaction("mark_payment_failure", action)

    def _ensure_active_retry_schedule(self, mandate_id: uuid.UUID, *, next_retry_at: datetime | None) -> None:
        """Create or reactivate the mandate's retry schedule so every failure gets followed up on.

        RetrySchedule.mandate_id is unique, so a mandate has at most one
        schedule ever. An already-active one (pending/scheduled) is left
        untouched — it's mid-cycle, and its own retry_count/recommended_time
        must not be reset out from under it.
        """
        schedule = self.retry_schedules.get_by_mandate(mandate_id)
        recommended_time = next_retry_at or (datetime.now(timezone.utc) + _DEFAULT_INITIAL_RETRY_DELAY)
        if schedule is None:
            self.retry_schedules.create(
                mandate_id=mandate_id,
                retry_strategy=_DEFAULT_RETRY_STRATEGY,
                recommended_time=recommended_time,
                retry_count=0,
                max_retries=_DEFAULT_MAX_RETRIES,
                status=RetryStatus.PENDING,
            )
            return
        if schedule.status in _TERMINAL_RETRY_STATUSES:
            self.retry_schedules.update(schedule.id, status=RetryStatus.PENDING, recommended_time=recommended_time, retry_count=0, actual_retry_time=None)

    def get_by_razorpay_order_id(self, razorpay_order_id: str) -> PaymentAttempt | None:
        """Resolve the payment attempt a Razorpay webhook event refers to."""
        return self.payment_attempts.get_by_razorpay_order_id(razorpay_order_id)

    def get_latest_attempt(self, mandate_id: uuid.UUID) -> PaymentAttempt | None:
        """Return the latest attempt for a mandate without opening a write transaction."""
        return self.payment_attempts.get_latest_attempt(mandate_id)

    def get_attempt(self, payment_attempt_id: uuid.UUID) -> PaymentAttempt:
        """Return a payment attempt or raise a domain-level not-found exception."""
        attempt = self.payment_attempts.get_by_id(payment_attempt_id)
        if attempt is None:
            raise NotFoundError("Payment attempt not found")
        return attempt

    def count_by_status(self) -> dict[PaymentStatus, int]:
        """Return the number of payment attempts grouped by outcome status."""
        return self.payment_attempts.count_by_status()

    def get_revenue_recovered(self) -> Decimal:
        """Return total revenue recovered by retries succeeding after a prior failure."""
        return self.payment_attempts.sum_recovered_amount()

    def get_daily_trend(self, *, days: int = 14) -> list[DailyPaymentTrend]:
        """Return real per-day attempt/collection/recovery figures for the last N days."""
        return self.payment_attempts.get_daily_trend(days=days)

    def list_unresolved_attempts(self, *, before: datetime | None = None, limit: int = 100) -> list[PaymentAttempt]:
        """Return attempts still awaiting a final outcome (pending/processing), oldest first."""
        return self.payment_attempts.list_unresolved(before=before, limit=limit)

    def list_attempts(self, mandate_id: uuid.UUID, *, status: PaymentStatus | None = None, offset: int = 0, limit: int = 100) -> list[PaymentAttempt]:
        """Return a mandate's attempt history, optionally filtered to one outcome."""
        if status is PaymentStatus.FAILED:
            return self.payment_attempts.get_failed_attempts(mandate_id, offset=offset, limit=limit)
        if status is PaymentStatus.SUCCEEDED:
            return self.payment_attempts.get_successful_attempts(mandate_id, offset=offset, limit=limit)
        return self.payment_attempts.get_attempt_history(mandate_id, offset=offset, limit=limit)

    def _apply_outcome(self, payment_attempt_id: uuid.UUID, status: PaymentStatus, **values: object) -> PaymentAttempt:
        """Validate and persist an attempt's outcome. Caller owns the transaction boundary."""
        attempt = self.payment_attempts.get_by_id(payment_attempt_id)
        if attempt is None:
            raise NotFoundError("Payment attempt not found")
        if attempt.status is PaymentStatus.SUCCEEDED and status is not PaymentStatus.SUCCEEDED:
            raise InvalidStateError("A successful payment attempt cannot be changed")
        updated = self.payment_attempts.update(payment_attempt_id, status=status, **values)
        if updated is None:
            raise NotFoundError("Payment attempt not found")
        return updated

    def _create_razorpay_order(self, attempt: PaymentAttempt, *, currency: str) -> str | None:
        """Best-effort real Razorpay order creation — never blocks recording the attempt."""
        client = self.razorpay_client
        if client is None:
            return None
        try:
            order = client.create_order(
                amount=attempt.amount,
                currency=currency,
                receipt=str(attempt.id),
                notes={"mandate_id": str(attempt.mandate_id), "payment_attempt_id": str(attempt.id)},
            )
            return order["id"]
        except RazorpayError as exc:
            logger.warning("Razorpay order creation failed for attempt %s: %s", attempt.id, exc)
            return None

    def _require_active_mandate(self, mandate_id: uuid.UUID) -> Mandate:
        mandate = self.mandates.get_by_id(mandate_id)
        if mandate is None:
            raise NotFoundError("Mandate not found")
        if mandate.status.value != "active":
            raise InvalidStateError("Payment attempts require an active mandate")
        return mandate
