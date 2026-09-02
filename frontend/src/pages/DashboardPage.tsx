import { useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { Activity, ArrowUpRight, Bot, ClipboardList, CreditCard, Gauge, MessageSquare, Play, Plus, Radio, Sparkles, Timer, Zap } from 'lucide-react'
import { useState } from 'react'
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Link, useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { useDashboardActivity, useDashboardSummary, useDashboardTrend } from '../hooks/useDashboard'
import { useRunWorkflows } from '../hooks/useRunWorkflows'
import { CreateMandateModal } from '../ui/CreateMandateModal'
import { EmptyState } from '../ui/EmptyState'
import { QueryError } from '../ui/QueryError'
import { RecentAiDecisionsCard } from '../ui/RecentAiDecisionsCard'
import { SectionCard as Panel } from '../ui/SectionCard'
import { Skeleton } from '../ui/Skeleton'
import type { DashboardSummary } from '../types/dashboard'
import type { PaymentStatus } from '../types/enums'
import { extractErrorMessage } from '../utils/apiError'
import { formatCount, formatCurrency, formatRelativeTime, formatShortDate, truncateId } from '../utils/format'

const CHART_AXIS_TICK = { fill: 'var(--text-muted)', fontSize: 10 }
const CHART_TOOLTIP_STYLE = { background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 12, color: 'var(--text)' }

/** Fixed display order/labels/colors for payment outcome slices, independent of API key order. */
const PAYMENT_STATUS_PRESENTATION: Array<{ status: PaymentStatus; label: string; color: string }> = [
  { status: 'succeeded', label: 'Succeeded', color: '#4ade80' },
  { status: 'retry_scheduled', label: 'Retry scheduled', color: '#818cf8' },
  { status: 'processing', label: 'Processing', color: '#2dd4bf' },
  { status: 'pending', label: 'Pending', color: '#a1a1aa' },
  { status: 'failed', label: 'Failed', color: '#f87171' },
]

function KpiCardSkeleton() {
  return (
    <div className="kpi-card">
      <div className="kpi-top"><Skeleton style={{ width: 90, height: 11 }} /></div>
      <Skeleton style={{ width: 70, height: 27, margin: '14px 0 9px' }} />
      <Skeleton style={{ width: 110, height: 10 }} />
    </div>
  )
}

function DashboardSkeleton() {
  return (
    <>
      <div className="kpi-grid">
        {Array.from({ length: 4 }, (_, index) => <KpiCardSkeleton key={index} />)}
      </div>
      <Panel title="Loading" className="decisions-panel standalone-panel">
        <Skeleton style={{ height: 180 }} />
      </Panel>
      <div className="chart-grid">
        {Array.from({ length: 2 }, (_, index) => (
          <Panel key={index} title="Loading">
            <Skeleton style={{ height: 218 }} />
          </Panel>
        ))}
      </div>
      <Panel title="Loading" className="standalone-panel">
        <Skeleton style={{ height: 180 }} />
      </Panel>
      <div className="bottom-grid">
        <Panel title="Loading">
          <Skeleton style={{ height: 140 }} />
        </Panel>
        <Panel title="Loading">
          <Skeleton style={{ height: 140 }} />
        </Panel>
      </div>
    </>
  )
}

export function DashboardPage() {
  const { data, isPending, isError, error, isFetching, refetch } = useDashboardSummary(10)
  const [isCreateMandateOpen, setIsCreateMandateOpen] = useState(false)
  const [highlightDecisions, setHighlightDecisions] = useState(false)
  const runWorkflows = useRunWorkflows()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  // "Live view" refreshes the whole page's data, not just the KPI summary —
  // otherwise the charts and Recent activity feed would silently sit on
  // stale data for up to a full poll interval after the user asked to refresh.
  function handleLiveViewClick() {
    void queryClient.invalidateQueries({ queryKey: ['dashboard'] })
  }

  function handleRunWorkflows() {
    runWorkflows.mutate(10, {
      onSuccess: result => {
        if (result.attempted === 0) {
          toast('No mandates to process', { description: 'There are no mandates for the workflow engine to run right now.' })
          return
        }
        toast.success('AI workflow run complete', {
          description: `Processed ${formatCount(result.attempted)} mandate${result.attempted === 1 ? '' : 's'} — ${formatCount(result.succeeded)} succeeded${result.failed > 0 ? `, ${formatCount(result.failed)} failed` : ''}. Results are below, in Recent AI decisions.`,
          action: { label: 'View all', onClick: () => navigate('/ai-decisions') },
        })
        // Scroll the panel that actually shows the new results into view and
        // briefly highlight it, so "where did it go" isn't a mystery.
        document.getElementById('recent-decisions')?.scrollIntoView({ behavior: 'smooth', block: 'center' })
        setHighlightDecisions(true)
        setTimeout(() => setHighlightDecisions(false), 2000)
      },
      onError: error => {
        toast.error('Could not run the AI workflow', {
          description: extractErrorMessage(error, 'This endpoint is only available when the backend is running in development mode.'),
        })
      },
    })
  }

  return (
    <motion.section className="dashboard-page" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.35 }}>
      <div className="dashboard-heading">
        <div>
          <div className="breadcrumb"><Link to="/dashboard">Workspace</Link><span>/</span><span>Dashboard</span></div>
          <p className="eyebrow">Recovery operations</p>
          <p className="dashboard-subtitle">
            Here's what's happening across your recovery operations today.
            {isFetching && !isPending && <span className="live-indicator"><span className="live-dot" />Syncing</span>}
          </p>
        </div>
        <div className="dashboard-actions">
          <button className="secondary-button" onClick={handleLiveViewClick} disabled={isFetching}>
            <Radio size={15} />
            {isFetching ? 'Refreshing...' : 'Live view'}
          </button>
          <button className="secondary-button" onClick={handleRunWorkflows} disabled={runWorkflows.isPending}>
            {runWorkflows.isPending
              ? <span className="thinking-pulse"><span /><span /><span /></span>
              : <Sparkles size={15} />}
            {runWorkflows.isPending ? 'AI is thinking...' : 'Run AI Workflow'}
          </button>
          <button className="primary-button" onClick={() => setIsCreateMandateOpen(true)}><Plus size={16} />Create mandate</button>
        </div>
      </div>

      {isPending && <DashboardSkeleton />}

      {isError && (
        <QueryError
          message={error instanceof Error ? error.message : 'Failed to load the dashboard summary.'}
          onRetry={() => void refetch()}
        />
      )}

      {data && <DashboardContent summary={data} onCreateMandate={() => setIsCreateMandateOpen(true)} highlightDecisions={highlightDecisions} />}

      <CreateMandateModal open={isCreateMandateOpen} onClose={() => setIsCreateMandateOpen(false)} />
    </motion.section>
  )
}

function RecentActivityPanel() {
  const activity = useDashboardActivity(15)

  return (
    <Panel title="Recent activity" meta="A live feed of workflow events">
      {activity.isPending && <Skeleton style={{ height: 140 }} />}
      {activity.isError && (
        <QueryError message={activity.error instanceof Error ? activity.error.message : 'Failed to load recent activity.'} onRetry={() => void activity.refetch()} />
      )}
      {activity.data && activity.data.length === 0 && (
        <EmptyState compact icon={Activity} title="No activity yet" description="Decisions and communications will appear here as retries are processed." />
      )}
      {activity.data && activity.data.length > 0 && (
        <div className="timeline">
          {activity.data.map(event => (
            <div className="timeline-item" key={`${event.event_type}-${event.mandate_id}-${event.timestamp}`}>
              <span className={`timeline-icon ${event.event_type === 'communication' ? 'violet' : 'green'}`}>
                {event.event_type === 'communication' ? <MessageSquare size={14} /> : <Bot size={14} />}
              </span>
              <div>
                <strong>{truncateId(event.mandate_id)} &middot; {event.event_type === 'communication' ? 'Communication sent' : 'AI decision'}</strong>
                <p>{event.description}</p>
                <small>{formatRelativeTime(event.timestamp)}</small>
              </div>
            </div>
          ))}
        </div>
      )}
    </Panel>
  )
}

function DashboardContent({ summary, onCreateMandate, highlightDecisions }: { summary: DashboardSummary; onCreateMandate: () => void; highlightDecisions: boolean }) {
  const totalMandates = Object.values(summary.mandate_counts_by_status).reduce((sum, count) => sum + (count ?? 0), 0)
  const activeMandates = summary.mandate_counts_by_status.active ?? 0
  const succeededAttempts = summary.payment_attempt_counts_by_status.succeeded ?? 0
  const failedAttempts = summary.payment_attempt_counts_by_status.failed ?? 0
  const decidedAttempts = succeededAttempts + failedAttempts
  const recoveryRate = decidedAttempts > 0 ? (succeededAttempts / decidedAttempts) * 100 : 0
  const totalAttempts = Object.values(summary.payment_attempt_counts_by_status).reduce((sum, count) => sum + (count ?? 0), 0)

  const kpis = [
    {
      label: 'Total mandates',
      value: formatCount(totalMandates),
      note: 'across all statuses',
      icon: CreditCard,
      tone: 'blue',
      progress: 100,
    },
    {
      label: 'Active mandates',
      value: formatCount(activeMandates),
      note: 'currently active',
      icon: Activity,
      tone: 'green',
      progress: totalMandates > 0 ? (activeMandates / totalMandates) * 100 : 0,
    },
    {
      label: 'Pending retries',
      value: formatCount(summary.pending_retries),
      note: 'awaiting processing',
      icon: Timer,
      tone: 'amber',
      progress: totalMandates > 0 ? Math.min(100, (summary.pending_retries / totalMandates) * 100) : 0,
    },
    {
      label: 'Recovery rate',
      value: `${recoveryRate.toFixed(1)}%`,
      note: `${formatCurrency(summary.revenue_recovered)} recovered`,
      icon: Gauge,
      tone: 'violet',
      progress: recoveryRate,
    },
  ] as const

  const outcomeSlices = PAYMENT_STATUS_PRESENTATION.map(entry => ({
    ...entry,
    count: summary.payment_attempt_counts_by_status[entry.status] ?? 0,
    percent: totalAttempts > 0 ? Math.round(((summary.payment_attempt_counts_by_status[entry.status] ?? 0) / totalAttempts) * 100) : 0,
  }))

  const trend = useDashboardTrend(14)
  const hasTrendActivity = trend.data?.some(point => point.attempts_total > 0) ?? false
  const trendSeries = (trend.data ?? []).map(point => {
    const decided = point.attempts_succeeded + point.attempts_failed
    const collected = Number.parseFloat(point.collected_amount)
    const recovered = Number.parseFloat(point.recovered_amount)
    return {
      date: formatShortDate(point.day),
      // null (not 0) when nothing is decided/collected yet — a day with no
      // resolved attempts isn't a 0% day, it's a day with no data yet, and
      // plotting it as a hard 0% is indistinguishable from a real all-failed day.
      successRate: decided > 0 ? Math.round((point.attempts_succeeded / decided) * 100) : null,
      collected,
      recoveryPercent: collected > 0 ? Math.round((recovered / collected) * 100) : null,
    }
  })

  return (
    <>
      <div className="kpi-grid">
        {kpis.map((kpi, index) => (
          <motion.div
            className={`kpi-card ${kpi.tone}`}
            key={kpi.label}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.07 }}
            whileHover={{ y: -3 }}
          >
            <div className="kpi-top"><span>{kpi.label}</span><span className="kpi-icon"><kpi.icon size={17} /></span></div>
            <strong>{kpi.value}</strong>
            <div className="kpi-foot"><small>{kpi.note}</small></div>
            <div className="progress-track">
              <motion.div initial={{ width: 0 }} animate={{ width: `${kpi.progress}%` }} transition={{ delay: 0.25 + index * 0.07, duration: 0.7 }} />
            </div>
          </motion.div>
        ))}
      </div>

      <div className="standalone-panel">
        <RecentAiDecisionsCard highlight={highlightDecisions} />
      </div>

      <div className="chart-grid">
        <Panel title="Retry success trend" meta="Real payment outcomes over the last 14 days">
          {trend.isPending && <Skeleton style={{ height: 188 }} />}
          {trend.isError && <QueryError message={trend.error instanceof Error ? trend.error.message : 'Failed to load the trend.'} onRetry={() => void trend.refetch()} />}
          {trend.data && !hasTrendActivity && <EmptyState compact title="No attempts in this window" description="Payment attempts recorded in the last 14 days will chart here." />}
          {trend.data && hasTrendActivity && (
            <ResponsiveContainer width="100%" height={188}>
              <LineChart data={trendSeries} margin={{ top: 8, right: 8, left: -22, bottom: 0 }}>
                <CartesianGrid vertical={false} stroke="var(--border)" />
                <XAxis dataKey="date" axisLine={false} tickLine={false} tick={CHART_AXIS_TICK} />
                <YAxis axisLine={false} tickLine={false} tick={CHART_AXIS_TICK} unit="%" domain={[0, 100]} />
                <Tooltip contentStyle={CHART_TOOLTIP_STYLE} formatter={value => [value === null ? 'No decided attempts' : `${value}%`, 'Success rate']} />
                {/* A visible dot per point, not just a connecting line — a real point
                    isolated between two null (no-data) days would otherwise have no
                    line segment reaching it and render as literally invisible. */}
                <Line type="monotone" dataKey="successRate" stroke="var(--accent)" strokeWidth={2} dot={{ r: 3, fill: 'var(--accent)', strokeWidth: 0 }} connectNulls={false} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </Panel>
        <Panel title="Daily collections" meta="Real revenue collected over the last 14 days">
          {trend.isPending && <Skeleton style={{ height: 188 }} />}
          {trend.isError && <QueryError message={trend.error instanceof Error ? trend.error.message : 'Failed to load the trend.'} onRetry={() => void trend.refetch()} />}
          {trend.data && !hasTrendActivity && <EmptyState compact title="No collections in this window" description="Revenue from succeeded payment attempts will chart here." />}
          {trend.data && hasTrendActivity && (
            <ResponsiveContainer width="100%" height={188}>
              <AreaChart data={trendSeries} margin={{ top: 8, right: 8, left: -14, bottom: 0 }}>
                <defs>
                  <linearGradient id="collectedFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="var(--accent)" stopOpacity={0.35} />
                    <stop offset="100%" stopColor="var(--accent)" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid vertical={false} stroke="var(--border)" />
                <XAxis dataKey="date" axisLine={false} tickLine={false} tick={CHART_AXIS_TICK} />
                <YAxis axisLine={false} tickLine={false} tick={CHART_AXIS_TICK} />
                <Tooltip contentStyle={CHART_TOOLTIP_STYLE} formatter={value => [formatCurrency(Number(value).toFixed(2)), 'Collected']} />
                <Area type="monotone" dataKey="collected" stroke="var(--accent)" strokeWidth={2} fill="url(#collectedFill)" />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </Panel>
        <Panel title="Payment attempt outcomes" meta="Current outcome distribution across all attempts">
          {totalAttempts === 0 ? (
            <EmptyState compact title="No payment attempts yet" description="Outcomes will appear here once payments have been attempted." />
          ) : (
            <div className="pie-wrap">
              <ResponsiveContainer width="57%" height={188}>
                <PieChart>
                  <Pie data={outcomeSlices} dataKey="count" nameKey="label" innerRadius={57} outerRadius={79} paddingAngle={3} stroke="none">
                    {outcomeSlices.map(slice => <Cell key={slice.status} fill={slice.color} />)}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
              <div className="pie-center"><strong>{recoveryRate.toFixed(1)}%</strong><span>recovered</span></div>
              <div className="pie-legend">
                {outcomeSlices.map(slice => <span key={slice.status}><i style={{ background: slice.color }} />{slice.label}<b>{slice.percent}%</b></span>)}
              </div>
            </div>
          )}
        </Panel>
        <Panel title="Recovery percentage" meta="Share of each day's revenue that came from a retry">
          {trend.isPending && <Skeleton style={{ height: 188 }} />}
          {trend.isError && <QueryError message={trend.error instanceof Error ? trend.error.message : 'Failed to load the trend.'} onRetry={() => void trend.refetch()} />}
          {trend.data && !hasTrendActivity && <EmptyState compact title="No collections in this window" description="How much of each day's revenue came from a retry will chart here." />}
          {trend.data && hasTrendActivity && (
            <ResponsiveContainer width="100%" height={188}>
              <BarChart data={trendSeries} margin={{ top: 8, right: 8, left: -22, bottom: 0 }}>
                <CartesianGrid vertical={false} stroke="var(--border)" />
                <XAxis dataKey="date" axisLine={false} tickLine={false} tick={CHART_AXIS_TICK} />
                <YAxis axisLine={false} tickLine={false} tick={CHART_AXIS_TICK} unit="%" domain={[0, 100]} />
                <Tooltip contentStyle={CHART_TOOLTIP_STYLE} formatter={value => [value === null ? 'No revenue collected' : `${value}%`, 'From a retry']} />
                <Bar dataKey="recoveryPercent" fill="var(--teal)" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </Panel>
      </div>

      <Panel title="Retry queue" meta="Pending recovery attempts" className="standalone-panel">
        {summary.pending_retries === 0 ? (
          <EmptyState compact icon={ClipboardList} title="No pending retries" description="The retry queue is empty right now." />
        ) : (
          <EmptyState
            compact
            icon={ClipboardList}
            title={`${formatCount(summary.pending_retries)} pending ${summary.pending_retries === 1 ? 'retry' : 'retries'}`}
            description="Open the Retry Queue page for the full itemized schedule."
          />
        )}
        <Link className="panel-link" to="/retry-queue">Open retry queue <ArrowUpRight size={14} /></Link>
      </Panel>

      <div className="bottom-grid">
        <RecentActivityPanel />
        <Panel title="Quick actions" meta="Common operations">
          <div className="quick-actions">
            <button type="button" onClick={onCreateMandate}><span className="quick-icon blue"><Plus size={17} /></span><strong>Create mandate</strong><small>Add a new payment mandate</small><ArrowUpRight size={15} /></button>
            <Link to="/retry-queue"><span className="quick-icon amber"><Play size={16} /></span><strong>Run retry</strong><small>Process pending attempts</small><ArrowUpRight size={15} /></Link>
            <Link to="/analytics"><span className="quick-icon green"><Zap size={16} /></span><strong>Analytics</strong><small>Explore recovery performance</small><ArrowUpRight size={15} /></Link>
            <Link to="/observability"><span className="quick-icon violet"><Radio size={16} /></span><strong>Observability</strong><small>Inspect AI system health</small><ArrowUpRight size={15} /></Link>
          </div>
        </Panel>
      </div>
    </>
  )
}
