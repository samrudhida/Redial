import { motion } from 'framer-motion'
import { ArrowLeft, CreditCard } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { toast } from 'sonner'
import { useMandates } from '../hooks/useMandates'
import { usePayments } from '../hooks/usePayments'
import { useRazorpayConfig } from '../hooks/useRazorpayConfig'
import { useRecordPaymentAttempt } from '../hooks/useRecordPaymentAttempt'
import { useSettings } from '../hooks/useSettings'
import type { DeclineCategory, PaymentStatus } from '../types/enums'
import type { PaymentAttempt } from '../types/payment'
import { DataTable, type DataTableColumn } from '../ui/DataTable'
import { EmptyState } from '../ui/EmptyState'
import { FilterBar, FilterSelect } from '../ui/FilterBar'
import { Modal } from '../ui/Modal'
import { PageHeader } from '../ui/PageHeader'
import { Pagination } from '../ui/Pagination'
import { QueryError } from '../ui/QueryError'
import { SearchBar } from '../ui/SearchBar'
import { SectionCard } from '../ui/SectionCard'
import { Skeleton } from '../ui/Skeleton'
import { StatusBadge } from '../ui/StatusBadge'
import { Timestamp } from '../ui/Timestamp'
import { extractErrorMessage } from '../utils/apiError'
import { formatCurrency, truncateId } from '../utils/format'
import { openRazorpayCheckout } from '../utils/razorpayCheckout'
import { declineCategoryLabel, paymentStatusPresentation } from '../utils/statusPresentation'

const STATUS_OPTIONS: Array<{ value: PaymentStatus; label: string }> = [
  { value: 'pending', label: 'Pending' },
  { value: 'processing', label: 'Processing' },
  { value: 'succeeded', label: 'Succeeded' },
  { value: 'failed', label: 'Failed' },
  { value: 'retry_scheduled', label: 'Retry Scheduled' },
]

const DECLINE_CATEGORY_OPTIONS: Array<{ value: DeclineCategory; label: string }> = [
  { value: 'insufficient_funds', label: 'Insufficient Funds' },
  { value: 'bank_unavailable', label: 'Bank Unavailable' },
  { value: 'authentication_required', label: 'Authentication Required' },
  { value: 'mandate_inactive', label: 'Mandate Inactive' },
  { value: 'limit_exceeded', label: 'Limit Exceeded' },
  { value: 'account_closed', label: 'Account Closed' },
  { value: 'technical_error', label: 'Technical Error' },
  { value: 'unknown', label: 'Unknown' },
]

/** GET /api/v1/mandates has no partial-search endpoint, so this picker relies on the same exact customer_id match used on the Mandates page. */
function MandatePicker({ onSelect }: { onSelect: (mandateId: string) => void }) {
  const [customerIdInput, setCustomerIdInput] = useState('')
  const [customerId, setCustomerId] = useState('')

  useEffect(() => {
    const timeout = setTimeout(() => setCustomerId(customerIdInput.trim()), 300)
    return () => clearTimeout(timeout)
  }, [customerIdInput])

  const { data, isPending, isError, error, refetch } = useMandates({ customer_id: customerId || undefined, limit: 25 })

  return (
    <SectionCard title="Select a mandate" className="data-panel" meta="GET /payments requires a mandate_id — there is no mandate-less payments listing">
      <FilterBar>
        <SearchBar value={customerIdInput} onChange={setCustomerIdInput} placeholder="Search by exact customer ID" />
      </FilterBar>

      {isPending && <Skeleton style={{ height: 120 }} />}
      {isError && <QueryError message={error instanceof Error ? error.message : 'Failed to load mandates.'} onRetry={() => void refetch()} />}
      {data && data.length === 0 && <EmptyState compact title="No mandates found" description="Search by customer ID to find a mandate and view its payments." />}
      {data && data.length > 0 && (
        <div className="table-scroll">
          <table>
            <thead><tr><th>Mandate ID</th><th>Customer ID</th><th>Amount</th><th /></tr></thead>
            <tbody>
              {data.map(mandate => (
                <tr key={mandate.id}>
                  <td><strong>{truncateId(mandate.id)}</strong></td>
                  <td>{mandate.customer_id}</td>
                  <td>{formatCurrency(mandate.amount)}</td>
                  <td><button type="button" className="secondary-button" onClick={() => onSelect(mandate.id)}>View payments</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </SectionCard>
  )
}

/**
 * Only the fields PaymentAttemptResponse actually returns (see
 * backend/app/api/routes/payments.py) are shown. There is no updated_at,
 * no dedicated failure-reason field (bank_response_message is the real
 * equivalent), and no retry_schedule_id — RetrySchedule rows are keyed by
 * mandate_id, not payment_attempt_id, so there is no real per-attempt
 * schedule id to display. "Retry Scheduled" is derived from whether
 * next_retry_at is set, which is shown alongside it for context.
 */
function PaymentAttemptDetail({ attempt, onBack }: { attempt: PaymentAttempt; onBack: () => void }) {
  const { label, tone } = paymentStatusPresentation(attempt.status)
  return (
    <div className="modal-body">
      <button type="button" className="secondary-button" onClick={onBack}><ArrowLeft size={14} /> Back to list</button>
      <div className="form-row">
        <div className="form-field"><label>Payment Attempt ID</label><p>{attempt.id}</p></div>
        <div className="form-field"><label>Mandate ID</label><p>{attempt.mandate_id}</p></div>
      </div>
      <div className="form-row">
        <div className="form-field"><label>Status</label><p><StatusBadge label={label} tone={tone} /></p></div>
        <div className="form-field"><label>Amount</label><p>{formatCurrency(attempt.amount)}</p></div>
      </div>
      <div className="form-row">
        <div className="form-field"><label>Decline Category</label><p>{attempt.decline_category ? declineCategoryLabel(attempt.decline_category) : '—'}</p></div>
        <div className="form-field"><label>Failure Reason</label><p>{attempt.bank_response_message ?? '—'}</p></div>
      </div>
      <div className="form-row">
        <div className="form-field"><label>Retry Scheduled</label><p>{attempt.next_retry_at ? 'Yes' : 'No'}</p></div>
        <div className="form-field"><label>Next Retry At</label><p><Timestamp iso={attempt.next_retry_at} /></p></div>
      </div>
      <div className="form-row">
        <div className="form-field"><label>Razorpay Order</label><p className="cell-muted">{attempt.razorpay_order_id ?? 'Not created (demo mode)'}</p></div>
        <div className="form-field"><label>Razorpay Payment</label><p className="cell-muted">{attempt.razorpay_payment_id ?? 'Awaiting confirmation'}</p></div>
      </div>
      <div className="form-field"><label>Created At</label><p><Timestamp iso={attempt.attempted_at} /></p></div>
    </div>
  )
}

/**
 * Records a real attempt via the existing POST /payments, then — only when
 * the backend actually attached a real Razorpay order (i.e. Razorpay is
 * configured) — opens real Razorpay Test Mode Checkout. The checkout's own
 * client-side callback never finalizes payment state itself; only the
 * signature-verified webhook does that (see backend/app/api/routes/webhooks.py).
 */
function RecordAttemptAction({ mandateId }: { mandateId: string }) {
  const recordAttempt = useRecordPaymentAttempt()
  const razorpayConfig = useRazorpayConfig()

  function handleRecord() {
    recordAttempt.mutate(
      { mandate_id: mandateId },
      {
        onSuccess: async attempt => {
          const canCheckout = razorpayConfig.data?.razorpay_configured && attempt.razorpay_order_id && razorpayConfig.data.razorpay_key_id
          if (!canCheckout) {
            toast.success('Payment attempt recorded', { description: 'Razorpay is not configured — this is a simulated attempt, exactly like before.' })
            return
          }
          toast.success('Payment attempt recorded', { description: 'Opening Razorpay Checkout — use a Razorpay test card to complete it.' })
          try {
            await openRazorpayCheckout({
              key: razorpayConfig.data!.razorpay_key_id!,
              amount: Math.round(Number.parseFloat(attempt.amount) * 100),
              currency: 'INR',
              order_id: attempt.razorpay_order_id!,
              name: 'Redial',
              description: `Payment attempt #${attempt.attempt_number}`,
              handler: () => {
                toast('Payment submitted', { description: 'Waiting for Razorpay to confirm via webhook — this list updates automatically once it arrives.' })
              },
              modal: { ondismiss: () => toast('Checkout closed', { description: 'No payment was submitted for this attempt.' }) },
            })
          } catch (error) {
            toast.error('Could not open Razorpay Checkout', { description: extractErrorMessage(error) })
          }
        },
        onError: error => {
          toast.error('Failed to record payment attempt', { description: extractErrorMessage(error) })
        },
      },
    )
  }

  return (
    <button type="button" className="secondary-button" onClick={handleRecord} disabled={recordAttempt.isPending}>
      <CreditCard size={14} />
      {recordAttempt.isPending ? 'Recording...' : 'Record payment attempt'}
    </button>
  )
}

function PaymentAttemptsModal({ mandateId, onClose }: { mandateId: string | null; onClose: () => void }) {
  const { settings } = useSettings()
  const [offset, setOffset] = useState(0)
  const [status, setStatus] = useState<PaymentStatus | ''>('')
  const [declineCategory, setDeclineCategory] = useState<DeclineCategory | ''>('')
  const [selectedAttempt, setSelectedAttempt] = useState<PaymentAttempt | null>(null)

  const { data, isPending, isError, error, refetch } = usePayments(
    mandateId ? { mandate_id: mandateId, status: status || undefined, offset, limit: settings.tablePageSize } : null,
  )

  // decline_category has no server-side filter on this endpoint — filtered client-side over the fetched page.
  const filteredRows = useMemo(
    () => (data ?? []).filter(attempt => !declineCategory || attempt.decline_category === declineCategory),
    [data, declineCategory],
  )

  const columns: DataTableColumn<PaymentAttempt>[] = [
    { key: 'attempt_number', header: 'Attempt Number', render: attempt => attempt.attempt_number },
    { key: 'status', header: 'Status', render: attempt => { const { label, tone } = paymentStatusPresentation(attempt.status); return <StatusBadge label={label} tone={tone} /> } },
    { key: 'razorpay', header: 'Razorpay', render: attempt => <StatusBadge label={attempt.razorpay_order_id ? 'Real order' : 'Demo'} tone={attempt.razorpay_order_id ? 'info' : 'neutral'} /> },
    { key: 'amount', header: 'Amount', render: attempt => formatCurrency(attempt.amount) },
    { key: 'decline_category', header: 'Decline Category', render: attempt => (attempt.decline_category ? declineCategoryLabel(attempt.decline_category) : '—') },
    { key: 'bank_response_message', header: 'Failure Reason', render: attempt => attempt.bank_response_message ?? '—' },
    { key: 'attempted_at', header: 'Created At', render: attempt => <Timestamp iso={attempt.attempted_at} /> },
  ]

  function handleClose() {
    setSelectedAttempt(null)
    setOffset(0)
    setStatus('')
    setDeclineCategory('')
    onClose()
  }

  return (
    <Modal open={mandateId !== null} onClose={handleClose} title={`Payment history — ${mandateId ? truncateId(mandateId) : ''}`} size="wide">
      {selectedAttempt ? (
        <PaymentAttemptDetail attempt={selectedAttempt} onBack={() => setSelectedAttempt(null)} />
      ) : (
        <div className="modal-body">
          <FilterBar>
            <FilterSelect label="Status" value={status} onChange={value => { setStatus(value as PaymentStatus | ''); setOffset(0) }} options={STATUS_OPTIONS} />
            <FilterSelect label="Decline Category" value={declineCategory} onChange={value => setDeclineCategory(value as DeclineCategory | '')} options={DECLINE_CATEGORY_OPTIONS} />
            {mandateId && <RecordAttemptAction mandateId={mandateId} />}
          </FilterBar>

          {isPending && <Skeleton style={{ height: 240 }} />}
          {isError && <QueryError message={error instanceof Error ? error.message : 'Failed to load payments.'} onRetry={() => void refetch()} />}
          {data && filteredRows.length === 0 && <EmptyState title="No payment attempts" description="No payment attempts have been recorded for this mandate." />}
          {data && filteredRows.length > 0 && (
            <>
              <DataTable columns={columns} rows={filteredRows} getRowKey={attempt => attempt.id} onRowClick={setSelectedAttempt} />
              <Pagination offset={offset} limit={settings.tablePageSize} count={data.length} onPrevious={() => setOffset(value => Math.max(0, value - settings.tablePageSize))} onNext={() => setOffset(value => value + settings.tablePageSize)} />
            </>
          )}
        </div>
      )}
    </Modal>
  )
}

export function PaymentsPage() {
  const [selectedMandateId, setSelectedMandateId] = useState<string | null>(null)

  return (
    <motion.section className="page" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.28 }}>
      <PageHeader title="Payments" description="Inspect payment attempts and their outcomes for a specific mandate." />

      <MandatePicker onSelect={setSelectedMandateId} />

      <PaymentAttemptsModal mandateId={selectedMandateId} onClose={() => setSelectedMandateId(null)} />
    </motion.section>
  )
}
