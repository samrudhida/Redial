import { CircleDashed, type LucideIcon } from 'lucide-react'

/** Generic "nothing to show yet" placeholder, reusing the app's existing empty-state visual language. */
export function EmptyState({
  icon: Icon = CircleDashed,
  title,
  description,
  compact = false,
}: {
  icon?: LucideIcon
  title: string
  description: string
  compact?: boolean
}) {
  return (
    <div className={`empty-state ${compact ? 'empty-state-compact' : ''}`}>
      <div className="empty-icon"><Icon size={compact ? 18 : 24} strokeWidth={1.7} /></div>
      <div>
        <h2>{title}</h2>
        <p>{description}</p>
      </div>
    </div>
  )
}
