import { useState, type ReactNode } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { Menu, X } from 'lucide-react'
import { Navbar } from '../navbar/Navbar'
import { Sidebar } from '../sidebar/Sidebar'

export function AppShell({ children }: { children: ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  return <div className="app-shell">
    <AnimatePresence>{sidebarOpen && <motion.button className="scrim" aria-label="Close navigation" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setSidebarOpen(false)} />}</AnimatePresence>
    <Sidebar open={sidebarOpen} onNavigate={() => setSidebarOpen(false)} />
    <div className="shell-main"><Navbar /><button className="mobile-menu" aria-label="Open navigation" onClick={() => setSidebarOpen(true)}>{sidebarOpen ? <X size={20} /> : <Menu size={20} />}</button><main>{children}</main><footer><span>REDIAL / OPERATIONS CONSOLE</span><span>v0.1.0 <i /> All systems nominal</span></footer></div>
  </div>
}
