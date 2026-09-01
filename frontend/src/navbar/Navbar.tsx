import { motion } from 'framer-motion'
import { Bell, ChevronDown, Moon, Search, Sun } from 'lucide-react'
import { useTheme } from '../hooks/useTheme'

export function Navbar() {
  const { theme, toggleTheme } = useTheme()
  return <motion.header className="navbar" initial={{ y: -10, opacity: 0 }} animate={{ y: 0, opacity: 1 }} transition={{ duration: .3 }}><div className="search"><Search size={17} /><input aria-label="Search" placeholder="Search mandates, decisions..." /><kbd>⌘ K</kbd></div><div className="nav-actions"><button className="icon-button" aria-label="Toggle dark mode" onClick={toggleTheme}>{theme === 'light' ? <Moon size={18} /> : <Sun size={18} />}</button><button className="icon-button notification" aria-label="Notifications"><Bell size={18} /><span /></button><div className="user"><div className="avatar">SA</div><div className="user-copy"><strong>Sam Analyst</strong><span>Operations</span></div><ChevronDown size={15} /></div></div></motion.header>
}
