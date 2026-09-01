"""Data access queries for individual payment collection attempts."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import Date, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.models.enums import PaymentStatus
from backend.app.models.payment_attempt import PaymentAttempt
from backend.app.repositories.base_repository import BaseRepository


@dataclass(frozen=True)
class DailyPaymentTrend:
    """One day's worth of real payment-attempt outcomes — never a fabricated point."""

    day: date
    attempts_total: int = 0
    attempts_succeeded: int = 0
    attempts_failed: int = 0
    collected_amount: Decimal = field(default_factory=lambda: Decimal("0"))
    recovered_amount: Decimal = field(default_factory=lambda: Decimal("0"))


class PaymentAttemptRepository(BaseRepository[PaymentAttempt]):
    """Repository for attempt history and outcome-oriented read queries."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, PaymentAttempt)

    def get_by_razorpay_order_id(self, razorpay_order_id: str) -> PaymentAttempt | None:
        """Resolve the payment attempt a Razorpay order/payment webhook event refers to."""
        try:
            statement = select(PaymentAttempt).where(PaymentAttempt.razorpay_order_id == razorpay_order_id)
            return self.session.execute(statement).scalars().first()
        except SQLAlchemyError as exc:
            self._raise_database_error("get_by_razorpay_order_id", exc)

    def get_latest_attempt(self, mandate_id: uuid.UUID) -> PaymentAttempt | None:
        """Return the latest attempt for a mandate, preferring attempt sequence."""
        try:
            statement = select(PaymentAttempt).where(PaymentAttempt.mandate_id == mandate_id).order_by(PaymentAttempt.attempt_number.desc(), PaymentAttempt.attempted_at.desc()).limit(1)
            return self.session.execute(statement).scalars().first()
        except SQLAlchemyError as exc:
            self._raise_database_error("get_latest_attempt", exc)

    def get_failed_attempts(self, mandate_id: uuid.UUID, *, offset: int = 0, limit: int = 100) -> list[PaymentAttempt]:
        """Return failed attempts for a mandate, newest first."""
        return self._get_by_status(mandate_id, PaymentStatus.FAILED, offset=offset, limit=limit)

    def get_successful_attempts(self, mandate_id: uuid.UUID, *, offset: int = 0, limit: int = 100) -> list[PaymentAttempt]:
        """Return successful attempts for a mandate, newest first."""
        return self._get_by_status(mandate_id, PaymentStatus.SUCCEEDED, offset=offset, limit=limit)

    def get_attempt_history(self, mandate_id: uuid.UUID, *, offset: int = 0, limit: int = 100) -> list[PaymentAttempt]:
        """Return all payment attempts in chronological attempt order."""
        self._validate_pagination(offset, limit)
        try:
            statement = select(PaymentAttempt).where(PaymentAttempt.mandate_id == mandate_id).order_by(PaymentAttempt.attempt_number, PaymentAttempt.attempted_at).offset(offset).limit(limit)
            return list(self.session.execute(statement).scalars().all())
        except SQLAlchemyError as exc:
            self._raise_database_error("get_attempt_history", exc)

    def list_unresolved(self, *, before: datetime | None = None, limit: int = 100) -> list[PaymentAttempt]:
        """Return attempts still awaiting a final outcome (pending/processing), oldest first.

        Only attempts started at or before ``before`` (default now) are
        eligible — mirrors RetryScheduleRepository.get_due_retries's ``as_of``
        idiom, so a freshly created attempt isn't immediately eligible.
        """
        self._validate_pagination(0, limit)
        cutoff = before or datetime.now(timezone.utc)
        try:
            statement = (
                select(PaymentAttempt)
                .where(PaymentAttempt.status.in_((PaymentStatus.PENDING, PaymentStatus.PROCESSING)), PaymentAttempt.attempted_at <= cutoff)
                .order_by(PaymentAttempt.attempted_at)
                .limit(limit)
            )
            return list(self.session.execute(statement).scalars().all())
        except SQLAlchemyError as exc:
            self._raise_database_error("list_unresolved", exc)

    def count_by_status(self) -> dict[PaymentStatus, int]:
        """Return the number of payment attempts grouped by outcome status."""
        try:
            statement = select(PaymentAttempt.status, func.count(PaymentAttempt.id)).group_by(PaymentAttempt.status)
            rows = self.session.execute(statement).all()
            return {status: count for status, count in rows}
        except SQLAlchemyError as exc:
            self._raise_database_error("count_by_status", exc)

    def sum_recovered_amount(self) -> Decimal:
        """Return total revenue recovered: succeeded attempts after a prior failure.

        The first attempt on a mandate is not "recovered" revenue since nothing
        failed beforehand; only attempts numbered two or later that succeeded
        represent money a retry sequence brought back.
        """
        try:
            statement = select(func.coalesce(func.sum(PaymentAttempt.amount), 0)).where(
                PaymentAttempt.status == PaymentStatus.SUCCEEDED,
                PaymentAttempt.attempt_number > 1,
            )
            total = self.session.execute(statement).scalar_one()
            return Decimal(total)
        except SQLAlchemyError as exc:
            self._raise_database_error("sum_recovered_amount", exc)

    def get_daily_trend(self, *, days: int = 14) -> list[DailyPaymentTrend]:
        """Return real per-day attempt/collection/recovery figures for the last N days.

        Every day in the window is present in the result (zero-filled when
        there were no attempts that day) so callers get a continuous series
        to chart, never gaps — but every non-zero value comes straight from
        recorded payment attempts.
        """
        try:
            today = datetime.now(timezone.utc).date()
            start_day = today - timedelta(days=days - 1)
            cutoff = datetime.combine(start_day, datetime.min.time(), tzinfo=timezone.utc)
            day_expr = func.date(PaymentAttempt.attempted_at, type_=Date)

            counts_statement = (
                select(day_expr, PaymentAttempt.status, func.count(PaymentAttempt.id), func.coalesce(func.sum(PaymentAttempt.amount), 0))
                .where(PaymentAttempt.attempted_at >= cutoff)
                .group_by(day_expr, PaymentAttempt.status)
            )
            recovered_statement = (
                select(day_expr, func.coalesce(func.sum(PaymentAttempt.amount), 0))
                .where(PaymentAttempt.attempted_at >= cutoff, PaymentAttempt.status == PaymentStatus.SUCCEEDED, PaymentAttempt.attempt_number > 1)
                .group_by(day_expr)
            )

            totals: dict[date, dict[str, Decimal | int]] = {}
            for day, status, count, amount in self.session.execute(counts_statement).all():
                bucket = totals.setdefault(day, {"total": 0, "succeeded": 0, "failed": 0, "collected": Decimal("0")})
                bucket["total"] = int(bucket["total"]) + count
                if status == PaymentStatus.SUCCEEDED:
                    bucket["succeeded"] = int(bucket["succeeded"]) + count
                    bucket["collected"] = Decimal(bucket["collected"]) + Decimal(amount)
                elif status == PaymentStatus.FAILED:
                    bucket["failed"] = int(bucket["failed"]) + count

            recovered_by_day: dict[date, Decimal] = {day: Decimal(amount) for day, amount in self.session.execute(recovered_statement).all()}

            trend: list[DailyPaymentTrend] = []
            for offset in range(days):
                day = start_day + timedelta(days=offset)
                bucket = totals.get(day)
                trend.append(
                    DailyPaymentTrend(
                        day=day,
                        attempts_total=int(bucket["total"]) if bucket else 0,
                        attempts_succeeded=int(bucket["succeeded"]) if bucket else 0,
                        attempts_failed=int(bucket["failed"]) if bucket else 0,
                        collected_amount=Decimal(bucket["collected"]) if bucket else Decimal("0"),
                        recovered_amount=recovered_by_day.get(day, Decimal("0")),
                    )
                )
            return trend
        except SQLAlchemyError as exc:
            self._raise_database_error("get_daily_trend", exc)

    def _get_by_status(self, mandate_id: uuid.UUID, status: PaymentStatus, *, offset: int, limit: int) -> list[PaymentAttempt]:
        self._validate_pagination(offset, limit)
        try:
            statement = select(PaymentAttempt).where(PaymentAttempt.mandate_id == mandate_id, PaymentAttempt.status == status).order_by(PaymentAttempt.attempted_at.desc()).offset(offset).limit(limit)
            return list(self.session.execute(statement).scalars().all())
        except SQLAlchemyError as exc:
            self._raise_database_error("get_attempts_by_status", exc)
