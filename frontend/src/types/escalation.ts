import type { EscalationLevel } from './enums'

/**
 * Mirrors EscalationResponse in backend/app/api/routes/escalations.py.
 * Note: the backend has no `created_at` for escalations — only
 * `resolved_at`, which is null until the escalation is resolved. Do not
 * invent a creation timestamp.
 */
export interface Escalation {
  id: string
  mandate_id: string
  escalation_level: EscalationLevel
  reason: string
  assigned_to: string | null
  resolved: boolean
  resolved_at: string | null
}
