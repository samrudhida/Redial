import { motion } from 'framer-motion'

const REASONS = [
  { label: 'insufficient_funds', drift: -10 },
  { label: 'card_expired', drift: 8 },
  { label: 'issuer_timeout', drift: -14 },
  { label: 'bank_decline', drift: 6 },
  { label: 'invalid_cvv', drift: -6 },
  { label: 'do_not_honor', drift: 12 },
  { label: 'processing_error', drift: -8 },
] as const

/** Drifting failure-reason tags — visual chaos that the next section resolves into one system. */
export function FailureChips() {
  return (
    <div className="failure-chips" aria-hidden="true">
      {REASONS.map((reason, index) => (
        <motion.span
          className="failure-chip"
          key={reason.label}
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: [16, 0, reason.drift, 0] }}
          viewport={{ once: true, margin: '-60px' }}
          transition={{
            opacity: { duration: 0.5, delay: index * 0.06 },
            y: { duration: 6 + index * 0.4, delay: index * 0.06, repeat: Infinity, repeatType: 'mirror', ease: 'easeInOut' },
          }}
        >
          {reason.label}
        </motion.span>
      ))}
    </div>
  )
}
