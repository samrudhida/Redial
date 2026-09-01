import { useQuery } from '@tanstack/react-query'
import { fetchEscalations, type ListEscalationsParams } from '../services/escalationApi'

export const escalationKeys = {
  list: (params: ListEscalationsParams) => ['escalations', 'list', params] as const,
}

export function useEscalations(params: ListEscalationsParams = {}) {
  return useQuery({
    queryKey: escalationKeys.list(params),
    queryFn: () => fetchEscalations(params),
    staleTime: 30_000,
    gcTime: 5 * 60_000,
    retry: 2,
  })
}
