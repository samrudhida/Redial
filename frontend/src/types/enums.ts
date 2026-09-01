/**
 * String-literal unions mirroring backend/app/models/enums.py exactly.
 * Single source of truth — every entity type imports from here instead of
 * redefining these unions.
 */

export type MandateStatus = 'active' | 'paused' | 'cancelled' | 'expired' | 'completed'

export type PaymentStatus = 'pending' | 'processing' | 'succeeded' | 'failed' | 'retry_scheduled'

export type RetryStatus = 'pending' | 'scheduled' | 'executed' | 'skipped' | 'cancelled' | 'exhausted'

export type DeclineCategory =
  | 'insufficient_funds'
  | 'bank_unavailable'
  | 'authentication_required'
  | 'mandate_inactive'
  | 'limit_exceeded'
  | 'account_closed'
  | 'technical_error'
  | 'unknown'

export type CommunicationChannel = 'email' | 'sms' | 'whatsapp' | 'push'

export type DeliveryStatus = 'pending' | 'sent' | 'delivered' | 'failed'

export type EscalationLevel = 'level_1' | 'level_2' | 'level_3' | 'critical'
