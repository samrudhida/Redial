import { Menu, X } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'

const SECTION_LINKS = [
  { label: 'Home', href: '#top' },
  { label: 'Workflow', href: '#workflow' },
  { label: 'Why Redial', href: '#comparison' },
  { label: 'About', href: '#about' },
] as const

/** Marketing nav for the landing/auth pages — deliberately separate from the dashboard Sidebar/Navbar. */
export function LandingNav() {
  const [open, setOpen] = useState(false)

  return (
    <header className="landing-nav">
      <div className="landing-nav-inner">
        <a href="#top" className="landing-brand" onClick={() => setOpen(false)}>
          <span className="brand-mark" aria-hidden="true">
            <svg viewBox="0 0 40 40"><path d="M20 3 35 12v16L20 37 5 28V12L20 3Z" /><path d="m12 20 5 5 11-11" /></svg>
          </span>
          <strong>REDIAL</strong>
        </a>

        <nav className={`landing-nav-links ${open ? 'is-open' : ''}`}>
          {SECTION_LINKS.map(link => (
            <a key={link.href} href={link.href} onClick={() => setOpen(false)}>{link.label}</a>
          ))}
          <div className="landing-nav-auth">
            <Link to="/login" className="secondary-button" onClick={() => setOpen(false)}>Login</Link>
            <Link to="/signup" className="primary-button" onClick={() => setOpen(false)}>Sign Up</Link>
          </div>
        </nav>

        <button type="button" className="icon-button landing-nav-toggle" aria-label={open ? 'Close menu' : 'Open menu'} onClick={() => setOpen(value => !value)}>
          {open ? <X size={20} /> : <Menu size={20} />}
        </button>
      </div>
    </header>
  )
}
