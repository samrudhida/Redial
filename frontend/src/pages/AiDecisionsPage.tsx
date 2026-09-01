import { motion } from 'framer-motion'
import { Bot, Eye } from 'lucide-react'
import { useState } from 'react'
import { useDecisions } from '../hooks/useDecisions'
import { useSettings } from '../hooks/useSettings'
import type { DecisionLog } from '../types/decision'
import { ConfidenceMeter } from '../ui/ConfidenceMeter'
import { DataTable, type DataTableColumn } from '../ui/DataTable'
import { EmptyState } from '../ui/EmptyState'
import { Modal } from '../ui/Modal'
import { PageHeader } from '../ui/PageHeader'
import { Pagination } from '../ui/Pagination'
import { QueryError } from '../ui/QueryError'
import { SectionCard } from '../ui/SectionCard'
import { Skeleton } from '../ui/Skeleton'
import { StatusBadge } from '../ui/StatusBadge'
import { Timestamp } from '../ui/Timestamp'
import { truncateId } from '../utils/format'
import { decisionTypePresentation } from '../utils/statusPresentation'

function DecisionDetailModal({ decision, onClose }: { decision: DecisionLog | null; onClose: () => void }) {
  return (
    <Modal open={decision !== null} onClose={onClose} title="AI decision trace">
      {decision && (
        <div className="modal-body">
          <div className="form-row">
            <div className="form-field">
              <label>Mandate</label>
              <p className="cell-muted">{decision.mandate_id}</p>
            </div>
            <div className="form-field">
              <label>Recorded</label>
              <p><Timestamp iso={decision.created_at} /></p>
            </div>
          </div>
          <div className="form-row">
            <div className="form-field">
              <label>AI Decision</label>
              <p><StatusBadge {...decisionTypePresentation(decision.decision_type)} /></p>
            </div>
            <div className="form-field">
              <label>Confidence</label>
              <ConfidenceMeter score={decision.confidence_score} />
            </div>
          </div>
          <div className="form-field">
            <label>Reasoning</label>
            <div className="terminal-panel decision-trace">
              <div className="terminal-chrome"><Bot size={13} /><em>ai_service.reasoning</em></div>
              <p className="decision-trace-explanation">{decision.explanation}</p>
            </div>
          </div>
        </div>
      )}
    </Modal>
  )
}

export function AiDecisionsPage() {
  const { settings } = useSettings()
  const [offset, setOffset] = useState(0)
  const [selectedDecision, setSelectedDecision] = useState<DecisionLog | null>(null)

  const { data, isPending, isError, error, refetch } = useDecisions({ offset, limit: settings.tablePageSize })

  const columns: DataTableColumn<DecisionLog>[] = [
    { key: 'mandate_id', header: 'Mandate ID', render: decision => <span className="cell-muted" title={decision.mandate_id}>{truncateId(decision.mandate_id)}</span> },
    { key: 'decision_type', header: 'AI Decision', render: decision => <StatusBadge {...decisionTypePresentation(decision.decision_type)} /> },
    { key: 'confidence_score', header: 'Confidence', render: decision => <ConfidenceMeter score={decision.confidence_score} /> },
    { key: 'explanation', header: 'Reasoning', render: decision => <span className="wrap-cell" title={decision.explanation}>{decision.explanation}</span> },
    { key: 'created_at', header: 'Timestamp', render: decision => <Timestamp iso={decision.created_at} /> },
    {
      key: 'view',
      header: '',
      render: decision => (
        <button type="button" className="icon-button" aria-label="View decision details" onClick={event => { event.stopPropagation(); setSelectedDecision(decision) }}>
          <Eye size={15} />
        </button>
      ),
    },
  ]

  return (
    <motion.section className="page" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.28 }}>
      <PageHeader title="AI Decisions" description="Inspect the reasoning behind automated recommendations." />

      <SectionCard title="Decision log" className="data-panel" meta="Every AI decision recorded by the recovery workflow — click a row for full details">
        {isPending && <Skeleton style={{ height: 240 }} />}
        {isError && <QueryError message={error instanceof Error ? error.message : 'Failed to load AI decisions.'} onRetry={() => void refetch()} />}
        {data && data.length === 0 && <EmptyState icon={Bot} title="No decisions yet" description="AI decisions will appear here as retries are classified and scheduled." />}
        {data && data.length > 0 && (
          <>
            <DataTable columns={columns} rows={data} getRowKey={decision => decision.id} onRowClick={setSelectedDecision} selectedRowKey={selectedDecision?.id} />
            <Pagination offset={offset} limit={settings.tablePageSize} count={data.length} onPrevious={() => setOffset(value => Math.max(0, value - settings.tablePageSize))} onNext={() => setOffset(value => value + settings.tablePageSize)} />
          </>
        )}
      </SectionCard>

      <DecisionDetailModal decision={selectedDecision} onClose={() => setSelectedDecision(null)} />
    </motion.section>
  )
}
