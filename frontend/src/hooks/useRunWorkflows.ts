import { useMutation, useQueryClient } from '@tanstack/react-query'
import { runWorkflows } from '../services/workflowRunnerApi'

/**
 * Running the workflow can change mandates, retry schedules, AI decisions,
 * communications, escalations, workflow executions, and the dashboard
 * summary that aggregates all of them — so invalidate everything rather
 * than an incomplete hand-picked list of keys, matching useSeedDemoData.
 */
export function useRunWorkflows() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (limit: number) => runWorkflows(limit),
    onSuccess: () => {
      void queryClient.invalidateQueries()
    },
  })
}
