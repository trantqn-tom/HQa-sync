import { useEffect, useMemo, useRef, useState } from 'react'
import { Filter, Search } from 'lucide-react'

export default function StatusHeaderFilter({ options = [], value = [], onChange }) {
  const rootRef = useRef(null)
  const triggerRef = useRef(null)
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [draft, setDraft] = useState(value)
  const [menuPos, setMenuPos] = useState({ top: 0, left: 0 })

  const allSelected = value.length === 0 || (options.length > 0 && value.length === options.length)
  const active = !allSelected

  const updateMenuPos = () => {
    const rect = triggerRef.current?.getBoundingClientRect()
    if (!rect) return
    setMenuPos({ top: rect.bottom + 6, left: rect.left })
  }

  useEffect(() => {
    if (!open) return
    setDraft(value.length ? value : [...options])
    setQuery('')
    updateMenuPos()
  }, [open, value, options])

  useEffect(() => {
    if (!open) return
    const onDoc = (e) => {
      if (rootRef.current && !rootRef.current.contains(e.target)) setOpen(false)
    }
    const onReposition = () => updateMenuPos()
    document.addEventListener('mousedown', onDoc)
    window.addEventListener('resize', onReposition)
    window.addEventListener('scroll', onReposition, true)
    return () => {
      document.removeEventListener('mousedown', onDoc)
      window.removeEventListener('resize', onReposition)
      window.removeEventListener('scroll', onReposition, true)
    }
  }, [open])

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return options
    return options.filter((item) => item.toLowerCase().includes(q))
  }, [options, query])

  const toggle = (item) => {
    setDraft((prev) => (prev.includes(item) ? prev.filter((x) => x !== item) : [...prev, item]))
  }

  const apply = () => {
    if (draft.length === 0 || draft.length === options.length) onChange([])
    else onChange(draft)
    setOpen(false)
  }

  return (
    <div className={`sheet-filter ${active ? 'is-active' : ''}`} ref={rootRef}>
      <button
        ref={triggerRef}
        type="button"
        className="sheet-filter-trigger"
        onClick={(e) => { e.stopPropagation(); setOpen((v) => !v) }}
      >
        <span>Status</span>
        <Filter size={14}/>
      </button>

      {open && (
        <div
          className="sheet-filter-menu"
          style={{ top: menuPos.top, left: menuPos.left }}
          onClick={(e) => e.stopPropagation()}
        >
          <div className="sheet-filter-actions">
            <button type="button" className="linkish" onClick={() => setDraft([...options])}>
              Select all {options.length}
            </button>
            <button type="button" className="linkish" onClick={() => setDraft([])}>Clear</button>
            <span className="sheet-filter-count">Displaying {filtered.length}</span>
          </div>

          <div className="sheet-filter-search">
            <Search size={14}/>
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search values"
              autoFocus
            />
          </div>

          <div className="sheet-filter-list">
            {filtered.map((item) => (
              <label key={item} className="sheet-filter-item">
                <input
                  type="checkbox"
                  checked={draft.includes(item)}
                  onChange={() => toggle(item)}
                />
                <span>{item}</span>
              </label>
            ))}
            {!filtered.length && <div className="sheet-filter-empty">Không có giá trị</div>}
          </div>

          <div className="sheet-filter-footer">
            <button type="button" className="sheet-btn cancel" onClick={() => setOpen(false)}>Cancel</button>
            <button type="button" className="sheet-btn ok" onClick={apply}>OK</button>
          </div>
        </div>
      )}
    </div>
  )
}
