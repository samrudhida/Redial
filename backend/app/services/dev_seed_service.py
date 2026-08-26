"""Developer-only realistic demo-data generator for the Mandate Retry Sequencer.

This module is never imported unless the API layer decides to mount its
route (see backend/app/api/router.py, gated on APP_ENV == "development").
It exists purely to make every frontend page (Dashboard, Mandates, Payments,
Retry Queue, AI Decisions, Communications, Escalations, Analytics) show
meaningful data during local development/demos.

Design notes:
  - Every write goes through the existing domain services (MandateService,
    PaymentService, RetryService, DecisionService, CommunicationService,
    EscalationService) so all real business validation runs exactly as it
    would for a real user action.
  - A handful of fields have no service-layer way to override a
    ``server_default=func.now()`` timestamp (Mandate.created_at/updated_at,
    Communication.sent_at, DecisionLog.created_at) or to reach a lifecycle
    status no transition method produces (MandateStatus.EXPIRED/COMPLETED).
    For exactly those fields, this module calls the repository's existing
    generic ``update()`` through the service's already-public repository
    attribute (e.g. ``mandate_service.mandates``) — the same ORM-level method
    every other route already relies on, never raw SQL text.
  - Demo data is namespaced under the "DEMO-" mandate_reference prefix (and a
    matching "DEMO-CUST-" customer_id prefix), so deletion can find exactly
    what this tool created and nothing a real user entered.
"""

from __future__ import annotations

import random
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.enums import (
    CommunicationChannel,
    DeclineCategory,
    DeliveryStatus,
    EscalationLevel,
    MandateStatus,
    PaymentStatus,
    RetryStatus,
)
from backend.app.models.mandate import Mandate
from backend.app.services.communication_service import CommunicationService
from backend.app.services.decision_service import DecisionService
from backend.app.services.escalation_service import EscalationService
from backend.app.services.mandate_service import MandateService
from backend.app.services.payment_service import PaymentService
from backend.app.services.retry_service import RetryService

DEMO_REFERENCE_PREFIX = "DEMO-"
DEMO_CUSTOMER_PREFIX = "DEMO-CUST-"

BANK_NAMES = [
    "HDFC Bank", "ICICI Bank", "State Bank of India", "Axis Bank", "Kotak Mahindra Bank",
    "Punjab National Bank", "Bank of Baroda", "Yes Bank", "IndusInd Bank", "Federal Bank",
]

AMOUNT_CHOICES = [299, 499, 999, 1499, 2999, 4999, 7999, 9999, 14999, 19999]

SOFT_DECLINE_CATEGORIES = [
    DeclineCategory.INSUFFICIENT_FUNDS,
    DeclineCategory.BANK_UNAVAILABLE,
    DeclineCategory.TECHNICAL_ERROR,
    DeclineCategory.LIMIT_EXCEEDED,
]
HARD_DECLINE_CATEGORIES = [
    DeclineCategory.MANDATE_INACTIVE,
    DeclineCategory.ACCOUNT_CLOSED,
    DeclineCategory.AUTHENTICATION_REQUIRED,
]

RETRY_STRATEGIES = ["exponential_backoff", "fixed_interval_24h", "fixed_interval_72h", "next_business_day"]

SOFT_DECLINE_EXPLANATIONS: dict[DeclineCategory, str] = {
    DeclineCategory.INSUFFICIENT_FUNDS: "Bank declined due to insufficient funds in the linked account. Classified as a soft decline — eligible for retry after the RBI-mandated 24-hour cooldown.",
    DeclineCategory.BANK_UNAVAILABLE: "Issuing bank's authorization server timed out. Classified as a transient soft decline — retry scheduled per standard cooldown.",
    DeclineCategory.TECHNICAL_ERROR: "A technical error occurred while processing the mandate debit. Classified as a soft decline — safe to retry.",
    DeclineCategory.LIMIT_EXCEEDED: "Transaction exceeds the customer's daily debit limit. Classified as a soft decline — retry scheduled for the next settlement cycle.",
}
HARD_DECLINE_EXPLANATIONS: dict[DeclineCategory, str] = {
    DeclineCategory.MANDATE_INACTIVE: "Bank reports the underlying mandate as inactive or revoked. Classified as a hard decline — no further automated retries permitted; customer must re-authorize.",
    DeclineCategory.ACCOUNT_CLOSED: "The linked bank account has been closed. Classified as a hard decline — customer must update payment details.",
    DeclineCategory.AUTHENTICATION_REQUIRED: "Additional customer authentication is required by the bank before this mandate can be honored. Classified as a hard decline for automated-retry purposes.",
}

ESCALATION_REASONS = [
    "Maximum retry attempts exhausted without a successful payment.",
    "Repeated soft declines across all scheduled retries — recommend manual review.",
    "Customer has not responded to payment-method update requests after a hard decline.",
]

ASSIGNEES = [None, None, None, "support-queue", "merchant-ops"]


@dataclass
class SeedSummary:
    mandates_created: int = 0
    payment_attempts_created: int = 0
    retry_schedules_created: int = 0
    decisions_created: int = 0
    communications_created: int = 0
    escalations_created: int = 0


def _confidence(low: float, high: float) -> Decimal:
    return Decimal(str(round(random.uniform(low, high), 4)))


def _amount() -> Decimal:
    return Decimal(random.choice(AMOUNT_CHOICES)) + Decimal(random.choice(["0.00", "0.50", "0.99"]))


class DevSeedService:
    """Generates and removes internally-consistent demo data via the real service layer."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.mandate_service = MandateService(session)
        self.payment_service = PaymentService(session)
        self.retry_service = RetryService(session)
        self.decision_service = DecisionService(session)
        self.communication_service = CommunicationService(session)
        self.escalation_service = EscalationService(session)

    def _set_retry_schedule(self, mandate_id: uuid.UUID, retry_strategy: str, recommended_time: datetime, *, max_retries: int = 3):
        """Set the narrative retry-schedule fields for this scenario.

        PaymentService.mark_payment_failure already created a schedule (with
        its own defaults) as soon as the preceding failure was recorded, and
        RetrySchedule.mandate_id is unique — so this updates that schedule
        with the scenario's specific strategy/timing rather than creating a
        second one, which would violate the uniqueness constraint.
        """
        existing = self.retry_service.get_retry_schedule_for_mandate(mandate_id)
        if existing is None:
            return self.retry_service.create_retry_schedule(mandate_id, retry_strategy, recommended_time, max_retries=max_retries)
        return self.retry_service.update_retry_schedule(existing.id, retry_strategy=retry_strategy, recommended_time=recommended_time, max_retries=max_retries)

    # ------------------------------------------------------------------ #
    # Seeding
    # ------------------------------------------------------------------ #

    def seed(self, count: int) -> SeedSummary:
        summary = SeedSummary()
        now = datetime.now(timezone.utc)
        customer_pool_size = max(30, count // 3)

        for _ in range(count):
            created_at = now - timedelta(
                days=random.randint(0, 60), hours=random.randint(0, 23), minutes=random.randint(0, 59),
            )
            customer_id = f"{DEMO_CUSTOMER_PREFIX}{random.randint(1, customer_pool_size):04d}"
            reference = f"{DEMO_REFERENCE_PREFIX}{uuid.uuid4().hex[:10].upper()}"
            amount = _amount()

            mandate = self.mandate_service.register_mandate(
                customer_id,
                reference,
                amount,
                bank_name=random.choice(BANK_NAMES),
                account_last4=f"{random.randint(0, 9999):04d}",
            )
            summary.mandates_created += 1
            self._backdate(self.mandate_service.mandates, mandate.id, created_at=created_at, updated_at=created_at)

            scenario = random.choices(
                ["first_try_success", "soft_decline_retry_success", "soft_decline_pending_retry", "hard_decline", "repeated_failures_escalation", "in_flight"],
                weights=[28, 24, 19, 14, 9, 6],
                k=1,
            )[0]
            natural_status = self._run_scenario(scenario, mandate.id, amount, created_at, now, summary)

            final_status = natural_status
            if random.random() < 0.06:
                final_status = MandateStatus.EXPIRED
            elif natural_status is MandateStatus.ACTIVE and random.random() < 0.15:
                final_status = MandateStatus.COMPLETED

            self._apply_final_status(mandate.id, final_status)

        return summary

    def _run_scenario(
        self,
        scenario: str,
        mandate_id: uuid.UUID,
        amount: Decimal,
        created_at: datetime,
        now: datetime,
        summary: SeedSummary,
    ) -> MandateStatus:
        if scenario == "first_try_success":
            return self._scenario_first_try_success(mandate_id, amount, created_at, summary)
        if scenario == "soft_decline_retry_success":
            return self._scenario_soft_decline_retry_success(mandate_id, amount, created_at, summary)
        if scenario == "soft_decline_pending_retry":
            return self._scenario_soft_decline_pending_retry(mandate_id, amount, created_at, now, summary)
        if scenario == "hard_decline":
            return self._scenario_hard_decline(mandate_id, amount, created_at, summary)
        if scenario == "repeated_failures_escalation":
            return self._scenario_repeated_failures_escalation(mandate_id, amount, created_at, summary)
        return self._scenario_in_flight(mandate_id, amount, now, summary)

    def _scenario_first_try_success(self, mandate_id: uuid.UUID, amount: Decimal, created_at: datetime, summary: SeedSummary) -> MandateStatus:
        attempt_time = created_at + timedelta(minutes=random.randint(1, 30))
        attempt = self.payment_service.record_payment_attempt(mandate_id, amount=amount, attempted_at=attempt_time)
        self.payment_service.mark_payment_success(attempt.id)
        summary.payment_attempts_created += 1

        self._record_decision(
            mandate_id, "decline_classification",
            "Payment succeeded on first attempt; no retry action required.",
            _confidence(0.9, 0.99), attempt_time + timedelta(minutes=1), summary,
        )

        if random.random() < 0.6:
            channel = random.choice([CommunicationChannel.EMAIL, CommunicationChannel.SMS])
            message = f"Your payment of Rs.{amount} was processed successfully. Thank you."
            self._record_communication(mandate_id, channel, message, attempt_time + timedelta(minutes=2), summary)

        return MandateStatus.ACTIVE

    def _scenario_soft_decline_retry_success(self, mandate_id: uuid.UUID, amount: Decimal, created_at: datetime, summary: SeedSummary) -> MandateStatus:
        category = random.choice(SOFT_DECLINE_CATEGORIES)
        attempt1_time = created_at + timedelta(minutes=random.randint(1, 30))
        attempt1 = self.payment_service.record_payment_attempt(mandate_id, amount=amount, attempted_at=attempt1_time)
        self.payment_service.mark_payment_failure(attempt1.id, decline_category=category, bank_response_message=f"Declined: {category.value}")
        summary.payment_attempts_created += 1

        self._record_decision(mandate_id, "decline_classification", SOFT_DECLINE_EXPLANATIONS[category], _confidence(0.85, 0.98), attempt1_time + timedelta(minutes=1), summary)

        retry_time = attempt1_time + timedelta(hours=24)
        retry_schedule = self._set_retry_schedule(mandate_id, random.choice(RETRY_STRATEGIES), retry_time, max_retries=3)
        summary.retry_schedules_created += 1
        self._record_decision(
            mandate_id, "retry_schedule",
            f"Scheduling retry for {retry_time:%Y-%m-%d %H:%M} UTC; 24-hour cooldown requirement satisfied.",
            _confidence(0.8, 0.95), attempt1_time + timedelta(minutes=2), summary,
        )
        self._record_communication(
            mandate_id, random.choice([CommunicationChannel.SMS, CommunicationChannel.WHATSAPP]),
            f"Your payment of Rs.{amount} could not be processed. We'll automatically retry on {retry_time:%d %b, %I:%M %p}.",
            attempt1_time + timedelta(minutes=3), summary,
        )

        attempt2_time = retry_time + timedelta(minutes=random.randint(5, 60))
        attempt2 = self.payment_service.record_payment_attempt(mandate_id, amount=amount, attempted_at=attempt2_time)
        self.payment_service.mark_payment_success(attempt2.id)
        summary.payment_attempts_created += 1
        self.retry_service.update_retry_schedule(retry_schedule.id, status=RetryStatus.EXECUTED, actual_retry_time=attempt2_time, retry_count=1)
        self._record_communication(
            mandate_id, random.choice([CommunicationChannel.SMS, CommunicationChannel.EMAIL]),
            f"Good news! Your payment of Rs.{amount} was successfully processed on retry.",
            attempt2_time + timedelta(minutes=1), summary,
        )

        return MandateStatus.ACTIVE

    def _scenario_soft_decline_pending_retry(self, mandate_id: uuid.UUID, amount: Decimal, created_at: datetime, now: datetime, summary: SeedSummary) -> MandateStatus:
        category = random.choice(SOFT_DECLINE_CATEGORIES)
        attempt_time = created_at + timedelta(minutes=random.randint(1, 30))
        attempt = self.payment_service.record_payment_attempt(mandate_id, amount=amount, attempted_at=attempt_time)
        self.payment_service.mark_payment_failure(attempt.id, decline_category=category, bank_response_message=f"Declined: {category.value}")
        summary.payment_attempts_created += 1

        self._record_decision(mandate_id, "decline_classification", SOFT_DECLINE_EXPLANATIONS[category], _confidence(0.85, 0.98), attempt_time + timedelta(minutes=1), summary)

        # Mixed relative to "now": some overdue, some genuinely upcoming — realistic for a live queue.
        retry_time = now + timedelta(hours=random.randint(-48, 72))
        retry_schedule = self._set_retry_schedule(mandate_id, random.choice(RETRY_STRATEGIES), retry_time, max_retries=3)
        summary.retry_schedules_created += 1
        if random.random() < 0.4:
            self.retry_service.update_retry_schedule(retry_schedule.id, status=RetryStatus.SCHEDULED)

        self._record_decision(
            mandate_id, "retry_schedule",
            f"Scheduling retry for {retry_time:%Y-%m-%d %H:%M} UTC; 24-hour cooldown requirement satisfied.",
            _confidence(0.8, 0.95), attempt_time + timedelta(minutes=2), summary,
        )
        self._record_communication(
            mandate_id, random.choice([CommunicationChannel.SMS, CommunicationChannel.WHATSAPP]),
            f"Your payment of Rs.{amount} could not be processed. We'll automatically retry on {retry_time:%d %b, %I:%M %p}.",
            attempt_time + timedelta(minutes=3), summary,
        )

        return MandateStatus.ACTIVE

    def _scenario_hard_decline(self, mandate_id: uuid.UUID, amount: Decimal, created_at: datetime, summary: SeedSummary) -> MandateStatus:
        category = random.choice(HARD_DECLINE_CATEGORIES)
        attempt_time = created_at + timedelta(minutes=random.randint(1, 30))
        attempt = self.payment_service.record_payment_attempt(mandate_id, amount=amount, attempted_at=attempt_time)
        self.payment_service.mark_payment_failure(attempt.id, decline_category=category, bank_response_message=f"Declined: {category.value}")
        summary.payment_attempts_created += 1

        self._record_decision(mandate_id, "decline_classification", HARD_DECLINE_EXPLANATIONS[category], _confidence(0.9, 0.99), attempt_time + timedelta(minutes=1), summary)
        self._record_communication(
            mandate_id, CommunicationChannel.EMAIL,
            f"We were unable to process your payment of Rs.{amount}. Please update your payment method to avoid service interruption.",
            attempt_time + timedelta(minutes=2), summary,
        )

        return MandateStatus.PAUSED if random.random() < 0.6 else MandateStatus.CANCELLED

    def _scenario_repeated_failures_escalation(self, mandate_id: uuid.UUID, amount: Decimal, created_at: datetime, summary: SeedSummary) -> MandateStatus:
        attempt1_time = created_at + timedelta(minutes=random.randint(1, 30))
        attempt1 = self.payment_service.record_payment_attempt(mandate_id, amount=amount, attempted_at=attempt1_time)
        category1 = random.choice(SOFT_DECLINE_CATEGORIES)
        self.payment_service.mark_payment_failure(attempt1.id, decline_category=category1, bank_response_message=f"Declined: {category1.value}")
        summary.payment_attempts_created += 1
        self._record_decision(mandate_id, "decline_classification", SOFT_DECLINE_EXPLANATIONS[category1], _confidence(0.85, 0.98), attempt1_time + timedelta(minutes=1), summary)

        retry_time = attempt1_time + timedelta(hours=24)
        retry_schedule = self._set_retry_schedule(mandate_id, random.choice(RETRY_STRATEGIES), retry_time, max_retries=3)
        summary.retry_schedules_created += 1

        attempt2_time = retry_time + timedelta(minutes=random.randint(5, 60))
        attempt2 = self.payment_service.record_payment_attempt(mandate_id, amount=amount, attempted_at=attempt2_time)
        category2 = random.choice(SOFT_DECLINE_CATEGORIES)
        self.payment_service.mark_payment_failure(attempt2.id, decline_category=category2, bank_response_message=f"Declined: {category2.value}")
        summary.payment_attempts_created += 1
        self.retry_service.update_retry_schedule(retry_schedule.id, retry_count=1, actual_retry_time=attempt2_time)
        self._record_decision(mandate_id, "decline_classification", SOFT_DECLINE_EXPLANATIONS[category2], _confidence(0.8, 0.95), attempt2_time + timedelta(minutes=1), summary)
        self._record_communication(
            mandate_id, random.choice([CommunicationChannel.SMS, CommunicationChannel.WHATSAPP]),
            f"Your payment of Rs.{amount} has failed again. We'll try once more before escalating.",
            attempt2_time + timedelta(minutes=2), summary,
        )

        retry2_time = attempt2_time + timedelta(hours=random.choice([24, 72]))
        attempt3_time = retry2_time + timedelta(minutes=random.randint(5, 60))
        attempt3 = self.payment_service.record_payment_attempt(mandate_id, amount=amount, attempted_at=attempt3_time)
        category3 = random.choice(SOFT_DECLINE_CATEGORIES)
        self.payment_service.mark_payment_failure(attempt3.id, decline_category=category3, bank_response_message=f"Declined: {category3.value}")
        summary.payment_attempts_created += 1
        self.retry_service.update_retry_schedule(retry_schedule.id, retry_count=3, status=RetryStatus.EXHAUSTED, actual_retry_time=attempt3_time)
        self._record_decision(mandate_id, "decline_classification", SOFT_DECLINE_EXPLANATIONS[category3], _confidence(0.8, 0.95), attempt3_time + timedelta(minutes=1), summary)

        escalation_reason = random.choice(ESCALATION_REASONS)
        escalation_level = random.choices(
            [EscalationLevel.LEVEL_1, EscalationLevel.LEVEL_2, EscalationLevel.LEVEL_3, EscalationLevel.CRITICAL],
            weights=[50, 30, 15, 5], k=1,
        )[0]
        escalation = self.escalation_service.create_escalation(mandate_id, escalation_reason, escalation_level=escalation_level, assigned_to=random.choice(ASSIGNEES))
        summary.escalations_created += 1
        self._record_decision(
            mandate_id, "escalation_recommendation",
            f"Retry attempts exhausted ({escalation_reason.lower()}) — recommending escalation to {escalation_level.value.replace('_', ' ')}.",
            _confidence(0.6, 0.85), attempt3_time + timedelta(minutes=2), summary,
        )
        self._record_communication(
            mandate_id, CommunicationChannel.EMAIL,
            "We were unable to process your payment after multiple attempts. Our support team has been notified and will reach out shortly.",
            attempt3_time + timedelta(minutes=3), summary,
        )

        if random.random() < 0.5:
            resolved_at = attempt3_time + timedelta(days=random.randint(1, 5))
            self.escalation_service.resolve_escalation(escalation.id, resolved_at=resolved_at)

        return MandateStatus.PAUSED if random.random() < 0.3 else MandateStatus.CANCELLED

    def _scenario_in_flight(self, mandate_id: uuid.UUID, amount: Decimal, now: datetime, summary: SeedSummary) -> MandateStatus:
        attempt_time = now - timedelta(minutes=random.randint(1, 120))
        attempt = self.payment_service.record_payment_attempt(mandate_id, amount=amount, attempted_at=attempt_time)
        summary.payment_attempts_created += 1
        if random.random() < 0.5:
            self.payment_service.payment_attempts.update(attempt.id, status=PaymentStatus.PROCESSING)
            self.session.commit()
        return MandateStatus.ACTIVE

    # ------------------------------------------------------------------ #
    # Helpers shared across scenarios
    # ------------------------------------------------------------------ #

    def _record_decision(self, mandate_id: uuid.UUID, decision_type: str, explanation: str, confidence: Decimal, created_at: datetime, summary: SeedSummary) -> None:
        decision = self.decision_service.record_ai_decision(mandate_id, decision_type, explanation, confidence)
        self._backdate(self.decision_service.decision_logs, decision.id, created_at=created_at)
        summary.decisions_created += 1

    def _record_communication(self, mandate_id: uuid.UUID, channel: CommunicationChannel, message: str, sent_at: datetime, summary: SeedSummary) -> None:
        if channel is CommunicationChannel.SMS:
            communication = self.communication_service.record_sms(mandate_id, message)
        elif channel is CommunicationChannel.EMAIL:
            communication = self.communication_service.record_email(mandate_id, message)
        else:
            communication = self.communication_service.record_whatsapp(mandate_id, message)
        self._backdate(self.communication_service.communications, communication.id, sent_at=sent_at)
        if random.random() < 0.85:
            self.communication_service.update_delivery_status(communication.id, random.choice([DeliveryStatus.SENT, DeliveryStatus.DELIVERED]))
        summary.communications_created += 1

    def _backdate(self, repository, entity_id: uuid.UUID, **values: object) -> None:
        """Directly patches a server_default timestamp the service layer has no way to override.

        Uses the repository's existing generic ``update()`` (ORM-level, no raw SQL) — the same
        method every route already calls — then commits, since ``update()`` only flushes.
        """
        repository.update(entity_id, **values)
        self.session.commit()

    def _apply_final_status(self, mandate_id: uuid.UUID, status: MandateStatus) -> None:
        if status is MandateStatus.ACTIVE:
            return
        if status is MandateStatus.PAUSED:
            self.mandate_service.pause_mandate(mandate_id)
        elif status is MandateStatus.CANCELLED:
            self.mandate_service.cancel_mandate(mandate_id)
        else:
            # EXPIRED / COMPLETED: no service-layer transition reaches these terminal
            # statuses (only a real-world clock or a completed one-time debit would),
            # so the seed tool sets them directly via the repository, exactly like the
            # timestamp backdating above.
            self.mandate_service.mandates.update(mandate_id, status=status)
            self.session.commit()

    # ------------------------------------------------------------------ #
    # Deletion
    # ------------------------------------------------------------------ #

    def delete_seed_data(self) -> int:
        """Deletes every mandate created by this tool (and, via ON DELETE CASCADE,
        every payment attempt / retry schedule / decision / communication /
        escalation attached to it). Never touches a mandate outside the
        DEMO- namespace, so real user data is untouched.
        """
        statement = select(Mandate).where(Mandate.mandate_reference.like(f"{DEMO_REFERENCE_PREFIX}%"))
        demo_mandates = list(self.session.execute(statement).scalars().all())

        deleted = 0
        for mandate in demo_mandates:
            if self.mandate_service.mandates.delete(mandate.id):
                self.session.commit()
                deleted += 1

        return deleted
