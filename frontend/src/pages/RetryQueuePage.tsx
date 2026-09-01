import { motion } from 'framer-motion'
import { useMemo, useState } from 'react'
import { useRetrySchedules } from '../hooks/useRetrySchedules'
import { useSettings } from '../hooks/useSettings'
import type { RetrySchedule } from '../types/retrySchedule'
import { DataTable, type DataTableColumn } from '../ui/DataTable'
import { ClipboardCheck } from 'lucide-react'
import { EmptyState } from '../ui/EmptyState'
import { PageHeader } from '../ui/PageHeader'
import { Pagination } from '../ui/Pagination'
import { QueryError } from '../ui/QueryError'
import { SectionCard } from '../ui/SectionCard'
import { Skeleton } from '../ui/Skeleton'
import { StatusBadge } from '../ui/StatusBadge'
import { formatDate, truncateId } from '../utils/format'
import { retryStatusPresentation } from '../utils/statusPresentation'

type SortKey = 'recommended_time' | 'retry_count'

export function RetryQueuePage() {
  const { settings } = useSettings()
  const [offset, setOffset] = useState(0)
  const [sortKey, setSortKey] = useState<SortKey>('recommended_time')
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc')

  const { data, isPending, isError, error, refetch } = useRetrySchedules({ offset, limit: settings.tablePageSize })

  const sortedRows = useMemo(() => {
    if (!data) return []
    const rows = [...data]
    rows.sort((a, b) => {
      const direction = sortDirection === 'asc' ? 1 : -1
      if (sortKey === 'retry_count') return (a.retry_count - b.retry_count) * direction
      return (new Date(a.recommended_time).getTime() - new Date(b.recommended_time).getTime()) * direction
    })
    return rows
  }, [data, sortKey, sortDirection])

  function handleSort(key: string) {
    if (key !== 'recommended_time' && key !== 'retry_count') return
    if (key === sortKey) {
      setSortDirection(direction => (direction === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(key)
      setSortDirection('asc')
    }
  }

  const columns: DataTableColumn<RetrySchedule>[] = [
    { key: 'mandate_id', header: 'Mandate ID', render: schedule => truncateId(schedule.mandate_id) },
    { key: 'status', header: 'Retry Status', render: schedule => { const { label, tone } = retryStatusPresentation(schedule.status); return <StatusBadge label={label} tone={tone} /> } },
    { key: 'retry_strategy', header: 'Retry Strategy', render: schedule => schedule.retry_strategy },
    { key: 'retry_count', header: 'Retry Count', sortable: true, render: schedule => `${schedule.retry_count} / ${schedule.max_retries}` },
    { key: 'recommended_time', header: 'Next Retry', sortable: true, render: schedule => formatDate(schedule.recommended_time) },
  ]

  return (
    <motion.section className="page" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.28 }}>
      <PageHeader title="Retry Queue" description="Coordinate upcoming payment recovery attempts." />

      <SectionCard
        title="Pending retries"
        className="data-panel"
        meta="Only pending/scheduled retries — the backend has no priority field and no way to list executed/cancelled/exhausted retries through this endpoint"
      >
        {isPending && <Skeleton style={{ height: 240 }} />}
        {isError && <QueryError message={error instanceof Error ? error.message : 'Failed to load the retry queue.'} onRetry={() => void refetch()} />}
        {data && data.length === 0 && <EmptyState icon={ClipboardCheck} title="No pending retries" description="The retry queue is empty right now — every mandate is caught up." />}
        {data && data.length > 0 && (
          <>
            <DataTable columns={columns} rows={sortedRows} getRowKey={schedule => schedule.id} sortKey={sortKey} sortDirection={sortDirection} onSort={handleSort} />
            <Pagination offset={offset} limit={settings.tablePageSize} count={data.length} onPrevious={() => setOffset(value => Math.max(0, value - settings.tablePageSize))} onNext={() => setOffset(value => value + settings.tablePageSize)} />
          </>
        )}
      </SectionCard>
    </motion.section>
  )
}
