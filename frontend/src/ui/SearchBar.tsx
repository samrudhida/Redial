import { Search } from 'lucide-react'

export function SearchBar({
  value,
  onChange,
  placeholder,
}: {
  value: string
  onChange: (value: string) => void
  placeholder: string
}) {
  return (
    <label className="filter-search">
      <Search size={14} />
      <input type="text" value={value} onChange={event => onChange(event.target.value)} placeholder={placeholder} />
    </label>
  )
}
