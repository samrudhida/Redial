import { api } from './api'
import type { Mandate } from '../types/mandate'
import type { MandateStatus } from '../types/enums'

export interface ListMandatesParams {
  status?: MandateStatus
  customer_id?: string
  offset?: number
  limit?: number
}

/** GET /api/v1/mandates — see backend/app/api/routes/mandates.py::list_mandates. */
export async function fetchMandates(params: ListMandatesParams = {}): Promise<Mandate[]> {
  const { data } = await api.get<Mandate[]>('/mandates', { params })
  return data
}

export interface CreateMandateRequest {
  customer_id: string
  mandate_reference: string
  /** Decimal, sent as a string (matches how the app treats Decimal fields everywhere). */
  amount: string
  /** Omitted entirely so the backend applies its own default ("INR"). */
  currency?: string
  bank_name?: string
  account_last4?: string
}

/** POST /api/v1/mandates — see backend/app/api/routes/mandates.py::create_mandate. */
export async function createMandate(payload: CreateMandateRequest): Promise<Mandate> {
  const { data } = await api.post<Mandate>('/mandates', payload)
  return data
}
