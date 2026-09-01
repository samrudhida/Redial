import type { CSSProperties } from 'react'

/** Generic shimmering placeholder block, sized via className/style by the caller. */
export function Skeleton({ className = '', style }: { className?: string; style?: CSSProperties }) {
  return <div className={`skeleton-block ${className}`} style={style} aria-hidden="true" />
}
