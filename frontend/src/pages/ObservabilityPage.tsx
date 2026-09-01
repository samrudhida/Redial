import { motion } from 'framer-motion'
import { Bot, CheckCircle2, GitBranch, ShieldCheck, XCircle } from 'lucide-react'
import { useState } from 'react'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import {
  useObservabilityMetrics,
  useObservabilityOverview,
  useProviderHealth,
  useWorkflowErrors,
  useWorkflowExecutionDetail,
  useWorkflowExecutions,
} from '../hooks/useObservability'
import { useSettings } from '../hooks/useSettings'
import type { WorkflowError, WorkflowExecutionSummary } from '../types/observability'
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
import { formatCount, formatDate, formatDurationMs, truncateId } from '../utils/format'
import { providerStatusPresentation, workflowExecutionStatusPresentation } from '../utils/statusPresentation'

/**
 * Honest framing of the real architecture: the deterministic policy always
 * decides retry/communication/escalation outcomes (see DecisionOrchestrator
 * — AI never overrides them). AI only adds confidence + reasoning on top,
 * when a provider is configured and the call succeeds. `ai_provider` is
 * null exactly when that enrichment didn't happen (decision_node.py only
 * sets a trace when ai_used is true), so it's a reliable, non-fabricated
 * signal for whether AI was actually involved in this run.
 */
function DecisionComparison({ execution, reasoning }: { execution: WorkflowExecutionSummary; reasoning: string | null }) {
  const aiEnriched = execution.ai_provider !== null
  return (
    <div className="decision-comparison">
      <div className="decision-comparison-col">
        <span className="decision-comparison-label"><ShieldCheck size={13} /> Deterministic policy</span>
        <strong>{execution.retry_decision ? `Retry ${execution.retry_decision}` : 'No retry recorded'}</strong>
        <p>Always authoritative — the recovery workflow completes on this alone if AI is unavailable.</p>
      </div>
      <div className="decision-comparison-col">
        <span className="decision-comparison-label"><Bot size={13} /> AI enrichment</span>
        {aiEnriched ? (
          <>
            <strong>{execution.ai_provider} · {execution.ai_model ?? 'unknown model'}</strong>
            {execution.confidence && <ConfidenceMeter score={execution.confidence} />}
          </>
        ) : (
          <>
            <strong className="cell-muted">Not used for this run</strong>
            <p>Deterministic policy ran alone — no provider was configured or available at the time.</p>
          </>
        )}
      </div>
      {aiEnriched && reasoning && (
        <div className="terminal-panel decision-trace decision-comparison-trace">
          <div className="terminal-chrome"><Bot size={13} /><em>ai_service.reasoning</em></div>
          <p className="decision-trace-explanation">{reasoning}</p>
        </div>
      )}
    </div>
  )
}

function WorkflowDetailModal({ executionId, onClose }: { executionId: string | null; onClose: () => void }) {
  const { data, isPending, isError, error, refetch } = useWorkflowExecutionDetail(executionId)

  return (
    <Modal open={executionId !== null} onClose={onClose} title="Workflow execution trace" size="wide">
      <div className="modal-body">
        {isPending && <Skeleton style={{ height: 200 }} />}
        {isError && <QueryError message={error instanceof Error ? error.message : 'Failed to load this execution.'} onRetry={() => void refetch()} />}
        {data && (
          <>
            <div className="form-row">
              <div className="form-field">
                <label>Mandate</label>
                <p>{truncateId(data.execution.mandate_id)}</p>
              </div>
              <div className="form-field">
                <label>Status</label>
                <p><StatusBadge {...workflowExecutionStatusPresentation(data.execution.status)} /></p>
              </div>
              <div className="form-field">
                <label>Total Duration</label>
                <p>{formatDurationMs(data.execution.duration_ms)}</p>
              </div>
            </div>

            <div className="form-field">
              <label><GitBranch size={12} /> Decision, at a glance</label>
              <DecisionComparison execution={data.execution} reasoning={data.reasoning} />
            </div>

            {data.error_message && (
              <div className="form-field">
                <label>Error{data.failed_node ? ` (at ${data.failed_node})` : ''}</label>
                <p>{data.error_message}</p>
              </div>
            )}

            <div className="form-field">
              <label>Step-by-step timeline</label>
              <div className="timeline execution-timeline">
                {data.nodes.map((node, index) => (
                  <motion.div
                    className="timeline-item"
                    key={node.node_name}
                    initial={{ opacity: 0, x: -8 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: index * 0.06, duration: 0.3 }}
                  >
                    <span className={`timeline-icon ${node.success ? 'green' : 'danger'}`}>
                      {node.success ? <CheckCircle2 size={14} /> : <XCircle size={14} />}
                    </span>
                    <div>
                      <strong>{node.node_name}</strong>
                      <p>{node.event} &middot; {formatDurationMs(node.duration_ms)}</p>
                      <small>{formatDate(node.finished_at)}</small>
                    </div>
                  </motion.div>
                ))}
              </div>
            </div>
          </>
        )}
      </div>
    </Modal>
  )
}

export function ObservabilityPage() {
  const { settings } = useSettings()
  const [offset, setOffset] = useState(0)
  const [selectedExecutionId, setSelectedExecutionId] = useState<string | null>(null)

  const overview = useObservabilityOverview()
  const workflows = useWorkflowExecutions({ offset, limit: settings.tablePageSize })
  const providers = useProviderHealth()
  const errors = useWorkflowErrors({ limit: 25 })
  const metrics = useObservabilityMetrics()

  const workflowColumns: DataTableColumn<WorkflowExecutionSummary>[] = [
    { key: 'workflow_id', header: 'Workflow ID', render: row => <span className="cell-muted">{truncateId(row.workflow_id)}</span> },
    { key: 'mandate_id', header: 'Mandate', render: row => <span className="cell-muted">{truncateId(row.mandate_id)}</span> },
    { key: 'status', header: 'Status', render: row => { const { label, tone } = workflowExecutionStatusPresentation(row.status); return <StatusBadge label={label} tone={tone} /> } },
    { key: 'duration_ms', header: 'Duration', render: row => formatDurationMs(row.duration_ms) },
    {
      key: 'confidence',
      header: 'Confidence',
      // ai_provider is null exactly when AI enrichment didn't happen (see
      // DecisionComparison above) — row.confidence is unreliable for this
      // check since the backend always sends it as "0.0000" (a truthy
      // string) for deterministic-only runs, not a falsy/empty value.
      render: row => row.ai_provider !== null ? <ConfidenceMeter score={row.confidence ?? '0'} /> : <span className="cell-muted">N/A</span>,
    },
    { key: 'ai_provider', header: 'Provider', render: row => <span className="cell-muted">{row.ai_provider ?? 'None'}</span> },
    { key: 'started_at', header: 'Timestamp', render: row => <span className="cell-muted">{formatDate(row.started_at)}</span> },
  ]

  const errorColumns: DataTableColumn<WorkflowError>[] = [
    { key: 'workflow_id', header: 'Workflow ID', render: row => <span className="cell-muted">{truncateId(row.workflow_id)}</span> },
    { key: 'mandate_id', header: 'Mandate', render: row => <span className="cell-muted">{truncateId(row.mandate_id)}</span> },
    { key: 'node', header: 'Node', render: row => row.node ?? 'Unknown' },
    { key: 'exception', header: 'Exception', render: row => <strong>{row.exception}</strong> },
    { key: 'timestamp', header: 'Timestamp', render: row => <span className="cell-muted">{formatDate(row.timestamp)}</span> },
  ]

  const latencyChartData = metrics.data
    ? [
        { name: 'Workflow', ms: Math.round(metrics.data.average_workflow_duration_ms * 100) / 100 },
        { name: 'Node (avg)', ms: Math.round(metrics.data.average_node_duration_ms * 100) / 100 },
        { name: 'Decision', ms: Math.round(metrics.data.decision_latency_ms * 100) / 100 },
        { name: 'Comms', ms: Math.round(metrics.data.communication_latency_ms * 100) / 100 },
        { name: 'Escalation', ms: Math.round(metrics.data.escalation_latency_ms * 100) / 100 },
        { name: 'AI', ms: Math.round(metrics.data.ai_latency_ms * 100) / 100 },
        { name: 'DB Persist', ms: Math.round(metrics.data.database_persistence_latency_ms * 100) / 100 },
      ]
    : []

  const executionCountData = overview.data
    ? [
        { name: 'Successful', count: overview.data.successful_workflows },
        { name: 'Failed', count: overview.data.failed_workflows },
      ]
    : []

  return (
    <motion.section className="page" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.28 }}>
      <PageHeader title="Observability" description="Monitor AI execution quality and workflow behavior." />

      <SectionCard title="Overview" meta="Real metrics from GET /observability/overview">
        {overview.isPending && <Skeleton style={{ height: 100 }} />}
        {overview.isError && <QueryError message={overview.error instanceof Error ? overview.error.message : 'Failed to load overview.'} onRetry={() => void overview.refetch()} />}
        {overview.data && (
          <div className="metric-grid">
            <div className="metric-tile"><span>Total Workflows</span><strong>{formatCount(overview.data.workflows_executed)}</strong></div>
            <div className="metric-tile"><span>Successful</span><strong>{formatCount(overview.data.successful_workflows)}</strong></div>
            <div className="metric-tile"><span>Failed</span><strong>{formatCount(overview.data.failed_workflows)}</strong></div>
            <div className="metric-tile"><span>Avg Execution Time</span><strong>{formatDurationMs(overview.data.average_execution_time_ms)}</strong></div>
            <div className="metric-tile"><span>Avg AI Latency</span><strong>{formatDurationMs(overview.data.average_ai_latency_ms)}</strong></div>
            <div className="metric-tile"><span>Avg Confidence</span><strong>{(overview.data.average_confidence * 100).toFixed(1)}%</strong></div>
          </div>
        )}
      </SectionCard>

      <SectionCard title="Workflow executions" className="data-panel" meta="Every real run of the recovery workflow graph — click a row for its full node timeline">
        {workflows.isPending && <Skeleton style={{ height: 240 }} />}
        {workflows.isError && <QueryError message={workflows.error instanceof Error ? workflows.error.message : 'Failed to load workflow executions.'} onRetry={() => void workflows.refetch()} />}
        {workflows.data && workflows.data.length === 0 && (
          <EmptyState icon={GitBranch} title="No workflow executions yet" description="Runs of the recovery workflow graph will appear here once mandates are processed through it." />
        )}
        {workflows.data && workflows.data.length > 0 && (
          <>
            <DataTable
              columns={workflowColumns}
              rows={workflows.data}
              getRowKey={row => row.id}
              onRowClick={row => setSelectedExecutionId(row.id)}
              selectedRowKey={selectedExecutionId ?? undefined}
            />
            <Pagination
              offset={offset}
              limit={settings.tablePageSize}
              count={workflows.data.length}
              onPrevious={() => setOffset(value => Math.max(0, value - settings.tablePageSize))}
              onNext={() => setOffset(value => value + settings.tablePageSize)}
            />
          </>
        )}
      </SectionCard>

      <SectionCard title="Provider health" meta="Real, configured AI provider — from GET /observability/provider">
        {providers.isPending && <Skeleton style={{ height: 120 }} />}
        {providers.isError && <QueryError message={providers.error instanceof Error ? providers.error.message : 'Failed to load provider health.'} onRetry={() => void providers.refetch()} />}
        {providers.data && (
          <div className="provider-grid">
            {providers.data.map(provider => {
              const { label, tone } = providerStatusPresentation(provider.status)
              return (
                <div className="provider-card" key={provider.provider}>
                  <div className="provider-card-head">
                    <div>
                      <strong>{provider.provider}</strong>
                      <small>{provider.model ?? 'No model configured'}</small>
                    </div>
                    <StatusBadge label={label} tone={tone} />
                  </div>
                  <div className="provider-stats">
                    <div><span>Requests Today</span><strong>{formatCount(provider.requests_today)}</strong></div>
                    <div><span>Failures</span><strong>{formatCount(provider.failures)}</strong></div>
                    <div><span>Avg Latency</span><strong>{formatDurationMs(provider.average_latency_ms)}</strong></div>
                    <div><span>Avg Confidence</span><strong>{(provider.average_confidence * 100).toFixed(1)}%</strong></div>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </SectionCard>

      <SectionCard title="Recent errors" className="data-panel" meta="Workflow failures — from GET /observability/errors">
        {errors.isPending && <Skeleton style={{ height: 160 }} />}
        {errors.isError && <QueryError message={errors.error instanceof Error ? errors.error.message : 'Failed to load errors.'} onRetry={() => void errors.refetch()} />}
        {errors.data && errors.data.length === 0 && <EmptyState compact title="No workflow errors" description="Every recorded workflow execution has completed successfully so far." />}
        {errors.data && errors.data.length > 0 && <DataTable columns={errorColumns} rows={errors.data} getRowKey={row => `${row.workflow_id}-${row.timestamp}`} />}
      </SectionCard>

      <SectionCard
        title="Performance metrics"
        meta="Current aggregate latencies from GET /observability/metrics — shown as a comparison, not a trend, since the backend only reports point-in-time aggregates"
      >
        {metrics.isPending && <Skeleton style={{ height: 240 }} />}
        {metrics.isError && <QueryError message={metrics.error instanceof Error ? metrics.error.message : 'Failed to load metrics.'} onRetry={() => void metrics.refetch()} />}
        {metrics.data && overview.data && (
          <div className="chart-grid">
            <div>
              <p className="panel-heading" style={{ margin: '0 0 8px' }}><span style={{ color: '#5b6b85', fontSize: 11 }}>Average latency by stage (ms)</span></p>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={latencyChartData} margin={{ top: 12, right: 8, left: -8, bottom: 0 }}>
                  <CartesianGrid vertical={false} stroke="#e7edf5" />
                  <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: '#8b99ab', fontSize: 10 }} />
                  <YAxis axisLine={false} tickLine={false} tick={{ fill: '#8b99ab', fontSize: 10 }} />
                  <Tooltip />
                  <Bar dataKey="ms" name="Latency (ms)" fill="#2563eb" radius={[4, 4, 0, 0]} barSize={28} />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div>
              <p className="panel-heading" style={{ margin: '0 0 8px' }}><span style={{ color: '#5b6b85', fontSize: 11 }}>Execution count by outcome</span></p>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={executionCountData} margin={{ top: 12, right: 8, left: -8, bottom: 0 }}>
                  <CartesianGrid vertical={false} stroke="#e7edf5" />
                  <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: '#8b99ab', fontSize: 10 }} />
                  <YAxis axisLine={false} tickLine={false} tick={{ fill: '#8b99ab', fontSize: 10 }} allowDecimals={false} />
                  <Tooltip />
                  <Bar dataKey="count" name="Executions" fill="#22c55e" radius={[4, 4, 0, 0]} barSize={40} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}
      </SectionCard>

      <WorkflowDetailModal executionId={selectedExecutionId} onClose={() => setSelectedExecutionId(null)} />
    </motion.section>
  )
}
