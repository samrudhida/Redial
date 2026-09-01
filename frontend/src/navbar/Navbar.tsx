import { motion } from 'framer-motion'
import { Bell, ChevronDown, Moon, Search, Sun } from 'lucide-react'
import { useTheme } from '../hooks/useTheme'
import { useUser } from '../hooks/useUser'

export function Navbar() {
  const { theme, toggleTheme } = useTheme()
  const { name } = useUser()
  const displayName = name ?? 'Guest'
  const initials = getInitials(displayName)
  return <motion.header className="navbar" initial={{ y: -10, opacity: 0 }} animate={{ y: 0, opacity: 1 }} transition={{ duration: .3 }}><div className="search"><Search size={17} /><input aria-label="Search" placeholder="Search mandates, decisions..." /><kbd>⌘ K</kbd></div><div className="nav-actions"><button className="icon-button" aria-label="Toggle dark mode" onClick={toggleTheme}>{theme === 'light' ? <Moon size={18} /> : <Sun size={18} />}</button><button className="icon-button notification" aria-label="Notifications"><Bell size={18} /><span /></button><div className="user"><div className="avatar">{initials}</div><div className="user-copy"><strong>{displayName}</strong><span>Operations</span></div><ChevronDown size={15} /></div></div></motion.header>
}

function getInitials(name: string): string {
  const words = name.trim().split(/\s+/)
  if (words.length === 1) return words[0].slice(0, 1).toUpperCase() || 'G'
  return (words[0][0] + words[words.length - 1][0]).toUpperCase()
}
