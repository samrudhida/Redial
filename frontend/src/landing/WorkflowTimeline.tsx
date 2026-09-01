import { motion } from 'framer-motion'
import { Bot, CheckCircle2, CreditCard, MessageSquareText, ShieldAlert, Timer } from 'lucide-react'

const STEPS = [
  { label: 'Payment Failure', icon: CreditCard, tone: 'danger' },
  { label: 'AI Analysis', icon: Bot, tone: 'info' },
  { label: 'Retry Strategy', icon: Timer, tone: 'amber' },
  { label: 'Communication', icon: MessageSquareText, tone: 'violet' },
  { label: 'Escalation', icon: ShieldAlert, tone: 'danger' },
  { label: 'Completed', icon: CheckCircle2, tone: 'success' },
] as const

/** One continuous, self-drawing path connecting every workflow stage — a diagram, not a card list. */
export function WorkflowTimeline() {
  return (
    <div className="workflow-timeline">
      <svg className="workflow-line" viewBox="0 0 100 4" preserveAspectRatio="none" aria-hidden="true">
        <motion.path
          d="M2,2 L98,2"
          initial={{ pathLength: 0 }}
          whileInView={{ pathLength: 1 }}
          viewport={{ once: true, margin: '-100px' }}
          transition={{ duration: 1.3, ease: 'easeInOut' }}
        />
      </svg>
      <div className="workflow-nodes">
        {STEPS.map((step, index) => (
          <motion.div
            className={`workflow-node tone-${step.tone}`}
            key={step.label}
            initial={{ opacity: 0, scale: 0.6 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true, margin: '-100px' }}
            transition={{ duration: 0.35, delay: 0.25 + index * 0.16 }}
          >
            <span className="workflow-node-dot"><step.icon size={16} /></span>
            <small>{step.label}</small>
          </motion.div>
        ))}
      </div>
    </div>
  )
}
