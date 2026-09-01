import { useQuery } from '@tanstack/react-query'
import {
  fetchObservabilityMetrics,
  fetchObservabilityOverview,
  fetchProviderHealth,
  fetchWorkflowErrors,
  fetchWorkflowExecutionDetail,
  fetchWorkflowExecutions,
  type ListWorkflowsParams,
} from '../services/observabilityApi'

const STALE_TIME_MS = 30_000
const GC_TIME_MS = 5 * 60_000

export const observabilityKeys = {
  overview: ['observability', 'overview'] as const,
  workflows: (params: ListWorkflowsParams) => ['observability', 'workflows', 'list', params] as const,
  workflowDetail: (id: string) => ['observability', 'workflows', 'detail', id] as const,
  provider: ['observability', 'provider'] as const,
  errors: (params: ListWorkflowsParams) => ['observability', 'errors', params] as const,
  metrics: ['observability', 'metrics'] as const,
}

export function useObservabilityOverview() {
  return useQuery({
    queryKey: observabilityKeys.overview,
    queryFn: fetchObservabilityOverview,
    staleTime: STALE_TIME_MS,
    gcTime: GC_TIME_MS,
    retry: 2,
  })
}

export function useWorkflowExecutions(params: ListWorkflowsParams = {}) {
  return useQuery({
    queryKey: observabilityKeys.workflows(params),
    queryFn: () => fetchWorkflowExecutions(params),
    staleTime: STALE_TIME_MS,
    gcTime: GC_TIME_MS,
    retry: 2,
  })
}

export function useWorkflowExecutionDetail(executionId: string | null) {
  return useQuery({
    queryKey: observabilityKeys.workflowDetail(executionId ?? ''),
    queryFn: () => fetchWorkflowExecutionDetail(executionId as string),
    enabled: executionId !== null,
    staleTime: STALE_TIME_MS,
    gcTime: GC_TIME_MS,
    retry: 2,
  })
}

export function useProviderHealth() {
  return useQuery({
    queryKey: observabilityKeys.provider,
    queryFn: fetchProviderHealth,
    staleTime: STALE_TIME_MS,
    gcTime: GC_TIME_MS,
    retry: 2,
  })
}

export function useWorkflowErrors(params: ListWorkflowsParams = {}) {
  return useQuery({
    queryKey: observabilityKeys.errors(params),
    queryFn: () => fetchWorkflowErrors(params),
    staleTime: STALE_TIME_MS,
    gcTime: GC_TIME_MS,
    retry: 2,
  })
}

export function useObservabilityMetrics() {
  return useQuery({
    queryKey: observabilityKeys.metrics,
    queryFn: fetchObservabilityMetrics,
    staleTime: STALE_TIME_MS,
    gcTime: GC_TIME_MS,
    retry: 2,
  })
}
