import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, ExternalLink, ImageOff } from 'lucide-react'
import { api } from '../api/client'
import ActionDot from '../components/ActionDot'

const FIELD_LABELS = {
  product_id: 'Product ID',
  brand: 'Thương hiệu',
  model: 'Model',
  category_name: 'Tên category',
  keyword: 'Keyword',
  condition: 'Condition',
  quantity: 'Số lượng',
  location: 'Location',
  raw_confidence: 'Confidence',
  buying_options: 'Buying options',
  listing_location: 'Listing location',
}

const fmtTime = (v) => {
  if (!v) return '-'
  const d = new Date(v)
  if (Number.isNaN(d.getTime())) return String(v)
  return d.toLocaleString('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh', hour12: false })
}

const fmtValue = (key, value) => {
  if (value === null || value === undefined || value === '') return '-'
  if (typeof value === 'boolean') return value ? 'true' : 'false'
  if (key === 'raw_confidence') {
    const n = Number(value)
    return Number.isFinite(n) ? n.toLocaleString('vi-VN') : String(value)
  }
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

const labelOf = (key) => FIELD_LABELS[key] || key.replaceAll('_', ' ')

const formatMarketplace = (value) => {
  if (!value) return 'Marketplace'
  return String(value)
    .replace(/[_-]+/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())
}

const pickRaw = (raw, keys) => {
  for (const key of keys) {
    if (raw[key] !== undefined && raw[key] !== null && raw[key] !== '') return raw[key]
  }
  const lowerMap = Object.fromEntries(
    Object.entries(raw || {}).map(([k, v]) => [String(k).toLowerCase().replace(/\s+/g, '_'), v]),
  )
  for (const key of keys) {
    const normalized = String(key).toLowerCase().replace(/\s+/g, '_')
    if (lowerMap[normalized] !== undefined && lowerMap[normalized] !== null && lowerMap[normalized] !== '') {
      return lowerMap[normalized]
    }
  }
  return null
}

function AttrTable({ title, columns, values }) {
  return (
    <div className="detail-section">
      <h2>{title}</h2>
      <div className="table-card attr-table">
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                {columns.map((col) => (
                  <th key={col.key}>{col.label}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              <tr className="no-pointer">
                {columns.map((col) => (
                  <td key={col.key} className="wrap-cell" title={fmtValue(col.key, values[col.key])}>
                    {fmtValue(col.key, values[col.key])}
                  </td>
                ))}
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

export default function ListingDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let alive = true
    setLoading(true)
    setError('')
    api.get(`/listings/${id}`)
      .then((res) => { if (alive) setData(res.data) })
      .catch((err) => { if (alive) setError(err?.response?.data?.detail || 'Không tải được chi tiết') })
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [id])

  const listing = data?.listing
  const rawPayload = data?.raw_payload || {}
  const history = data?.history || []

  const detailValues = useMemo(() => {
    if (!listing) return {}
    return {
      brand: listing.brand,
      model: listing.model,
      category_name: listing.category_name,
      condition: listing.condition,
      quantity: listing.quantity,
      listing_location: pickRaw(rawPayload, [
        'listing_location', 'listing location', 'listingLocation', 'Listing location',
      ]),
    }
  }, [listing, rawPayload])

  const productColumns = [
    { key: 'brand', label: 'Thương hiệu' },
    { key: 'model', label: 'Model' },
    { key: 'category_name', label: 'Tên category' },
    { key: 'condition', label: 'Condition' },
    { key: 'quantity', label: 'Số lượng' },
    { key: 'listing_location', label: 'Listing location' },
  ]

  const historyRows = useMemo(() => {
    const rows = []
    for (const item of history) {
      const fields = item.changed_fields || {}
      const entries = Object.entries(fields)
      if (!entries.length) {
        rows.push({
          id: `${item.id}-empty`,
          created_at: item.created_at,
          change_type: item.change_type,
          field: '-',
          oldValue: '-',
          newValue: '-',
        })
        continue
      }
      for (const [field, diff] of entries) {
        rows.push({
          id: `${item.id}-${field}`,
          created_at: item.created_at,
          change_type: item.change_type,
          field,
          oldValue: diff?.old,
          newValue: diff?.new,
        })
      }
    }
    return rows
  }, [history])

  if (loading) {
    return <div className="detail-page"><p className="muted">Đang tải chi tiết listing...</p></div>
  }

  if (error || !listing) {
    return (
      <div className="detail-page">
        <button className="ghost-btn" onClick={() => navigate('/')}><ArrowLeft size={16}/> Quay lại</button>
        <p className="error-text">{error || 'Không tìm thấy listing'}</p>
      </div>
    )
  }

  const priceText = listing.total_price != null
    ? `${Number(listing.total_price).toLocaleString('vi-VN')} ${listing.currency || ''}`.trim()
    : '-'
  const marketplaceName = formatMarketplace(listing.marketplace)

  return (
    <div className="detail-page">
      <div className="detail-topbar">
        <button className="ghost-btn" onClick={() => navigate('/')}><ArrowLeft size={16}/> Quay lại danh sách</button>
      </div>

      <section className="detail-hero">
        <div className="detail-image">
          {listing.image_url
            ? <img src={listing.image_url} alt={listing.listing_title || listing.listing_id} />
            : <div className="image-fallback"><ImageOff size={28}/> Không có ảnh</div>}
        </div>
        <div className="detail-hero-body">
          <div className="detail-hero-meta">
            <span className="marketplace-pill">{marketplaceName}</span>
            <span className="status-pill">{listing.listing_status || '-'}</span>
            <ActionDot action={listing.last_sync_action} />
          </div>
          <h1>{listing.listing_title || '(Không có tiêu đề)'}</h1>
          <p className="detail-sub">{[listing.brand, listing.model].filter(Boolean).join(' ') || listing.product_id || '—'}</p>

          <div className="detail-highlights">
            <div className="highlight-card"><span>Marketplace</span><strong>{marketplaceName}</strong></div>
            <div className="highlight-card"><span>Listing ID</span><strong>{listing.listing_id || '-'}</strong></div>
            <div className="highlight-card"><span>Giá</span><strong>{priceText}</strong></div>
            <div className="highlight-card"><span>Seller</span><strong>{listing.seller_or_shop || '-'}</strong></div>
            <div className="highlight-card"><span>Đồng bộ gần nhất</span><strong>{fmtTime(listing.last_seen_at)}</strong></div>
          </div>

          {listing.listing_url
            ? <a className="listing-link" href={listing.listing_url} target="_blank" rel="noreferrer">
                Mở trên {marketplaceName} <ExternalLink size={16}/>
              </a>
            : <span className="muted">Không có link listing</span>}
        </div>
      </section>

      <AttrTable title="Thông tin sản phẩm" columns={productColumns} values={detailValues} />

      <section className="detail-section">
        <h2>Lịch sử trạng thái / thay đổi</h2>
        <div className="table-card history-table">
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Thời gian</th>
                  <th>Action</th>
                  <th>Trường</th>
                  <th>Giá trị cũ</th>
                  <th>Giá trị mới</th>
                </tr>
              </thead>
              <tbody>
                {historyRows.length === 0 && (
                  <tr className="no-pointer"><td colSpan={5}>Chưa có lịch sử thay đổi</td></tr>
                )}
                {historyRows.map((row) => (
                  <tr key={row.id} className="no-pointer">
                    <td>{fmtTime(row.created_at)}</td>
                    <td><ActionDot action={row.change_type} /></td>
                    <td>{labelOf(row.field)}</td>
                    <td className="wrap-cell">{fmtValue(row.field, row.oldValue)}</td>
                    <td className="wrap-cell">{fmtValue(row.field, row.newValue)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </div>
  )
}
