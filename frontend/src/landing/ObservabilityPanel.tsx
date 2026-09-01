import { motion } from 'framer-motion'

const TRACE_FIELDS = [
  { label: 'provider', value: 'groq' },
  { label: 'model', value: 'openai/gpt-oss-20b' },
  { label: 'latency_ms', value: '874.9' },
  { label: 'confidence', value: '0.87' },
  { label: 'success', value: 'true' },
] as const

/** A live-monitoring-styled readout of a real AITrace shape — not a generic metrics grid. */
export function ObservabilityPanel() {
  return (
    <motion.div
      className="terminal-panel"
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-80px' }}
      transition={{ duration: 0.5 }}
    >
      <div className="terminal-chrome">
        <span className="live-dot" />
        <em>ai_trace · live</em>
      </div>
      <div className="terminal-body observability-fields">
        {TRACE_FIELDS.map((field, index) => (
          <motion.div
            className="terminal-line"
            key={field.label}
            initial={{ opacity: 0, x: -6 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true, margin: '-80px' }}
            transition={{ delay: index * 0.12, duration: 0.35 }}
          >
            <span className="terminal-key">{field.label}</span>
            <span className="terminal-value">{field.value}</span>
          </motion.div>
        ))}
      </div>
    </motion.div>
  )
}
