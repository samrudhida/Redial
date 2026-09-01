import { useQuery } from '@tanstack/react-query'
import { fetchHealth } from '../services/healthApi'

/** Whether Razorpay is configured server-side, and its public key_id if so. Long staleTime — this rarely changes at runtime. */
export function useRazorpayConfig() {
  return useQuery({
    queryKey: ['health'],
    queryFn: fetchHealth,
    staleTime: 5 * 60_000,
    gcTime: 10 * 60_000,
    retry: 1,
  })
}
