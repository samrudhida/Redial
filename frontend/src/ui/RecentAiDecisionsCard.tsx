import { ArrowUpRight, Bot, ChevronDown } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useDecisions } from '../hooks/useDecisions'
import type { DecisionLog } from '../types/decision'
import { formatConfidencePercent, formatRelativeTime } from '../utils/format'
import { decisionTypePresentation } from '../utils/statusPresentation'
import { EmptyState } from './EmptyState'
import { QueryError } from './QueryError'
import { SectionCard as Panel } from './SectionCard'
import { Skeleton } from './Skeleton'
import { StatusBadge } from './StatusBadge'

// AI-enriched explanations sometimes quote the raw enum token ("bank_unavailable")
// and sometimes spell it out in prose ("technical error") — match either form.
const DECLINE_CATEGORY_PATTERN = /\b(insufficient[ _]funds|bank[ _]unavailable|authentication[ _]required|mandate[ _]inactive|limit[ _]exceeded|account[ _]closed|technical[ _]error)\b/i

function humanizeToken(token: string): string {
  return token.replace(/_/g, ' ').replace(/\b\w/g, char => char.toUpperCase())
}

/**
 * DecisionLog has no separate "failure reason" field — it's embedded in the
 * explanation's prose. This pulls out the known decline-category token if
 * the explanation mentions one and pairs it with the decision's own type
 * label; falls back to just the type label when no category is mentioned
 * (e.g. escalations), rather than ever showing the raw mandate UUID.
 */
function decisionHeadline(decision: DecisionLog): string {
  const { label } = decisionTypePresentation(decision.decision_type)
  const match = decision.explanation.match(DECLINE_CATEGORY_PATTERN)
  return match ? `${humanizeToken(match[1])} → ${label}` : label
}

function confidenceBadgeTone(score: string): 'success' | 'warning' | 'danger' {
  const value = Number.parseFloat(score) * 100
  if (value >= 85) return 'success'
  if (value >= 60) return 'warning'
  return 'danger'
}

/**
 * Scannable, collapsed-by-default feed of the 5 most recent AI decisions,
 * for the dashboard's front page. Reuses the same data (useDecisions) and
 * decision-type presentation as the full AI Decisions page — this is a
 * compact preview of it, not a separate source of truth.
 */
export function RecentAiDecisionsCard({ highlight = false }: { highlight?: boolean }) {
  const { data, isPending, isError, error, refetch } = useDecisions({ limit: 5 })
  const [expandedId, setExpandedId] = useState<string | null>(null)

  return (
    <Panel
      id="recent-decisions"
      title="Recent AI decisions"
      meta="The AI's latest reasoning, live from the recovery workflow"
      className={`decisions-panel ${highlight ? 'panel-highlight' : ''}`}
    >
      {isPending && <Skeleton style={{ height: 180 }} />}
      {isError && (
        <QueryError message={error instanceof Error ? error.message : 'Failed to load AI decisions.'} onRetry={() => void refetch()} />
      )}
      {data && data.length === 0 && (
        <EmptyState compact icon={Bot} title="No AI decisions yet" description="Create a mandate to see the AI in action." />
      )}
      {data && data.length > 0 && (
        <div className="ai-decision-list">
          {data.map(decision => {
            const expanded = expandedId === decision.id
            return (
              <div className="ai-decision-row" key={decision.id}>
                <button
                  type="button"
                  className="ai-decision-summary"
                  aria-expanded={expanded}
                  onClick={() => setExpandedId(expanded ? null : decision.id)}
                >
                  <span className="ai-decision-headline">{decisionHeadline(decision)}</span>
                  <span className="ai-decision-meta">
                    <StatusBadge label={formatConfidencePercent(decision.confidence_score)} tone={confidenceBadgeTone(decision.confidence_score)} />
                    <small>{formatRelativeTime(decision.created_at)}</small>
                    <ChevronDown size={15} className={`ai-decision-chevron ${expanded ? 'expanded' : ''}`} />
                  </span>
                </button>
                <div className={`ai-decision-detail ${expanded ? 'expanded' : ''}`}>
                  <div className="ai-decision-detail-inner">
                    <p>{decision.explanation}</p>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
      <Link className="panel-link" to="/ai-decisions">View all decisions <ArrowUpRight size={14} /></Link>
    </Panel>
  )
}
