import { motion } from 'framer-motion'
import { Check, X } from 'lucide-react'

const ROWS = [
  { traditional: 'Retries on a fixed timer, blind to why the payment failed', redial: 'AI reasons over the failure reason before deciding whether to retry at all' },
  { traditional: 'Failures and retries live in disconnected logs', redial: 'Every decision, confidence score, and provider trace is persisted together' },
  { traditional: 'One provider outage stops the whole system', redial: 'AI is optional enrichment — deterministic policy always completes the workflow' },
  { traditional: 'Escalations depend on someone noticing', redial: 'Cases are routed to a human automatically, with the reasoning attached' },
] as const

/** A direct comparison argues the point sharper than a differentiators grid. */
export function ComparisonTable() {
  return (
    <div className="comparison-table">
      <div className="comparison-head">
        <span>Traditional retry systems</span>
        <span className="comparison-head-redial">REDIAL</span>
      </div>
      {ROWS.map((row, index) => (
        <motion.div
          className="comparison-row"
          key={row.traditional}
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-60px' }}
          transition={{ duration: 0.4, delay: index * 0.08 }}
        >
          <div className="comparison-cell comparison-cell-no"><X size={15} /><span>{row.traditional}</span></div>
          <div className="comparison-cell comparison-cell-yes"><Check size={15} /><span>{row.redial}</span></div>
        </motion.div>
      ))}
    </div>
  )
}
