import type { RetryStatus } from './enums'

/**
 * Mirrors RetryScheduleResponse in backend/app/api/routes/retry_schedules.py.
 * Note: the backend has no "priority" concept for retry schedules — do not
 * invent one. The only ordering signal is `recommended_time`.
 */
export interface RetrySchedule {
  id: string
  mandate_id: string
  retry_strategy: string
  recommended_time: string
  actual_retry_time: string | null
  retry_count: number
  max_retries: number
  status: RetryStatus
}
