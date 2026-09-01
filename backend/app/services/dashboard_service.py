"""Read-only aggregation of platform-wide metrics for the operator dashboard.

This service composes the existing domain services rather than querying
repositories directly, so it stays subject to the same layering rule as every
other service: business-facing reads are assembled here, persistence stays in
the repository layer beneath each domain service.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from backend.app.models.decision_log import DecisionLog
from backend.app.models.enums import MandateStatus, PaymentStatus
from backend.app.models.escalation import Escalation
from backend.app.models.retry_schedule import RetrySchedule
from backend.app.repositories.payment_attempt_repository import DailyPaymentTrend
from backend.app.services.communication_service import CommunicationService
from backend.app.services.decision_service import DecisionService
from backend.app.services.escalation_service import EscalationService
from backend.app.services.mandate_service import MandateService
from backend.app.services.payment_service import PaymentService
from backend.app.services.retry_service import RetryService


@dataclass(frozen=True)
class DashboardSummary:
    """Aggregated counters and recent activity shown on the dashboard landing view."""

    mandate_counts_by_status: dict[MandateStatus, int] = field(default_factory=dict)
    payment_attempt_counts_by_status: dict[PaymentStatus, int] = field(default_factory=dict)
    revenue_recovered: Decimal = Decimal("0")
    pending_retries: int = 0
    open_escalations: int = 0
    recent_decisions: list[DecisionLog] = field(default_factory=list)


@dataclass(frozen=True)
class ActivityEvent:
    """One real, timestamped workflow event — a decision made or a communication sent."""

    event_type: str
    mandate_id: uuid.UUID
    description: str
    timestamp: datetime


class DashboardService:
    """Assembles cross-domain read models; performs no writes of its own."""

    def __init__(
        self,
        mandate_service: MandateService,
        payment_service: PaymentService,
        retry_service: RetryService,
        escalation_service: EscalationService,
        decision_service: DecisionService,
        communication_service: CommunicationService,
    ) -> None:
        self.mandates = mandate_service
        self.payments = payment_service
        self.retries = retry_service
        self.escalations = escalation_service
        self.decisions = decision_service
        self.communications = communication_service

    def get_summary(self, *, recent_decision_limit: int = 10) -> DashboardSummary:
        """Return the aggregated counters that drive the dashboard landing view."""
        return DashboardSummary(
            mandate_counts_by_status=self.mandates.count_by_status(),
            payment_attempt_counts_by_status=self.payments.count_by_status(),
            revenue_recovered=self.payments.get_revenue_recovered(),
            pending_retries=self.retries.count_pending_retries(),
            open_escalations=self.escalations.count_open_escalations(),
            recent_decisions=self.decisions.list_decisions(limit=recent_decision_limit),
        )

    def get_trend(self, *, days: int = 14) -> list[DailyPaymentTrend]:
        """Return the real per-day payment trend that backs the dashboard's charts."""
        return self.payments.get_daily_trend(days=days)

    def get_retry_queue(self, *, offset: int = 0, limit: int = 100) -> list[RetrySchedule]:
        """Return the pending retry queue for the operator's retry-queue view."""
        return self.retries.list_pending_retries(offset=offset, limit=limit)

    def get_open_escalations(self, *, offset: int = 0, limit: int = 100) -> list[Escalation]:
        """Return unresolved escalations for the operator's escalation queue."""
        return self.escalations.list_open_escalations(offset=offset, limit=limit)

    def get_recent_activity(self, *, limit: int = 20) -> list[ActivityEvent]:
        """Return the most recent real workflow events, newest first.

        Merges decisions and communications — the two domain records with a
        reliable per-event timestamp — across every mandate. Escalation
        records have no creation timestamp (only resolved_at, null while
        open) so they're not included here.
        """
        events = [
            ActivityEvent(event_type="decision", mandate_id=decision.mandate_id, description=decision.explanation, timestamp=decision.created_at)
            for decision in self.decisions.list_decisions(limit=limit)
        ] + [
            ActivityEvent(event_type="communication", mandate_id=communication.mandate_id, description=communication.message, timestamp=communication.sent_at)
            for communication in self.communications.list_communications(limit=limit)
        ]
        events.sort(key=lambda event: event.timestamp, reverse=True)
        return events[:limit]
