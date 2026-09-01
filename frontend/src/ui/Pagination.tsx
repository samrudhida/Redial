import { ChevronLeft, ChevronRight } from 'lucide-react'

/**
 * Offset/limit pagination. None of the list endpoints this app calls return
 * a total count, so "has next page" is inferred from the fetched page being
 * exactly `limit` long — a full page might still be the last one, in which
 * case Next simply loads an empty page and re-disables itself.
 */
export function Pagination({
  offset,
  limit,
  count,
  onPrevious,
  onNext,
}: {
  offset: number
  limit: number
  count: number
  onPrevious: () => void
  onNext: () => void
}) {
  const rangeStart = count === 0 ? 0 : offset + 1
  const rangeEnd = offset + count

  return (
    <div className="pagination">
      <span className="pagination-range">{rangeStart}–{rangeEnd}</span>
      <button type="button" className="secondary-button" onClick={onPrevious} disabled={offset === 0}>
        <ChevronLeft size={14} />
        Previous
      </button>
      <button type="button" className="secondary-button" onClick={onNext} disabled={count < limit}>
        Next
        <ChevronRight size={14} />
      </button>
    </div>
  )
}
