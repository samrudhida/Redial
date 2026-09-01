const currencyFormatter = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 2 })
const numberFormatter = new Intl.NumberFormat('en-IN')
const dateFormatter = new Intl.DateTimeFormat('en-IN', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })
const shortDateFormatter = new Intl.DateTimeFormat('en-IN', { day: 'numeric', month: 'short' })

/** Formats a Decimal-as-string amount (e.g. "500.00") as INR currency. */
export function formatCurrency(amount: string): string {
  const value = Number.parseFloat(amount)
  return Number.isFinite(value) ? currencyFormatter.format(value) : amount
}

/** Formats a Decimal-as-string confidence score in [0, 1] as a percentage string (e.g. "92%"). */
export function formatConfidencePercent(score: string): string {
  const value = Number.parseFloat(score)
  return Number.isFinite(value) ? `${Math.round(value * 100)}%` : score
}

export function formatCount(value: number): string {
  return numberFormatter.format(value)
}

/** Formats an ISO timestamp as a short relative time (e.g. "2 min ago"). */
export function formatRelativeTime(isoTimestamp: string): string {
  const then = new Date(isoTimestamp).getTime()
  if (Number.isNaN(then)) return isoTimestamp

  const diffSeconds = Math.round((then - Date.now()) / 1000)
  const divisions: Array<[Intl.RelativeTimeFormatUnit, number]> = [
    ['second', 60],
    ['minute', 60],
    ['hour', 24],
    ['day', 30],
    ['month', 12],
    ['year', Number.POSITIVE_INFINITY],
  ]

  const formatter = new Intl.RelativeTimeFormat('en', { numeric: 'auto' })
  let value = diffSeconds
  for (const [unit, amount] of divisions) {
    if (Math.abs(value) < amount) return formatter.format(Math.round(value), unit)
    value /= amount
  }
  return formatter.format(Math.round(value), 'year')
}

/** Formats an ISO timestamp as an absolute date + time (e.g. "25 Aug 2026, 12:37"). */
export function formatDate(isoTimestamp: string | null): string {
  if (isoTimestamp === null) return '—'
  const parsed = new Date(isoTimestamp)
  return Number.isNaN(parsed.getTime()) ? isoTimestamp : dateFormatter.format(parsed)
}

/** Formats an ISO date (e.g. "2026-08-20") as a short chart-axis label (e.g. "20 Aug"). */
export function formatShortDate(isoDate: string): string {
  const parsed = new Date(`${isoDate}T00:00:00`)
  return Number.isNaN(parsed.getTime()) ? isoDate : shortDateFormatter.format(parsed)
}

/** Shortens a UUID for compact display (e.g. "240a07e9…a817"). */
export function truncateId(id: string): string {
  return id.length <= 12 ? id : `${id.slice(0, 8)}…${id.slice(-4)}`
}

/** Truncates free text to roughly `maxLength` characters, breaking on a word boundary where possible. */
export function truncateText(text: string, maxLength = 140): string {
  if (text.length <= maxLength) return text
  const cut = text.slice(0, maxLength)
  const lastSpace = cut.lastIndexOf(' ')
  return `${lastSpace > maxLength * 0.6 ? cut.slice(0, lastSpace) : cut}...`
}

/** Formats a millisecond duration for display (e.g. "2.7 ms", "1.2 s"). */
export function formatDurationMs(ms: number | null): string {
  if (ms === null || !Number.isFinite(ms)) return '—'
  if (ms < 1000) return `${ms.toFixed(ms < 10 ? 2 : 1)} ms`
  return `${(ms / 1000).toFixed(2)} s`
}
