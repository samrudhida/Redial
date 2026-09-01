import type { CommunicationChannel, DeliveryStatus } from './enums'

/** Mirrors CommunicationResponse in backend/app/api/routes/communications.py. */
export interface Communication {
  id: string
  mandate_id: string
  channel: CommunicationChannel
  template_name: string | null
  message: string
  sent_at: string
  delivery_status: DeliveryStatus
}
