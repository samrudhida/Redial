import { api } from './api'
import type { ActivityEvent, DailyTrendPoint, DashboardSummary } from '../types/dashboard'

/**
 * GET /api/v1/dashboard/summary
 * See backend/app/api/routes/dashboard.py::get_dashboard_summary.
 */
export async function fetchDashboardSummary(recentDecisionLimit = 10): Promise<DashboardSummary> {
  const { data } = await api.get<DashboardSummary>('/dashboard/summary', {
    params: { recent_decision_limit: recentDecisionLimit },
  })
  return data
}

/**
 * GET /api/v1/dashboard/trend
 * See backend/app/api/routes/dashboard.py::get_dashboard_trend.
 */
export async function fetchDashboardTrend(days = 14): Promise<DailyTrendPoint[]> {
  const { data } = await api.get<DailyTrendPoint[]>('/dashboard/trend', { params: { days } })
  return data
}

/**
 * GET /api/v1/dashboard/activity
 * See backend/app/api/routes/dashboard.py::get_dashboard_activity.
 */
export async function fetchDashboardActivity(limit = 20): Promise<ActivityEvent[]> {
  const { data } = await api.get<ActivityEvent[]>('/dashboard/activity', { params: { limit } })
  return data
}
