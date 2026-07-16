import { ChevronsLeft, ChevronsRight, ChevronLeft, ChevronRight } from 'lucide-react'

/** Build items like: 1 2 3 4 5 … 10 11 12 13 14 15 */
export function buildPageItems(current, total, edge = 5, sibling = 2) {
  const pages = Math.max(1, total || 1)
  const page = Math.min(Math.max(1, current || 1), pages)
  if (pages <= edge * 2) {
    return Array.from({ length: pages }, (_, i) => i + 1)
  }

  const set = new Set()
  for (let i = 1; i <= edge; i++) set.add(i)
  for (let i = pages - edge + 1; i <= pages; i++) set.add(i)
  for (let i = page - sibling; i <= page + sibling; i++) {
    if (i >= 1 && i <= pages) set.add(i)
  }

  const sorted = [...set].sort((a, b) => a - b)
  const items = []
  for (let i = 0; i < sorted.length; i++) {
    if (i > 0 && sorted[i] - sorted[i - 1] > 1) items.push('ellipsis')
    items.push(sorted[i])
  }
  return items
}

export default function Pagination({ page, pages, onChange }) {
  const total = Math.max(1, pages || 1)
  const current = Math.min(Math.max(1, page || 1), total)
  const items = buildPageItems(current, total)

  return (
    <div className="pagination">
      <button type="button" disabled={current <= 1} onClick={() => onChange(1)} title="Trang đầu">
        <ChevronsLeft size={16} />
      </button>
      <button type="button" disabled={current <= 1} onClick={() => onChange(current - 1)} title="Trước">
        <ChevronLeft size={16} />
      </button>

      {items.map((item, index) => (
        item === 'ellipsis'
          ? <span key={`e-${index}`} className="pagination-ellipsis">…</span>
          : (
            <button
              key={item}
              type="button"
              className={item === current ? 'active' : ''}
              onClick={() => onChange(item)}
            >
              {item}
            </button>
          )
      ))}

      <button type="button" disabled={current >= total} onClick={() => onChange(current + 1)} title="Sau">
        <ChevronRight size={16} />
      </button>
      <button type="button" disabled={current >= total} onClick={() => onChange(total)} title="Trang cuối">
        <ChevronsRight size={16} />
      </button>
    </div>
  )
}
