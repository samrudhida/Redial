import { api } from './api'
import type { DecisionLog } from '../types/decision'

export interface ListDecisionsParams {
  mandate_id?: string
  offset?: number
  limit?: number
}

/** GET /api/v1/decisions — see backend/app/api/routes/decisions.py::list_decisions. */
export async function fetchDecisions(params: ListDecisionsParams = {}): Promise<DecisionLog[]> {
  const { data } = await api.get<DecisionLog[]>('/decisions', { params })
  return data
}
