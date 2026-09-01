import { api } from './api'

export interface RunWorkflowsResult {
  attempted: number
  succeeded: number
  failed: number
}

/**
 * POST /api/v1/dev/workflows/run — development-only endpoint (see
 * backend/app/api/routes/dev_workflow.py). Runs the real recovery workflow
 * graph (context -> decision -> communication -> escalation -> persistence)
 * for existing mandates. Only mounted when the backend's APP_ENV is
 * "development"; returns 404 in any other environment.
 */
export async function runWorkflows(limit = 10): Promise<RunWorkflowsResult> {
  const { data } = await api.post<RunWorkflowsResult>('/dev/workflows/run', { limit })
  return data
}
