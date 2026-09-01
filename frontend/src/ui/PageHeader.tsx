import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'

/** Shared breadcrumb + title + description header, used by every routed page. */
export function PageHeader({
  title,
  description,
  actions,
}: {
  title: string
  description: string
  actions?: ReactNode
}) {
  return (
    <>
      <div className="breadcrumb"><Link to="/dashboard">Workspace</Link><span>/</span><span>{title}</span></div>
      <div className="page-heading">
        <div>
          <p className="eyebrow">Redial workspace</p>
          <h1>{title}</h1>
          <p className="page-description">{description}</p>
        </div>
        {actions}
      </div>
    </>
  )
}
