import { Link } from 'react-router-dom'

export function LandingFooter() {
  return (
    <footer className="landing-footer" id="about">
      <div className="landing-footer-inner">
        <div className="landing-footer-brand">
          <span className="brand-mark" aria-hidden="true">
            <svg viewBox="0 0 40 40"><path d="M20 3 35 12v16L20 37 5 28V12L20 3Z" /><path d="m12 20 5 5 11-11" /></svg>
          </span>
          <div>
            <strong>REDIAL</strong>
            <p>AI mandate retry sequencer — an operations console for intelligent payment recovery workflows.</p>
          </div>
        </div>

        <div className="landing-footer-links">
          <div>
            <span>Product</span>
            <a href="#workflow">Workflow</a>
            <a href="#thinking">How it thinks</a>
            <a href="#comparison">Why Redial</a>
          </div>
          <div>
            <span>Console</span>
            <Link to="/dashboard">Dashboard</Link>
            <Link to="/login">Login</Link>
            <Link to="/signup">Sign Up</Link>
          </div>
        </div>
      </div>
      <div className="landing-footer-bottom">
        <span>REDIAL / OPERATIONS CONSOLE</span>
        <span>v0.1.0 <i /> Built for the Razorpay AI Buildathon 2026</span>
      </div>
    </footer>
  )
}
