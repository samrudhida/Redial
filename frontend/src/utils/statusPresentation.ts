import { Bell, Mail, MessageCircle, MessageSquare, type LucideIcon } from 'lucide-react'
import type { BadgeTone } from '../ui/StatusBadge'
import type {
  CommunicationChannel,
  DeclineCategory,
  DeliveryStatus,
  EscalationLevel,
  MandateStatus,
  PaymentStatus,
  RetryStatus,
} from '../types/enums'

function titleCase(value: string): string {
  return value.replace(/_/g, ' ').replace(/\b\w/g, char => char.toUpperCase())
}

export function mandateStatusPresentation(status: MandateStatus): { label: string; tone: BadgeTone } {
  const tone: Record<MandateStatus, BadgeTone> = {
    active: 'success',
    paused: 'warning',
    cancelled: 'neutral',
    expired: 'neutral',
    completed: 'info',
  }
  return { label: titleCase(status), tone: tone[status] }
}

export function paymentStatusPresentation(status: PaymentStatus): { label: string; tone: BadgeTone } {
  const tone: Record<PaymentStatus, BadgeTone> = {
    pending: 'neutral',
    processing: 'info',
    succeeded: 'success',
    failed: 'danger',
    retry_scheduled: 'warning',
  }
  return { label: titleCase(status), tone: tone[status] }
}

export function retryStatusPresentation(status: RetryStatus): { label: string; tone: BadgeTone } {
  const tone: Record<RetryStatus, BadgeTone> = {
    pending: 'neutral',
    scheduled: 'warning',
    executed: 'success',
    skipped: 'neutral',
    cancelled: 'neutral',
    exhausted: 'danger',
  }
  return { label: titleCase(status), tone: tone[status] }
}

export function deliveryStatusPresentation(status: DeliveryStatus): { label: string; tone: BadgeTone } {
  const tone: Record<DeliveryStatus, BadgeTone> = {
    pending: 'neutral',
    sent: 'info',
    delivered: 'success',
    failed: 'danger',
  }
  return { label: titleCase(status), tone: tone[status] }
}

export function escalationLevelPresentation(level: EscalationLevel): { label: string; tone: BadgeTone } {
  const tone: Record<EscalationLevel, BadgeTone> = {
    level_1: 'neutral',
    level_2: 'warning',
    level_3: 'warning',
    critical: 'danger',
  }
  return { label: titleCase(level), tone: tone[level] }
}

export function communicationChannelLabel(channel: CommunicationChannel): string {
  return titleCase(channel)
}

const CHANNEL_ICONS: Record<CommunicationChannel, LucideIcon> = {
  email: Mail,
  sms: MessageSquare,
  whatsapp: MessageCircle,
  push: Bell,
}

export function communicationChannelIcon(channel: CommunicationChannel): LucideIcon {
  return CHANNEL_ICONS[channel]
}

export function declineCategoryLabel(category: DeclineCategory): string {
  return titleCase(category)
}

/** Workflow execution status is a free-form string set by WorkflowMetadata, not a fixed backend enum. */
export function workflowExecutionStatusPresentation(status: string): { label: string; tone: BadgeTone } {
  if (status === 'completed') return { label: 'Completed', tone: 'success' }
  if (status === 'failed') return { label: 'Failed', tone: 'danger' }
  return { label: titleCase(status), tone: 'neutral' }
}

/** Provider health status, set by WorkflowExecutionService.get_provider_health. */
export function providerStatusPresentation(status: string): { label: string; tone: BadgeTone } {
  if (status === 'healthy') return { label: 'Healthy', tone: 'success' }
  if (status === 'degraded') return { label: 'Degraded', tone: 'warning' }
  if (status === 'not_configured') return { label: 'Not Configured', tone: 'neutral' }
  return { label: titleCase(status), tone: 'neutral' }
}

/** 95–100 green, 80–94 blue, 60–79 yellow, below 60 red. */
export function confidenceTone(score: string): BadgeTone {
  const value = Number.parseFloat(score) * 100
  if (!Number.isFinite(value)) return 'neutral'
  if (value >= 95) return 'success'
  if (value >= 80) return 'info'
  if (value >= 60) return 'warning'
  return 'danger'
}

/**
 * decision_type is a free-form string (no backend enum) — the three values
 * actually ever recorded by this app are retry_schedule,
 * decline_classification, and escalation_recommendation (see every call
 * site of DecisionService.record_ai_decision). Anything else falls back to
 * a neutral badge with the raw value title-cased, rather than assuming a
 * fixed set.
 */
export function decisionTypePresentation(type: string): { label: string; tone: BadgeTone } {
  if (type === 'retry_schedule') return { label: 'Retry', tone: 'info' }
  if (type === 'decline_classification') return { label: 'Decline Classification', tone: 'warning' }
  if (type === 'escalation_recommendation') return { label: 'Escalate', tone: 'danger' }
  return { label: titleCase(type), tone: 'neutral' }
}
