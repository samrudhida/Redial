import { useQuery } from '@tanstack/react-query'
import { fetchDecisions, type ListDecisionsParams } from '../services/decisionApi'

export const decisionKeys = {
  list: (params: ListDecisionsParams) => ['decisions', 'list', params] as const,
}

export function useDecisions(params: ListDecisionsParams = {}) {
  return useQuery({
    queryKey: decisionKeys.list(params),
    queryFn: () => fetchDecisions(params),
    staleTime: 30_000,
    gcTime: 5 * 60_000,
    retry: 2,
  })
}
