import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { ShieldCheck, Sparkles, Workflow } from 'lucide-react'

const HIGHLIGHTS = [
  { icon: Sparkles, text: 'AI-assisted retry decisions with full reasoning trails' },
  { icon: Workflow, text: 'A visual, auditable recovery workflow end to end' },
  { icon: ShieldCheck, text: 'Every decision logged for observability and audit' },
]

/** Shared two-pane chrome for Login/Signup — matches the landing page's visual language. */
export function AuthLayout({ title, description, children }: { title: string; description: string; children: ReactNode }) {
  return (
    <div className="auth-shell">
      <div className="auth-side">
        <Link to="/" className="landing-brand">
          <span className="brand-mark" aria-hidden="true">
            <svg viewBox="0 0 40 40"><path d="M20 3 35 12v16L20 37 5 28V12L20 3Z" /><path d="m12 20 5 5 11-11" /></svg>
          </span>
          <strong>REDIAL</strong>
        </Link>
        <h2>Operate payment recovery with an AI co-pilot.</h2>
        <ul className="auth-highlights">
          {HIGHLIGHTS.map(item => (
            <li key={item.text}><item.icon size={16} />{item.text}</li>
          ))}
        </ul>
      </div>

      <div className="auth-main">
        <div className="auth-card">
          <div className="auth-card-head">
            <h1>{title}</h1>
            <p>{description}</p>
          </div>
          {children}
        </div>
      </div>
    </div>
  )
}
