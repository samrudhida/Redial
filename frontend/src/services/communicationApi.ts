import { api } from './api'
import type { Communication } from '../types/communication'
import type { CommunicationChannel } from '../types/enums'

export interface ListCommunicationsParams {
  mandate_id?: string
  channel?: CommunicationChannel
  offset?: number
  limit?: number
}

/** GET /api/v1/communications — see backend/app/api/routes/communications.py::list_communications. */
export async function fetchCommunications(params: ListCommunicationsParams = {}): Promise<Communication[]> {
  const { data } = await api.get<Communication[]>('/communications', { params })
  return data
}
