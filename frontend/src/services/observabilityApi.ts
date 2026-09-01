import { api } from './api'
import type {
  ObservabilityMetrics,
  ObservabilityOverview,
  ProviderHealth,
  WorkflowError,
  WorkflowExecutionDetail,
  WorkflowExecutionSummary,
} from '../types/observability'

export interface ListWorkflowsParams {
  offset?: number
  limit?: number
}

/** GET /api/v1/observability/overview */
export async function fetchObservabilityOverview(): Promise<ObservabilityOverview> {
  const { data } = await api.get<ObservabilityOverview>('/observability/overview')
  return data
}

/** GET /api/v1/observability/workflows */
export async function fetchWorkflowExecutions(params: ListWorkflowsParams = {}): Promise<WorkflowExecutionSummary[]> {
  const { data } = await api.get<WorkflowExecutionSummary[]>('/observability/workflows', { params })
  return data
}

/** GET /api/v1/observability/workflows/{id} */
export async function fetchWorkflowExecutionDetail(executionId: string): Promise<WorkflowExecutionDetail> {
  const { data } = await api.get<WorkflowExecutionDetail>(`/observability/workflows/${executionId}`)
  return data
}

/** GET /api/v1/observability/provider */
export async function fetchProviderHealth(): Promise<ProviderHealth[]> {
  const { data } = await api.get<ProviderHealth[]>('/observability/provider')
  return data
}

/** GET /api/v1/observability/errors */
export async function fetchWorkflowErrors(params: ListWorkflowsParams = {}): Promise<WorkflowError[]> {
  const { data } = await api.get<WorkflowError[]>('/observability/errors', { params })
  return data
}

/** GET /api/v1/observability/metrics */
export async function fetchObservabilityMetrics(): Promise<ObservabilityMetrics> {
  const { data } = await api.get<ObservabilityMetrics>('/observability/metrics')
  return data
}
