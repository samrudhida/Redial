import { motion } from 'framer-motion'
import { DatabaseZap, Moon, Sun, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'
import { useDeleteDemoData, useSeedDemoData } from '../hooks/useDevSeed'
import { useTheme } from '../hooks/useTheme'
import { useSettings } from '../hooks/useSettings'
import { Modal } from '../ui/Modal'
import { PageHeader } from '../ui/PageHeader'
import { SectionCard } from '../ui/SectionCard'
import { extractErrorMessage } from '../utils/apiError'
import { formatCount } from '../utils/format'
import type { SeedSummary } from '../services/devSeedApi'

const PAGE_SIZE_OPTIONS = [10, 25, 50, 100]
const REFRESH_OPTIONS = [
  { value: 0, label: 'Off' },
  { value: 30, label: 'Every 30 seconds' },
  { value: 60, label: 'Every minute' },
  { value: 300, label: 'Every 5 minutes' },
]

function describeSeedSummary(summary: SeedSummary): string {
  return [
    `${formatCount(summary.mandates_created)} mandates`,
    `${formatCount(summary.payment_attempts_created)} payment attempts`,
    `${formatCount(summary.retry_schedules_created)} retry schedules`,
    `${formatCount(summary.decisions_created)} AI decisions`,
    `${formatCount(summary.communications_created)} communications`,
    `${formatCount(summary.escalations_created)} escalations`,
  ].join(', ')
}

export function SettingsPage() {
  const { theme, toggleTheme } = useTheme()
  const { settings, updateSettings } = useSettings()
  const seedDemoData = useSeedDemoData()
  const deleteDemoData = useDeleteDemoData()
  const [isConfirmDeleteOpen, setIsConfirmDeleteOpen] = useState(false)

  function handleSeed() {
    seedDemoData.mutate(150, {
      onSuccess: summary => {
        toast.success('Demo data generated', { description: describeSeedSummary(summary) })
      },
      onError: error => {
        toast.error('Failed to generate demo data', { description: extractErrorMessage(error, 'This endpoint is only available when the backend is running in development mode.') })
      },
    })
  }

  function handleConfirmDelete() {
    deleteDemoData.mutate(undefined, {
      onSuccess: summary => {
        toast.success('Demo data deleted', { description: `Removed ${formatCount(summary.mandates_deleted)} demo mandates and everything attached to them.` })
        setIsConfirmDeleteOpen(false)
      },
      onError: error => {
        toast.error('Failed to delete demo data', { description: extractErrorMessage(error, 'This endpoint is only available when the backend is running in development mode.') })
        setIsConfirmDeleteOpen(false)
      },
    })
  }

  return (
    <motion.section className="page" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.28 }}>
      <PageHeader title="Settings" description="Configure workspace preferences and integrations." />

      <SectionCard title="Workspace preferences" meta="Stored locally in this browser — there is no backend settings API">
        <div className="settings-form">
          <div className="settings-field">
            <label htmlFor="theme-toggle">Theme</label>
            <p>Switch between light and dark mode.</p>
            <button type="button" id="theme-toggle" className="secondary-button theme-toggle-row" onClick={toggleTheme}>
              {theme === 'light' ? <Moon size={16} /> : <Sun size={16} />}
              {theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'}
            </button>
          </div>

          <div className="settings-field">
            <label htmlFor="table-page-size">Table page size</label>
            <p>Number of rows fetched per page across Mandates, Payments, Retry Queue, Communications, AI Decisions, and Escalations.</p>
            <select
              id="table-page-size"
              value={settings.tablePageSize}
              onChange={event => updateSettings({ tablePageSize: Number(event.target.value) })}
            >
              {PAGE_SIZE_OPTIONS.map(size => <option key={size} value={size}>{size} rows</option>)}
            </select>
          </div>

          <div className="settings-field">
            <label htmlFor="dashboard-refresh">Live data refresh</label>
            <p>How often every page — KPIs, tables, charts, and graphs — automatically refetches from the backend. Applies app-wide.</p>
            <select
              id="dashboard-refresh"
              value={settings.dashboardRefreshIntervalSeconds}
              onChange={event => updateSettings({ dashboardRefreshIntervalSeconds: Number(event.target.value) })}
            >
              {REFRESH_OPTIONS.map(option => <option key={option.value} value={option.value}>{option.label}</option>)}
            </select>
          </div>
        </div>
      </SectionCard>

      <SectionCard title="Developer tools" meta="Only available when the backend is running in development mode">
        <div className="settings-form">
          <div className="settings-field">
            <label htmlFor="seed-demo-data">Seed demo data</label>
            <p>Generates 150 realistic demo mandates (with matching payment attempts, retry schedules, AI decisions, communications, and escalations) through the real backend APIs, spread across the past 60 days.</p>
            <button type="button" id="seed-demo-data" className="secondary-button theme-toggle-row" onClick={handleSeed} disabled={seedDemoData.isPending}>
              <DatabaseZap size={16} />
              {seedDemoData.isPending ? 'Generating...' : 'Seed demo data'}
            </button>
          </div>

          <div className="settings-field">
            <label htmlFor="delete-demo-data">Delete demo data</label>
            <p>Removes only the demo mandates this tool created (and everything attached to them). Real, user-created mandates are never touched.</p>
            <button type="button" id="delete-demo-data" className="secondary-button theme-toggle-row" onClick={() => setIsConfirmDeleteOpen(true)} disabled={deleteDemoData.isPending}>
              <Trash2 size={16} />
              {deleteDemoData.isPending ? 'Deleting...' : 'Delete demo data'}
            </button>
          </div>
        </div>
      </SectionCard>

      <Modal open={isConfirmDeleteOpen} onClose={() => setIsConfirmDeleteOpen(false)} title="Delete demo data?">
        <div className="modal-body">
          <p>This permanently deletes every mandate seeded by this tool, and everything attached to it (payment attempts, retry schedules, AI decisions, communications, escalations). Mandates you created yourself are never affected.</p>
        </div>
        <div className="modal-footer">
          <button type="button" className="secondary-button" onClick={() => setIsConfirmDeleteOpen(false)} disabled={deleteDemoData.isPending}>Cancel</button>
          <button type="button" className="primary-button" onClick={handleConfirmDelete} disabled={deleteDemoData.isPending}>
            {deleteDemoData.isPending ? 'Deleting...' : 'Delete demo data'}
          </button>
        </div>
      </Modal>
    </motion.section>
  )
}
