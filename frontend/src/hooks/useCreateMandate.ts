import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createMandate } from '../services/mandateApi'
import { dashboardKeys } from './useDashboard'
import { mandateKeys } from './useMandates'

/**
 * POST /api/v1/mandates. On success, invalidates the mandates list and the
 * dashboard summary so both the Mandates page and Dashboard reflect the new
 * mandate without a manual refresh.
 */
export function useCreateMandate() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: createMandate,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: mandateKeys.all })
      queryClient.invalidateQueries({ queryKey: dashboardKeys.summaryAll })
    },
  })
}
