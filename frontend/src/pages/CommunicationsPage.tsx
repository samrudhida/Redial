import { motion } from 'framer-motion'
import { useState } from 'react'
import { useCommunications } from '../hooks/useCommunications'
import { useSettings } from '../hooks/useSettings'
import type { CommunicationChannel } from '../types/enums'
import type { Communication } from '../types/communication'
import { DataTable, type DataTableColumn } from '../ui/DataTable'
import { MessageSquareText } from 'lucide-react'
import { EmptyState } from '../ui/EmptyState'
import { FilterBar, FilterSelect } from '../ui/FilterBar'
import { PageHeader } from '../ui/PageHeader'
import { Pagination } from '../ui/Pagination'
import { QueryError } from '../ui/QueryError'
import { SectionCard } from '../ui/SectionCard'
import { Skeleton } from '../ui/Skeleton'
import { StatusBadge } from '../ui/StatusBadge'
import { truncateId } from '../utils/format'
import { communicationChannelIcon, communicationChannelLabel, deliveryStatusPresentation } from '../utils/statusPresentation'
import { Timestamp } from '../ui/Timestamp'

const CHANNEL_OPTIONS: Array<{ value: CommunicationChannel; label: string }> = [
  { value: 'email', label: 'Email' },
  { value: 'sms', label: 'SMS' },
  { value: 'whatsapp', label: 'WhatsApp' },
  { value: 'push', label: 'Push' },
]

export function CommunicationsPage() {
  const { settings } = useSettings()
  const [offset, setOffset] = useState(0)
  const [channel, setChannel] = useState<CommunicationChannel | ''>('')

  const { data, isPending, isError, error, refetch } = useCommunications({
    channel: channel || undefined,
    offset,
    limit: settings.tablePageSize,
  })

  const columns: DataTableColumn<Communication>[] = [
    { key: 'mandate_id', header: 'Mandate ID', render: communication => <span className="cell-muted" title={communication.mandate_id}>{truncateId(communication.mandate_id)}</span> },
    {
      key: 'channel',
      header: 'Channel',
      render: communication => {
        const Icon = communicationChannelIcon(communication.channel)
        return <span className="channel-cell"><Icon size={14} />{communicationChannelLabel(communication.channel)}</span>
      },
    },
    { key: 'delivery_status', header: 'Delivery Status', render: communication => { const { label, tone } = deliveryStatusPresentation(communication.delivery_status); return <StatusBadge label={label} tone={tone} /> } },
    { key: 'message', header: 'Message', render: communication => <span className="wrap-cell" title={communication.message}>{communication.message}</span> },
    { key: 'sent_at', header: 'Timestamp', render: communication => <Timestamp iso={communication.sent_at} /> },
  ]

  return (
    <motion.section className="page" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.28 }}>
      <PageHeader title="Communications" description="Track customer outreach across recovery workflows." />

      <SectionCard title="All communications" className="data-panel">
        <FilterBar>
          <FilterSelect label="Channel" value={channel} onChange={value => { setChannel(value as CommunicationChannel | ''); setOffset(0) }} options={CHANNEL_OPTIONS} />
        </FilterBar>

        {isPending && <Skeleton style={{ height: 240 }} />}
        {isError && <QueryError message={error instanceof Error ? error.message : 'Failed to load communications.'} onRetry={() => void refetch()} />}
        {data && data.length === 0 && <EmptyState icon={MessageSquareText} title="No communications found" description="No communications match the current filters." />}
        {data && data.length > 0 && (
          <>
            <DataTable columns={columns} rows={data} getRowKey={communication => communication.id} />
            <Pagination offset={offset} limit={settings.tablePageSize} count={data.length} onPrevious={() => setOffset(value => Math.max(0, value - settings.tablePageSize))} onNext={() => setOffset(value => value + settings.tablePageSize)} />
          </>
        )}
      </SectionCard>
    </motion.section>
  )
}
