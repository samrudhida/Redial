import type { ReactNode } from 'react'

export interface DataTableColumn<T> {
  key: string
  header: string
  render: (row: T) => ReactNode
  sortable?: boolean
}

/**
 * Generic paginated-table renderer shared by every list page. Reuses the
 * exact table/th/td styling already established by the dashboard's decisions
 * table (see the `.data-panel` / `.decisions-panel` CSS rules) — no new
 * visual language introduced.
 */
export function DataTable<T>({
  columns,
  rows,
  getRowKey,
  sortKey,
  sortDirection,
  onSort,
  onRowClick,
  selectedRowKey,
}: {
  columns: DataTableColumn<T>[]
  rows: T[]
  getRowKey: (row: T) => string
  sortKey?: string
  sortDirection?: 'asc' | 'desc'
  onSort?: (key: string) => void
  /** When provided, rows become clickable (hover affordance + keyboard-accessible). */
  onRowClick?: (row: T) => void
  /** Row key to visually mark as selected (e.g. the row whose detail is currently open). */
  selectedRowKey?: string
}) {
  return (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            {columns.map(column => (
              <th
                key={column.key}
                className={column.sortable ? 'sortable-header' : undefined}
                onClick={column.sortable && onSort ? () => onSort(column.key) : undefined}
              >
                {column.header}
                {column.sortable && sortKey === column.key ? (sortDirection === 'asc' ? ' ▲' : ' ▼') : null}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map(row => {
            const rowKey = getRowKey(row)
            const isSelected = selectedRowKey !== undefined && rowKey === selectedRowKey
            const className = [onRowClick ? 'data-row-clickable' : null, isSelected ? 'data-row-selected' : null].filter(Boolean).join(' ') || undefined
            return (
              <tr
                key={rowKey}
                className={className}
                onClick={onRowClick ? () => onRowClick(row) : undefined}
                tabIndex={onRowClick ? 0 : undefined}
                role={onRowClick ? 'button' : undefined}
                onKeyDown={onRowClick ? event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); onRowClick(row) } } : undefined}
              >
                {columns.map(column => <td key={column.key}>{column.render(row)}</td>)}
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
