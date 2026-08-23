"""Domain enums persisted by the SQLAlchemy ORM models."""

from enum import Enum


def enum_values(enum_class: type[Enum]) -> list[str]:
    """Return enum values for SQLAlchemy persistence instead of member names."""
    return [member.value for member in enum_class]


class MandateStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    COMPLETED = "completed"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    RETRY_SCHEDULED = "retry_scheduled"


class RetryStatus(str, Enum):
    PENDING = "pending"
    SCHEDULED = "scheduled"
    EXECUTED = "executed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"
    EXHAUSTED = "exhausted"


class DeclineCategory(str, Enum):
    INSUFFICIENT_FUNDS = "insufficient_funds"
    BANK_UNAVAILABLE = "bank_unavailable"
    AUTHENTICATION_REQUIRED = "authentication_required"
    MANDATE_INACTIVE = "mandate_inactive"
    LIMIT_EXCEEDED = "limit_exceeded"
    ACCOUNT_CLOSED = "account_closed"
    TECHNICAL_ERROR = "technical_error"
    UNKNOWN = "unknown"


class CommunicationChannel(str, Enum):
    EMAIL = "email"
    SMS = "sms"
    WHATSAPP = "whatsapp"
    PUSH = "push"


class DeliveryStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"


class EscalationLevel(str, Enum):
    LEVEL_1 = "level_1"
    LEVEL_2 = "level_2"
    LEVEL_3 = "level_3"
    CRITICAL = "critical"
