import { useQuery } from '@tanstack/react-query'
import { fetchDashboardActivity, fetchDashboardSummary, fetchDashboardTrend } from '../services/dashboardApi'

export const dashboardKeys = {
  /** Prefix matching every summary query regardless of recentDecisionLimit — use for invalidation. */
  summaryAll: ['dashboard', 'summary'] as const,
  summary: (recentDecisionLimit: number) => ['dashboard', 'summary', recentDecisionLimit] as const,
  trend: (days: number) => ['dashboard', 'trend', days] as const,
  activity: (limit: number) => ['dashboard', 'activity', limit] as const,
}

/**
 * Fetches the dashboard aggregate summary (GET /dashboard/summary).
 *
 * staleTime is short since the summary reflects live retry/payment activity,
 * but non-zero so rapid re-renders (e.g. tab refocus) don't refire the
 * request. gcTime keeps the last result cached briefly after the dashboard
 * unmounts, so navigating away and back doesn't show a cold loading state.
 *
 * refetchInterval is intentionally NOT set here — it inherits the QueryClient's
 * app-wide default (see App.tsx/QueryDefaultsSync), which is user-controlled
 * via Settings > Live data refresh. Passing `refetchInterval: undefined`
 * explicitly here would override that default with "polling off" instead of
 * falling through to it, since React Query's options merge treats an
 * explicitly-present `undefined` key as an override, not an absence.
 */
export function useDashboardSummary(recentDecisionLimit = 10) {
  return useQuery({
    queryKey: dashboardKeys.summary(recentDecisionLimit),
    queryFn: () => fetchDashboardSummary(recentDecisionLimit),
    staleTime: 30_000,
    gcTime: 5 * 60_000,
    retry: 2,
  })
}

/**
 * Fetches the real per-day payment trend (GET /dashboard/trend) that backs the
 * dashboard's charts. Inherits the app-wide refetchInterval default — see
 * useDashboardSummary's docstring for why it isn't passed explicitly here.
 */
export function useDashboardTrend(days = 14) {
  return useQuery({
    queryKey: dashboardKeys.trend(days),
    queryFn: () => fetchDashboardTrend(days),
    staleTime: 60_000,
    gcTime: 5 * 60_000,
    retry: 2,
  })
}

/** Fetches the real recent-activity feed (GET /dashboard/activity) — decisions and communications, newest first. */
export function useDashboardActivity(limit = 20) {
  return useQuery({
    queryKey: dashboardKeys.activity(limit),
    queryFn: () => fetchDashboardActivity(limit),
    staleTime: 30_000,
    gcTime: 5 * 60_000,
    retry: 2,
  })
}
