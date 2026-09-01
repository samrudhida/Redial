import { motion } from 'framer-motion'
import { Activity, Bot, CreditCard, Gauge, Timer } from 'lucide-react'

/**
 * A static, illustrative mock of the real dashboard — reuses the exact
 * `.kpi-card` / `.dash-panel` / `.confidence` / `.pie-legend` visual language
 * from DashboardPage so the hero preview feels like the real product rather
 * than a generic illustration. Numbers here are representative placeholders
 * for layout purposes only, not a claim of live data.
 */
export function DashboardPreview() {
  const kpis = [
    { label: 'Active mandates', value: '128', icon: CreditCard, tone: 'blue' },
    { label: 'Pending retries', value: '24', icon: Timer, tone: 'amber' },
    { label: 'Recovery rate', value: '76.3%', icon: Gauge, tone: 'violet' },
  ] as const

  const decisions = [
    { mandate: 'MND-2201', type: 'retry scheduled', confidence: '92%' },
    { mandate: 'MND-2198', type: 'communication sent', confidence: '87%' },
    { mandate: 'MND-2190', type: 'escalation raised', confidence: '81%' },
  ]

  return (
    <motion.div
      className="hero-preview"
      initial={{ opacity: 0, y: 40, rotateX: 8, scale: 0.96 }}
      whileInView={{ opacity: 1, y: 0, rotateX: 0, scale: 1 }}
      viewport={{ once: true, margin: '-100px' }}
      transition={{ duration: 0.8, ease: 'easeOut' }}
      aria-hidden="true"
    >
      <div className="hero-preview-chrome">
        <span /><span /><span />
        <em>redial.app/dashboard</em>
      </div>
      <div className="hero-preview-body">
        <div className="kpi-grid hero-preview-kpis">
          {kpis.map(kpi => (
            <div className={`kpi-card ${kpi.tone}`} key={kpi.label}>
              <div className="kpi-top"><span>{kpi.label}</span><span className="kpi-icon"><kpi.icon size={15} /></span></div>
              <strong>{kpi.value}</strong>
              <div className="progress-track"><div style={{ width: '68%' }} /></div>
            </div>
          ))}
        </div>
        <div className="dash-panel hero-preview-panel">
          <div className="panel-heading"><div><h2>Recent AI decisions</h2><p>Latest recommendations</p></div></div>
          <div className="hero-preview-rows">
            {decisions.map(decision => (
              <div className="hero-preview-row" key={decision.mandate}>
                <span className="cell-muted">{decision.mandate}</span>
                <span className="channel-cell"><Bot size={13} />{decision.type}</span>
                <span className="confidence"><span style={{ width: decision.confidence }} />{decision.confidence}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="hero-preview-status">
          <Activity size={13} /> Workflow engine <b>operational</b>
        </div>
      </div>
    </motion.div>
  )
}
