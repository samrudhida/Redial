export type BadgeTone = 'success' | 'warning' | 'danger' | 'neutral' | 'info'

/** Generic status pill — reuses the existing `.status-badge` visual language across all tones. */
export function StatusBadge({ label, tone }: { label: string; tone: BadgeTone }) {
  return <span className={`status-badge tone-${tone}`}>{label}</span>
}
