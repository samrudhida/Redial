import { api } from './api'
import type { RetrySchedule } from '../types/retrySchedule'

export interface ListRetrySchedulesParams {
  offset?: number
  limit?: number
}

/**
 * GET /api/v1/retry-schedules — see
 * backend/app/api/routes/retry_schedules.py::list_pending_retries.
 * Always returns only pending/scheduled retries; there is no status filter
 * and no way to list executed/cancelled/exhausted schedules through this
 * endpoint.
 */
export async function fetchRetrySchedules(params: ListRetrySchedulesParams = {}): Promise<RetrySchedule[]> {
  const { data } = await api.get<RetrySchedule[]>('/retry-schedules', { params })
  return data
}
