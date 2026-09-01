import { useQuery } from '@tanstack/react-query'
import { fetchRetrySchedules, type ListRetrySchedulesParams } from '../services/retryScheduleApi'

export const retryScheduleKeys = {
  list: (params: ListRetrySchedulesParams) => ['retry-schedules', 'list', params] as const,
}

export function useRetrySchedules(params: ListRetrySchedulesParams = {}) {
  return useQuery({
    queryKey: retryScheduleKeys.list(params),
    queryFn: () => fetchRetrySchedules(params),
    staleTime: 30_000,
    gcTime: 5 * 60_000,
    retry: 2,
  })
}
