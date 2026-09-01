import { api } from './api'
import type { PaymentAttempt } from '../types/payment'
import type { PaymentStatus } from '../types/enums'

export interface ListPaymentsParams {
  /** Required by the backend — GET /payments has no mandate-less listing. */
  mandate_id: string
  status?: PaymentStatus
  offset?: number
  limit?: number
}

/** GET /api/v1/payments — see backend/app/api/routes/payments.py::list_payment_attempts. */
export async function fetchPayments(params: ListPaymentsParams): Promise<PaymentAttempt[]> {
  const { data } = await api.get<PaymentAttempt[]>('/payments', { params })
  return data
}

export interface RecordPaymentAttemptRequest {
  mandate_id: string
  amount?: string
}

/**
 * POST /api/v1/payments — see backend/app/api/routes/payments.py::record_payment_attempt.
 * When Razorpay is configured, the backend also creates a real order and
 * returns its id on the response (razorpay_order_id).
 */
export async function recordPaymentAttempt(request: RecordPaymentAttemptRequest): Promise<PaymentAttempt> {
  const { data } = await api.post<PaymentAttempt>('/payments', request)
  return data
}
