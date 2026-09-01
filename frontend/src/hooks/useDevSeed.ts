import { useMutation, useQueryClient } from '@tanstack/react-query'
import { deleteDemoData, seedDemoData } from '../services/devSeedApi'

/**
 * Seeding/deleting demo data can change every entity in the app at once
 * (mandates, payments, retry schedules, decisions, communications,
 * escalations, and the dashboard summary that aggregates them), so both
 * mutations invalidate the entire query cache rather than an incomplete
 * hand-picked list of keys.
 */
export function useSeedDemoData() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (count: number) => seedDemoData(count),
    onSuccess: () => {
      void queryClient.invalidateQueries()
    },
  })
}

export function useDeleteDemoData() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: deleteDemoData,
    onSuccess: () => {
      void queryClient.invalidateQueries()
    },
  })
}
