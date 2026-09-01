import { motion } from 'framer-motion'
import { ArrowRight } from 'lucide-react'
import { Link } from 'react-router-dom'
import { ComparisonTable } from '../landing/ComparisonTable'
import { DashboardPreview } from '../landing/DashboardPreview'
import { FailureChips } from '../landing/FailureChips'
import { LandingFooter } from '../landing/LandingFooter'
import { LandingNav } from '../landing/LandingNav'
import { ObservabilityPanel } from '../landing/ObservabilityPanel'
import { ReasoningTerminal } from '../landing/ReasoningTerminal'
import { ThinkingScroll } from '../landing/ThinkingScroll'
import { WorkflowTimeline } from '../landing/WorkflowTimeline'

export function LandingPage() {
  return (
    <div className="landing-page" id="top">
      <div className="landing-mesh" aria-hidden="true" />
      <LandingNav />

      {/* 1 — Hero: the product's real differentiator, shown live, not described */}
      <section className="hero">
        <div className="hero-copy">
          <motion.p className="landing-eyebrow" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
            AI-native payment recovery
          </motion.p>
          <motion.h1 initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 0.08 }}>
            Every failed payment<br />has a reason.
            <span className="hero-accent-line">REDIAL finds it — and acts.</span>
          </motion.h1>
          <motion.p className="hero-subtitle" initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 0.14 }}>
            An AI reasoning layer sits inside your payment recovery workflow — deciding, communicating, and escalating,
            with full transparency on every call it makes.
          </motion.p>
          <motion.div className="hero-actions" initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 0.2 }}>
            <Link to="/dashboard" className="primary-button hero-cta">Launch Dashboard <ArrowRight size={16} /></Link>
            <a href="#thinking" className="hero-learn-more">Learn More</a>
          </motion.div>
        </div>
        <ReasoningTerminal />
      </section>

      {/* 2 — Problem framing: chaos, not a capability list */}
      <section className="landing-block failure-block">
        <motion.h2 initial={{ opacity: 0, y: 16 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, margin: '-80px' }} transition={{ duration: 0.5 }}>
          Payments don&apos;t just &quot;fail.&quot; They fail for a reason —<br />
          and most systems never ask what it was.
        </motion.h2>
        <FailureChips />
      </section>

      {/* 3 — The signature interaction: reasoning stages, pinned to scroll */}
      <div id="thinking">
        <ThinkingScroll />
      </div>

      {/* 4 — The workflow, as one continuous diagram */}
      <section className="landing-block" id="workflow">
        <p className="landing-kicker">End to end</p>
        <h2>One traceable workflow, every time</h2>
        <p className="landing-lede">Every mandate that fails a payment moves through the same six-stage graph — visible, ordered, and logged.</p>
        <WorkflowTimeline />
      </section>

      {/* 5 — Observability, shown as a live trace, not a metrics grid */}
      <section className="landing-block observability-block">
        <div className="observability-copy">
          <p className="landing-kicker">Transparency</p>
          <h2>Nothing happens off the record</h2>
          <p className="landing-lede">
            Every AI call — provider, model, latency, and confidence — is traced and persisted alongside the decision
            it produced. If a provider fails, the workflow still completes on deterministic policy alone.
          </p>
        </div>
        <ObservabilityPanel />
      </section>

      {/* 6 — Why it's different: a direct argument, not adjective cards */}
      <section className="landing-block" id="comparison">
        <p className="landing-kicker">Why Redial</p>
        <h2>Built to be trusted in production</h2>
        <ComparisonTable />
      </section>

      {/* 7 — The proof: the real product */}
      <section className="landing-block dashboard-block">
        <p className="landing-kicker">See it running</p>
        <h2>The console behind every decision</h2>
        <DashboardPreview />
      </section>

      {/* 8 — Close */}
      <section className="landing-block landing-cta-v2">
        <h2>Stop guessing why payments fail.</h2>
        <p className="landing-lede">Launch the dashboard and browse a live workflow run — no setup required.</p>
        <Link to="/dashboard" className="primary-button hero-cta">Launch Dashboard <ArrowRight size={16} /></Link>
      </section>

      <LandingFooter />
    </div>
  )
}
