import type { MandateStatus } from './enums'

/** Mirrors MandateResponse in backend/app/api/routes/mandates.py. */
export interface Mandate {
  id: string
  customer_id: string
  mandate_reference: string
  /** Decimal, serialized as a string (e.g. "500.00"). */
  amount: string
  currency: string
  bank_name: string | null
  account_last4: string | null
  status: MandateStatus
  created_at: string
  updated_at: string
}
