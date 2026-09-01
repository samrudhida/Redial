import type { DeclineCategory, PaymentStatus } from './enums'

/** Mirrors PaymentAttemptResponse in backend/app/api/routes/payments.py. */
export interface PaymentAttempt {
  id: string
  mandate_id: string
  attempt_number: number
  attempted_at: string
  /** Decimal, serialized as a string (e.g. "500.00"). */
  amount: string
  status: PaymentStatus
  bank_response_code: string | null
  bank_response_message: string | null
  decline_category: DeclineCategory | null
  ai_reasoning: string | null
  next_retry_at: string | null
  /** Set once a real Razorpay Test/Live Mode order exists for this attempt — null in demo mode. */
  razorpay_order_id: string | null
  /** Set once Razorpay reports a real payment against the order (via webhook) — null until then. */
  razorpay_payment_id: string | null
}
