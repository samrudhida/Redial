import { AlertTriangle, RotateCcw } from 'lucide-react'

/** Generic inline error state for a failed query, with a retry action. */
export function QueryError({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="query-error" role="alert">
      <span className="query-error-icon"><AlertTriangle size={18} /></span>
      <div>
        <strong>Couldn't load this data</strong>
        <p>{message}</p>
      </div>
      <button type="button" className="secondary-button query-error-retry" onClick={onRetry}>
        <RotateCcw size={14} />
        Retry
      </button>
    </div>
  )
}
