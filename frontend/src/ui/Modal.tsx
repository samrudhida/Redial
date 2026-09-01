import { AnimatePresence, motion } from 'framer-motion'
import { X } from 'lucide-react'
import { useEffect } from 'react'
import type { ReactNode } from 'react'

/** Generic dialog shell — backdrop, esc-to-close, click-outside-to-close. */
export function Modal({
  open,
  onClose,
  title,
  children,
  size = 'default',
}: {
  open: boolean
  onClose: () => void
  title: string
  children: ReactNode
  /** 'wide' is for content that needs more room than a form, e.g. a data table. */
  size?: 'default' | 'wide'
}) {
  useEffect(() => {
    if (!open) return
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [open, onClose])

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="modal-backdrop"
          onClick={onClose}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.15 }}
        >
          <motion.div
            className={`modal-panel ${size === 'wide' ? 'modal-panel-wide' : ''}`}
            role="dialog"
            aria-modal="true"
            aria-label={title}
            onClick={event => event.stopPropagation()}
            initial={{ opacity: 0, y: 12, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8, scale: 0.98 }}
            transition={{ duration: 0.18 }}
          >
            <div className="modal-header">
              <h2>{title}</h2>
              <button type="button" className="icon-button" aria-label="Close" onClick={onClose}><X size={18} /></button>
            </div>
            {children}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
