import { api } from './api'
import type { Escalation } from '../types/escalation'

export interface ListEscalationsParams {
  mandate_id?: string
  /** Defaults to false server-side (open escalations) if omitted. */
  resolved?: boolean
  offset?: number
  limit?: number
}

/** GET /api/v1/escalations — see backend/app/api/routes/escalations.py::list_escalations. */
export async function fetchEscalations(params: ListEscalationsParams = {}): Promise<Escalation[]> {
  const { data } = await api.get<Escalation[]>('/escalations', { params })
  return data
}
