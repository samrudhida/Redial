import { useMutation, useQueryClient } from '@tanstack/react-query'
import { recordPaymentAttempt } from '../services/paymentApi'
import { dashboardKeys } from './useDashboard'

/**
 * POST /api/v1/payments. On success, invalidates the payments list for the
 * mandate and the dashboard summary — the same invalidation shape as
 * useCreateMandate, since this can also change what the dashboard shows.
 */
export function useRecordPaymentAttempt() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: recordPaymentAttempt,
    onSuccess: attempt => {
      queryClient.invalidateQueries({ queryKey: ['payments', 'list'] })
      queryClient.invalidateQueries({ queryKey: dashboardKeys.summaryAll })
      return attempt
    },
  })
}
