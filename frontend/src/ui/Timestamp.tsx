import { formatDate, formatRelativeTime } from '../utils/format'

/** Renders an absolute timestamp with the relative time as a hover tooltip. */
export function Timestamp({ iso }: { iso: string | null }) {
  if (iso === null) return <span className="cell-muted">—</span>
  return (
    <span className="cell-muted" title={formatRelativeTime(iso)}>
      {formatDate(iso)}
    </span>
  )
}
