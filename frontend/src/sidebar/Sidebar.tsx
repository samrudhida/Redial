import { motion } from 'framer-motion'
import { Activity, BarChart3, BellRing, Bot, ClipboardList, CreditCard, Gauge, LifeBuoy, MessageSquareText, Receipt, Settings, ShieldAlert } from 'lucide-react'
import { NavLink } from 'react-router-dom'
import { useDashboardSummary } from '../hooks/useDashboard'

const items = [
  ['Dashboard', '/dashboard', Gauge],
  ['Mandates', '/mandates', CreditCard],
  ['Payments', '/payments', Receipt],
  ['Retry Queue', '/retry-queue', ClipboardList],
  ['AI Decisions', '/ai-decisions', Bot],
  ['Communications', '/communications', MessageSquareText],
  ['Escalations', '/escalations', ShieldAlert],
  ['Analytics', '/analytics', BarChart3],
  ['Observability', '/observability', Activity],
  ['Settings', '/settings', Settings],
] as const

export function Sidebar({ open, onNavigate }: { open: boolean; onNavigate: () => void }) {
  const { data } = useDashboardSummary()
  return <aside className={`sidebar ${open ? 'sidebar-open' : ''}`}>
    <div className="brand"><div className="brand-mark" aria-hidden="true"><svg viewBox="0 0 40 40"><path d="M20 3 35 12v16L20 37 5 28V12L20 3Z" /><path d="m12 20 5 5 11-11" /></svg></div><div><strong>REDIAL</strong><span>AI MANDATE RETRY SEQUENCER</span></div></div>
    <div className="nav-label">Workspace</div><nav>{items.map(([label, path, Icon]) => <NavLink key={path} to={path} onClick={onNavigate} className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}><Icon size={17} strokeWidth={1.8} /><span>{label}</span>{path === '/retry-queue' && data && data.pending_retries > 0 && <em>{data.pending_retries}</em>}</NavLink>)}</nav>
    <motion.div className="sidebar-status" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: .2 }}><div className="status-top"><BellRing size={15} /><span>System status</span><span className="status-dot" /></div><strong>Operational</strong><p>Last checked just now</p></motion.div>
    <div className="sidebar-foot"><LifeBuoy size={15} /><span>Support center</span></div>
  </aside>
}
