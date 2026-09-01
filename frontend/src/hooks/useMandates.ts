import { useQuery } from '@tanstack/react-query'
import { fetchMandates, type ListMandatesParams } from '../services/mandateApi'

export const mandateKeys = {
  all: ['mandates'] as const,
  list: (params: ListMandatesParams) => ['mandates', 'list', params] as const,
}

export function useMandates(params: ListMandatesParams) {
  return useQuery({
    queryKey: mandateKeys.list(params),
    queryFn: () => fetchMandates(params),
    staleTime: 30_000,
    gcTime: 5 * 60_000,
    retry: 2,
  })
}
