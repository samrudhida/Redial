import type { DecisionLog } from './decision'
import type { MandateStatus, PaymentStatus } from './enums'

/**
 * Mirrors DashboardSummaryResponse in backend/app/api/routes/dashboard.py.
 * Decimal fields (revenue_recovered) are serialized by the API as strings,
 * not numbers.
 */
export interface DashboardSummary {
  /** Only statuses with at least one mandate are present as keys. */
  mandate_counts_by_status: Partial<Record<MandateStatus, number>>
  /** Only statuses with at least one payment attempt are present as keys. */
  payment_attempt_counts_by_status: Partial<Record<PaymentStatus, number>>
  /** Decimal amount, serialized as a string (e.g. "500.00"). */
  revenue_recovered: string
  pending_retries: number
  open_escalations: number
  recent_decisions: DecisionLog[]
}

/**
 * Mirrors DailyTrendPointResponse in backend/app/api/routes/dashboard.py.
 * Every day in the requested window is present, zero-filled when there were
 * no payment attempts that day — not sparse, so it charts as a continuous series.
 */
export interface DailyTrendPoint {
  /** ISO date, e.g. "2026-08-20" (no time component). */
  day: string
  attempts_total: number
  attempts_succeeded: number
  attempts_failed: number
  /** Decimal amount, serialized as a string (e.g. "500.00"). */
  collected_amount: string
  /** Decimal amount, serialized as a string (e.g. "500.00"). */
  recovered_amount: string
}

/**
 * Mirrors ActivityEventResponse in backend/app/api/routes/dashboard.py.
 * A real decision or communication event, not a synthetic audit log.
 */
export interface ActivityEvent {
  event_type: 'decision' | 'communication'
  mandate_id: string
  description: string
  timestamp: string
}
