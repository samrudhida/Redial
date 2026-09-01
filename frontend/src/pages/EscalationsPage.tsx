import { motion } from 'framer-motion'
import { useState } from 'react'
import { useEscalations } from '../hooks/useEscalations'
import { useSettings } from '../hooks/useSettings'
import type { Escalation } from '../types/escalation'
import { DataTable, type DataTableColumn } from '../ui/DataTable'
import { ShieldAlert } from 'lucide-react'
import { EmptyState } from '../ui/EmptyState'
import { FilterBar } from '../ui/FilterBar'
import { PageHeader } from '../ui/PageHeader'
import { Pagination } from '../ui/Pagination'
import { QueryError } from '../ui/QueryError'
import { SectionCard } from '../ui/SectionCard'
import { Skeleton } from '../ui/Skeleton'
import { StatusBadge } from '../ui/StatusBadge'
import { formatDate, truncateId, truncateText } from '../utils/format'
import { escalationLevelPresentation } from '../utils/statusPresentation'

const RESOLUTION_OPTIONS = [
  { value: 'false', label: 'Open' },
  { value: 'true', label: 'Resolved' },
]

export function EscalationsPage() {
  const { settings } = useSettings()
  const [offset, setOffset] = useState(0)
  const [resolved, setResolved] = useState<'false' | 'true'>('false')

  const { data, isPending, isError, error, refetch } = useEscalations({
    resolved: resolved === 'true',
    offset,
    limit: settings.tablePageSize,
  })

  const columns: DataTableColumn<Escalation>[] = [
    { key: 'mandate_id', header: 'Mandate ID', render: escalation => <span className="cell-muted">{truncateId(escalation.mandate_id)}</span> },
    { key: 'escalation_level', header: 'Escalation Level', render: escalation => { const { label, tone } = escalationLevelPresentation(escalation.escalation_level); return <StatusBadge label={label} tone={tone} /> } },
    { key: 'resolved', header: 'Status', render: escalation => <StatusBadge label={escalation.resolved ? 'Resolved' : 'Open'} tone={escalation.resolved ? 'success' : 'warning'} /> },
    { key: 'reason', header: 'Reason', render: escalation => <strong>{truncateText(escalation.reason, 130)}</strong> },
    { key: 'assigned_to', header: 'Assigned To', render: escalation => <span className="cell-muted">{escalation.assigned_to ?? 'Unassigned'}</span> },
    // The backend has no created_at for escalations — resolved_at is the only
    // real timestamp, and it's null until resolved. Do not invent a creation time.
    { key: 'resolved_at', header: 'Resolved At', render: escalation => <span className="cell-muted">{formatDate(escalation.resolved_at)}</span> },
  ]

  return (
    <motion.section className="page" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.28 }}>
      <PageHeader title="Escalations" description="Keep operational exceptions visible and accountable." />

      <SectionCard
        title="Escalations"
        className="data-panel"
        meta="The backend does not record an escalation creation time — only a resolution timestamp, which is empty until resolved"
      >
        <FilterBar>
          <label className="filter-select">
            <span>Resolution</span>
            <select value={resolved} onChange={event => { setResolved(event.target.value === 'true' ? 'true' : 'false'); setOffset(0) }}>
              {RESOLUTION_OPTIONS.map(option => <option key={option.value} value={option.value}>{option.label}</option>)}
            </select>
          </label>
        </FilterBar>

        {isPending && <Skeleton style={{ height: 240 }} />}
        {isError && <QueryError message={error instanceof Error ? error.message : 'Failed to load escalations.'} onRetry={() => void refetch()} />}
        {data && data.length === 0 && <EmptyState icon={ShieldAlert} title={resolved === 'true' ? 'No resolved escalations' : 'No open escalations'} description="No escalations match the current filter." />}
        {data && data.length > 0 && (
          <>
            <DataTable columns={columns} rows={data} getRowKey={escalation => escalation.id} />
            <Pagination offset={offset} limit={settings.tablePageSize} count={data.length} onPrevious={() => setOffset(value => Math.max(0, value - settings.tablePageSize))} onNext={() => setOffset(value => value + settings.tablePageSize)} />
          </>
        )}
      </SectionCard>
    </motion.section>
  )
}
