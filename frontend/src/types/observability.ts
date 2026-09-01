/** Mirrors backend/app/api/routes/observability.py response models exactly. */

export interface ObservabilityOverview {
  workflows_executed: number
  successful_workflows: number
  failed_workflows: number
  average_execution_time_ms: number
  average_ai_latency_ms: number
  average_confidence: number
  total_ai_calls: number
}

export interface WorkflowExecutionSummary {
  id: string
  workflow_id: string
  mandate_id: string
  started_at: string
  finished_at: string | null
  duration_ms: number | null
  status: string
  ai_provider: string | null
  ai_model: string | null
  /** Decimal in [0, 1], serialized as a string. */
  confidence: string | null
  retry_decision: string | null
  communication_decision: string | null
  escalation_decision: string | null
}

export interface WorkflowExecutionNode {
  node_name: string
  event: string
  started_at: string
  finished_at: string
  duration_ms: number
  success: boolean
  details: Record<string, unknown>
}

export interface WorkflowExecutionDetail {
  execution: WorkflowExecutionSummary
  reasoning: string | null
  error_message: string | null
  failed_node: string | null
  nodes: WorkflowExecutionNode[]
}

export interface ProviderHealth {
  provider: string
  model: string | null
  status: string
  requests_today: number
  failures: number
  average_latency_ms: number
  average_confidence: number
}

export interface WorkflowError {
  workflow_id: string
  mandate_id: string
  node: string | null
  exception: string
  timestamp: string
}

export interface ObservabilityMetrics {
  average_workflow_duration_ms: number
  average_node_duration_ms: number
  decision_latency_ms: number
  communication_latency_ms: number
  escalation_latency_ms: number
  ai_latency_ms: number
  database_persistence_latency_ms: number
}
