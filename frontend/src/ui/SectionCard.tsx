import { MoreHorizontal } from 'lucide-react'
import type { ReactNode } from 'react'

/** Shared panel chrome (heading + meta + decorative "more" button) used across the app. */
export function SectionCard({
  title,
  meta,
  children,
  className = '',
  id,
}: {
  title: string
  meta?: string
  children: ReactNode
  className?: string
  id?: string
}) {
  return (
    <section id={id} className={`dash-panel ${className}`}>
      <div className="panel-heading">
        <div>
          <h2>{title}</h2>
          {meta && <p>{meta}</p>}
        </div>
        <button className="more-button" aria-label={`More ${title}`}><MoreHorizontal size={19} /></button>
      </div>
      {children}
    </section>
  )
}
