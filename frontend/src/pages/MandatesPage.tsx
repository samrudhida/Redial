import { motion } from 'framer-motion'
import { Plus } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useMandates } from '../hooks/useMandates'
import { useSettings } from '../hooks/useSettings'
import type { MandateStatus } from '../types/enums'
import { CreateMandateModal } from '../ui/CreateMandateModal'
import { DataTable, type DataTableColumn } from '../ui/DataTable'
import { CreditCard } from 'lucide-react'
import { EmptyState } from '../ui/EmptyState'
import { FilterBar, FilterSelect } from '../ui/FilterBar'
import { PageHeader } from '../ui/PageHeader'
import { Pagination } from '../ui/Pagination'
import { QueryError } from '../ui/QueryError'
import { SearchBar } from '../ui/SearchBar'
import { SectionCard } from '../ui/SectionCard'
import { Skeleton } from '../ui/Skeleton'
import { StatusBadge } from '../ui/StatusBadge'
import type { Mandate } from '../types/mandate'
import { formatCurrency, formatDate, truncateId } from '../utils/format'
import { mandateStatusPresentation } from '../utils/statusPresentation'

const STATUS_OPTIONS: Array<{ value: MandateStatus; label: string }> = [
  { value: 'active', label: 'Active' },
  { value: 'paused', label: 'Paused' },
  { value: 'cancelled', label: 'Cancelled' },
  { value: 'expired', label: 'Expired' },
  { value: 'completed', label: 'Completed' },
]

export function MandatesPage() {
  const { settings } = useSettings()
  const [offset, setOffset] = useState(0)
  const [status, setStatus] = useState<MandateStatus | ''>('')
  const [customerIdInput, setCustomerIdInput] = useState('')
  const [customerId, setCustomerId] = useState('')
  const [isCreateMandateOpen, setIsCreateMandateOpen] = useState(false)

  // The backend only supports an exact customer_id match (no partial/fuzzy
  // search), so debounce the raw input before sending it as a filter.
  useEffect(() => {
    const timeout = setTimeout(() => {
      setCustomerId(customerIdInput.trim())
      setOffset(0)
    }, 300)
    return () => clearTimeout(timeout)
  }, [customerIdInput])

  const { data, isPending, isError, error, refetch } = useMandates({
    status: status || undefined,
    customer_id: customerId || undefined,
    offset,
    limit: settings.tablePageSize,
  })

  const columns: DataTableColumn<Mandate>[] = [
    { key: 'id', header: 'Mandate ID', render: mandate => truncateId(mandate.id) },
    { key: 'customer_id', header: 'Customer ID', render: mandate => mandate.customer_id },
    { key: 'amount', header: 'Amount', render: mandate => `${formatCurrency(mandate.amount)} ${mandate.currency !== 'INR' ? mandate.currency : ''}`.trim() },
    { key: 'status', header: 'Status', render: mandate => { const { label, tone } = mandateStatusPresentation(mandate.status); return <StatusBadge label={label} tone={tone} /> } },
    { key: 'created_at', header: 'Created', render: mandate => formatDate(mandate.created_at) },
    { key: 'updated_at', header: 'Updated', render: mandate => formatDate(mandate.updated_at) },
  ]

  return (
    <motion.section className="page" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.28 }}>
      <PageHeader
        title="Mandates"
        description="Review and manage customer mandate records."
        actions={<button type="button" className="primary-button" onClick={() => setIsCreateMandateOpen(true)}><Plus size={16} />New Mandate</button>}
      />

      <SectionCard title="All mandates" className="data-panel" meta="Exact customer ID match — the backend does not support partial/fuzzy search">
        <FilterBar>
          <SearchBar value={customerIdInput} onChange={setCustomerIdInput} placeholder="Search by exact customer ID" />
          <FilterSelect label="Status" value={status} onChange={value => { setStatus(value as MandateStatus | ''); setOffset(0) }} options={STATUS_OPTIONS} />
        </FilterBar>

        {isPending && <Skeleton style={{ height: 240 }} />}

        {isError && (
          <QueryError message={error instanceof Error ? error.message : 'Failed to load mandates.'} onRetry={() => void refetch()} />
        )}

        {data && data.length === 0 && (
          <EmptyState icon={CreditCard} title="No mandates found" description="No mandates match the current filters." />
        )}

        {data && data.length > 0 && (
          <>
            <DataTable columns={columns} rows={data} getRowKey={mandate => mandate.id} />
            <Pagination offset={offset} limit={settings.tablePageSize} count={data.length} onPrevious={() => setOffset(value => Math.max(0, value - settings.tablePageSize))} onNext={() => setOffset(value => value + settings.tablePageSize)} />
          </>
        )}
      </SectionCard>

      <CreateMandateModal open={isCreateMandateOpen} onClose={() => setIsCreateMandateOpen(false)} />
    </motion.section>
  )
}
