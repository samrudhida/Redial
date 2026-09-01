import { motion } from 'framer-motion'

export interface ReasoningLine {
  prompt?: string
  key?: string
  value: string
  tone?: 'default' | 'accent' | 'success' | 'muted'
}

const LINES: ReasoningLine[] = [
  { prompt: '>', value: 'payment_attempt.failed', tone: 'muted' },
  { key: 'failure_reason', value: 'insufficient_funds', tone: 'default' },
  { key: 'retry_count', value: '0', tone: 'default' },
  { prompt: '>', value: 'ai_service.generate_retry_decision()', tone: 'muted' },
  { key: 'confidence', value: '0.87', tone: 'accent' },
  { key: 'decision', value: 'retry_in_24h', tone: 'success' },
]

/** Self-playing terminal-style reasoning trace for the hero — a real shape of what AIService produces, not a generic illustration. */
export function ReasoningTerminal() {
  return (
    <motion.div
      className="terminal-panel hero-terminal"
      initial={{ opacity: 0, y: 20, rotate: 1.5 }}
      animate={{ opacity: 1, y: 0, rotate: 0 }}
      transition={{ duration: 0.7, delay: 0.2, ease: 'easeOut' }}
    >
      <div className="terminal-chrome">
        <span /><span /><span />
        <em>ai_service.py</em>
      </div>
      <div className="terminal-body">
        {LINES.map((line, index) => (
          <motion.div
            className={`terminal-line tone-${line.tone ?? 'default'}`}
            key={`${line.key ?? line.prompt}-${index}`}
            initial={{ opacity: 0, x: -6 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.6 + index * 0.22, duration: 0.35 }}
          >
            {line.prompt && <span className="terminal-prompt">{line.prompt}</span>}
            {line.key && <span className="terminal-key">{line.key}:</span>}
            <span className="terminal-value">{line.value}</span>
          </motion.div>
        ))}
        <motion.span
          className="terminal-cursor"
          initial={{ opacity: 0 }}
          animate={{ opacity: [0, 1, 0] }}
          transition={{ delay: 0.6 + LINES.length * 0.22, duration: 0.9, repeat: Infinity }}
        />
      </div>
    </motion.div>
  )
}
