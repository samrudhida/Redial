import { motion } from 'framer-motion'
import { Area, AreaChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { useDashboardSummary, useDashboardTrend } from '../hooks/useDashboard'
import { EmptyState } from '../ui/EmptyState'
import { PageHeader } from '../ui/PageHeader'
import { QueryError } from '../ui/QueryError'
import { SectionCard } from '../ui/SectionCard'
import { Skeleton } from '../ui/Skeleton'
import { formatCount, formatCurrency, formatShortDate } from '../utils/format'
import { mandateStatusPresentation, paymentStatusPresentation } from '../utils/statusPresentation'
import type { MandateStatus, PaymentStatus } from '../types/enums'

const MANDATE_STATUSES: MandateStatus[] = ['active', 'paused', 'cancelled', 'expired', 'completed']
const PAYMENT_STATUSES: PaymentStatus[] = ['pending', 'processing', 'succeeded', 'failed', 'retry_scheduled']

const CHART_AXIS_TICK = { fill: 'var(--text-muted)', fontSize: 10 }
const CHART_TOOLTIP_STYLE = { background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 12, color: 'var(--text)' }

function TrendAnalyticsSection() {
  const trend = useDashboardTrend(30)
  const hasTrendActivity = trend.data?.some(point => point.attempts_total > 0) ?? false
  const trendSeries = (trend.data ?? []).map(point => {
    const decided = point.attempts_succeeded + point.attempts_failed
    return {
      date: formatShortDate(point.day),
      successRate: decided > 0 ? Math.round((point.attempts_succeeded / decided) * 100) : null,
      collected: Number.parseFloat(point.collected_amount),
    }
  })

  return (
    <SectionCard title="Trend analytics" meta="Real per-day payment outcomes from GET /dashboard/trend — last 30 days">
      {trend.isPending && <Skeleton style={{ height: 240 }} />}
      {trend.isError && <QueryError message={trend.error instanceof Error ? trend.error.message : 'Failed to load the trend.'} onRetry={() => void trend.refetch()} />}
      {trend.data && !hasTrendActivity && (
        <EmptyState title="No attempts in this window" description="Payment attempts recorded in the last 30 days will chart here." />
      )}
      {trend.data && hasTrendActivity && (
        <div className="chart-grid">
          <div>
            <p className="panel-heading" style={{ margin: '0 0 8px' }}><span style={{ color: 'var(--text-muted)', fontSize: 11 }}>Success rate (%) — days with no decided attempts yet are gapped, not shown as 0%</span></p>
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={trendSeries} margin={{ top: 12, right: 8, left: -8, bottom: 0 }}>
                <CartesianGrid vertical={false} stroke="var(--border)" />
                <XAxis dataKey="date" axisLine={false} tickLine={false} tick={CHART_AXIS_TICK} />
                <YAxis axisLine={false} tickLine={false} tick={CHART_AXIS_TICK} unit="%" domain={[0, 100]} />
                <Tooltip contentStyle={CHART_TOOLTIP_STYLE} formatter={value => [value === null ? 'No decided attempts' : `${value}%`, 'Success rate']} />
                {/* A visible dot per point — an isolated real value between two
                    null (no-data) days would otherwise have no line segment
                    reaching it and render as invisible. */}
                <Line type="monotone" dataKey="successRate" stroke="var(--accent)" strokeWidth={2} dot={{ r: 3, fill: 'var(--accent)', strokeWidth: 0 }} connectNulls={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <div>
            <p className="panel-heading" style={{ margin: '0 0 8px' }}><span style={{ color: 'var(--text-muted)', fontSize: 11 }}>Collected revenue</span></p>
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={trendSeries} margin={{ top: 12, right: 8, left: -8, bottom: 0 }}>
                <defs>
                  <linearGradient id="analyticsCollectedFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="var(--accent)" stopOpacity={0.35} />
                    <stop offset="100%" stopColor="var(--accent)" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid vertical={false} stroke="var(--border)" />
                <XAxis dataKey="date" axisLine={false} tickLine={false} tick={CHART_AXIS_TICK} />
                <YAxis axisLine={false} tickLine={false} tick={CHART_AXIS_TICK} />
                <Tooltip contentStyle={CHART_TOOLTIP_STYLE} formatter={value => [formatCurrency(Number(value).toFixed(2)), 'Collected']} />
                <Area type="monotone" dataKey="collected" stroke="var(--accent)" strokeWidth={2} fill="url(#analyticsCollectedFill)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </SectionCard>
  )
}

export function AnalyticsPage() {
  const { data, isPending, isError, error, refetch } = useDashboardSummary()

  return (
    <motion.section className="page" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.28 }}>
      <PageHeader title="Analytics" description="Understand recovery performance over time." />

      {isPending && <Skeleton style={{ height: 300 }} />}
      {isError && <QueryError message={error instanceof Error ? error.message : 'Failed to load analytics data.'} onRetry={() => void refetch()} />}

      {data && (
        <>
          <SectionCard title="Mandates by status" meta="Current snapshot from GET /dashboard/summary">
            <div className="metric-grid">
              {MANDATE_STATUSES.map(status => (
                <div className="metric-tile" key={status}>
                  <span>{mandateStatusPresentation(status).label}</span>
                  <strong>{formatCount(data.mandate_counts_by_status[status] ?? 0)}</strong>
                </div>
              ))}
            </div>
          </SectionCard>

          <SectionCard title="Payment attempts by outcome" meta="Current snapshot from GET /dashboard/summary">
            <div className="metric-grid">
              {PAYMENT_STATUSES.map(status => (
                <div className="metric-tile" key={status}>
                  <span>{paymentStatusPresentation(status).label}</span>
                  <strong>{formatCount(data.payment_attempt_counts_by_status[status] ?? 0)}</strong>
                </div>
              ))}
            </div>
          </SectionCard>

          <SectionCard title="Recovery" meta="Current snapshot from GET /dashboard/summary">
            <div className="metric-grid">
              <div className="metric-tile"><span>Revenue Recovered</span><strong>{formatCurrency(data.revenue_recovered)}</strong></div>
              <div className="metric-tile"><span>Pending Retries</span><strong>{formatCount(data.pending_retries)}</strong></div>
              <div className="metric-tile"><span>Open Escalations</span><strong>{formatCount(data.open_escalations)}</strong></div>
            </div>
          </SectionCard>

          <TrendAnalyticsSection />
        </>
      )}
    </motion.section>
  )
}
