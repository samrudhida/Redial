import { useQuery } from '@tanstack/react-query'
import { fetchPayments, type ListPaymentsParams } from '../services/paymentApi'

export const paymentKeys = {
  list: (params: ListPaymentsParams) => ['payments', 'list', params] as const,
}

/**
 * The backend requires `mandate_id` on GET /payments (no mandate-less
 * listing exists), so the query stays disabled until one is provided.
 */
export function usePayments(params: ListPaymentsParams | null) {
  return useQuery({
    queryKey: paymentKeys.list(params ?? { mandate_id: '' }),
    queryFn: () => fetchPayments(params as ListPaymentsParams),
    enabled: Boolean(params?.mandate_id),
    staleTime: 30_000,
    gcTime: 5 * 60_000,
    retry: 2,
  })
}
