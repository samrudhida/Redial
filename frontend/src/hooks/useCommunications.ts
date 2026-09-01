import { useQuery } from '@tanstack/react-query'
import { fetchCommunications, type ListCommunicationsParams } from '../services/communicationApi'

export const communicationKeys = {
  list: (params: ListCommunicationsParams) => ['communications', 'list', params] as const,
}

export function useCommunications(params: ListCommunicationsParams = {}) {
  return useQuery({
    queryKey: communicationKeys.list(params),
    queryFn: () => fetchCommunications(params),
    staleTime: 30_000,
    gcTime: 5 * 60_000,
    retry: 2,
  })
}
