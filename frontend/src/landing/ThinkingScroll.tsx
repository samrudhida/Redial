import { motion, useScroll, useTransform } from 'framer-motion'
import { useRef } from 'react'
import { Bot, CheckCircle2, FileJson2 } from 'lucide-react'

const STAGES = [
  {
    title: 'Structured prompting',
    body: 'Payment history, failure reason, retry count, and customer context are assembled into a schema-constrained prompt — never a freeform question.',
  },
  {
    title: 'The model reasons',
    body: 'A Groq-backed model reasons over that context and returns a raw response. Every call is traced — provider, model, and latency recorded before anything else happens.',
  },
  {
    title: 'Validated, not trusted blindly',
    body: 'The response is parsed against a strict schema. Confidence is clamped between 0 and 1. Malformed output never reaches a decision — it falls back to deterministic policy instead.',
  },
] as const

/**
 * inactiveOpacity defaults to a dim-not-hidden 0.25 for the stepper text
 * (normal document flow, fine to keep faintly visible). The stacked terminal
 * panels on the right (position: absolute; inset: 0, all three sharing the
 * same box) need a hard 0 instead — anything short of that leaves the
 * inactive panels' text still painted underneath the active one.
 */
function useStageOpacity(progress: ReturnType<typeof useScroll>['scrollYProgress'], index: number, inactiveOpacity = 0.25) {
  const step = 1 / STAGES.length
  const start = index * step
  const end = start + step
  const pad = step * 0.18
  return useTransform(progress, [Math.max(0, start - pad), start + pad, end - pad, Math.min(1, end + pad)], [inactiveOpacity, 1, 1, inactiveOpacity])
}

/** The signature interaction: reasoning stages advance as the section is pinned and scrolled through. */
export function ThinkingScroll() {
  const containerRef = useRef<HTMLDivElement>(null)
  const { scrollYProgress } = useScroll({ target: containerRef, offset: ['start start', 'end end'] })

  const opacities = [
    useStageOpacity(scrollYProgress, 0),
    useStageOpacity(scrollYProgress, 1),
    useStageOpacity(scrollYProgress, 2),
  ]
  // Stacked panels (position: absolute; inset: 0) must fully hide when inactive,
  // unlike the stepper text above — see useStageOpacity's doc comment.
  const panelOpacities = [
    useStageOpacity(scrollYProgress, 0, 0),
    useStageOpacity(scrollYProgress, 1, 0),
    useStageOpacity(scrollYProgress, 2, 0),
  ]

  return (
    <div className="thinking-section" ref={containerRef}>
      <div className="thinking-sticky">
        <div className="thinking-copy">
          <p className="landing-kicker">How REDIAL thinks</p>
          <h2>Reasoning you can inspect, not a black box</h2>
          {STAGES.map((stage, index) => (
            <motion.div className="thinking-stage" key={stage.title} style={{ opacity: opacities[index] }}>
              <span className="thinking-stage-index">0{index + 1}</span>
              <div>
                <strong>{stage.title}</strong>
                <p>{stage.body}</p>
              </div>
            </motion.div>
          ))}
        </div>

        <div className="thinking-visual">
          <motion.div className="terminal-panel thinking-panel-layer" style={{ opacity: panelOpacities[0] }}>
            <div className="terminal-chrome"><span /><span /><span /><em>prompt_builder.py</em></div>
            <div className="terminal-body">
              <div className="terminal-line tone-muted"><span className="terminal-prompt">{'{'}</span></div>
              <div className="terminal-line"><span className="terminal-key">  payment_history</span><span className="terminal-value">[...]</span></div>
              <div className="terminal-line"><span className="terminal-key">  failure_reason</span><span className="terminal-value">"insufficient_funds"</span></div>
              <div className="terminal-line"><span className="terminal-key">  retry_count</span><span className="terminal-value">0</span></div>
              <div className="terminal-line"><span className="terminal-key">  customer_profile</span><span className="terminal-value">{'{...}'}</span></div>
              <div className="terminal-line tone-muted"><span className="terminal-prompt">{'}'}</span></div>
            </div>
          </motion.div>

          <motion.div className="terminal-panel thinking-panel-layer" style={{ opacity: panelOpacities[1] }}>
            <div className="terminal-chrome"><span /><span /><span /><em>groq_provider.py</em></div>
            <div className="terminal-body thinking-model-body">
              <Bot size={22} className="thinking-model-icon" />
              <div className="terminal-line tone-accent">client.chat.completions.create(...)</div>
              <div className="terminal-line tone-muted">model: openai/gpt-oss-20b</div>
              <div className="thinking-pulse"><span /><span /><span /></div>
            </div>
          </motion.div>

          <motion.div className="terminal-panel thinking-panel-layer" style={{ opacity: panelOpacities[2] }}>
            <div className="terminal-chrome"><span /><span /><span /><em>response_validator.py</em></div>
            <div className="terminal-body">
              <div className="terminal-line tone-muted"><FileJson2 size={13} /> RetryDecision</div>
              <div className="terminal-line"><span className="terminal-key">  confidence</span><span className="terminal-value">0.87</span></div>
              <div className="terminal-line"><span className="terminal-key">  decision</span><span className="terminal-value">"retry_in_24h"</span></div>
              <div className="terminal-line tone-success"><CheckCircle2 size={13} /> schema validated</div>
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  )
}
