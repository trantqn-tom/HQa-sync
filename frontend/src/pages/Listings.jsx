import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, RefreshCw } from 'lucide-react'
import { api } from '../api/client'
import ActionDot from '../components/ActionDot'
import StatusHeaderFilter from '../components/StatusHeaderFilter'

export default function Listings() {
  const navigate = useNavigate()
  const [data, setData] = useState({ items: [], total: 0, pages: 0 })
  const [page, setPage] = useState(1)
  const [q, setQ] = useState('')
  const [selectedStatuses, setSelectedStatuses] = useState([])
  const [marketplace, setMarketplace] = useState('')
  const [action, setAction] = useState('')
  const [statuses, setStatuses] = useState([])
  const [marketplaces, setMarketplaces] = useState([])
  const [loading, setLoading] = useState(false)

  const loadMeta = async () => {
    try {
      const [statusRes, marketplaceRes] = await Promise.all([
        api.get('/listings/meta/statuses'),
        api.get('/listings/meta/marketplaces'),
      ])
      setStatuses(statusRes.data.statuses || [])
      setMarketplaces(marketplaceRes.data.marketplaces || [])
    } catch {
      setStatuses([])
      setMarketplaces([])
    }
  }

  const load = async () => {
    setLoading(true)
    try {
      const res = await api.get('/listings', {
        params: {
          page,
          page_size: 30,
          q: q || undefined,
          status: selectedStatuses.length ? selectedStatuses : undefined,
          marketplace: marketplace || undefined,
          action: action || undefined,
        },
        paramsSerializer: {
          indexes: null,
        },
      })
      setData(res.data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadMeta() }, [])
  useEffect(() => { load() }, [page, selectedStatuses, marketplace, action])

  return (
    <>
      <header className="page-header">
        <div>
          <h1>Listings</h1>
          <p>{data.total.toLocaleString()} bản ghi marketplace đã đồng bộ</p>
        </div>
        <button onClick={() => { loadMeta(); load() }}>
          <RefreshCw size={16}/>{loading ? 'Đang tải' : 'Làm mới'}
        </button>
      </header>

      <section className="toolbar">
        <div className="search">
          <Search size={17}/>
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && (setPage(1), load())}
            placeholder="Listing ID, tiêu đề, thương hiệu..."
          />
        </div>
        <select value={marketplace} onChange={(e) => (setMarketplace(e.target.value), setPage(1))}>
          <option value="">Tất cả marketplace</option>
          {marketplaces.map((item) => (
            <option key={item} value={item}>{item}</option>
          ))}
        </select>
        <select value={action} onChange={(e) => (setAction(e.target.value), setPage(1))}>
          <option value="">Tất cả thay đổi</option>
          <option value="INSERT">Thêm mới</option>
          <option value="UPDATE">Cập nhật</option>
          <option value="SKIP">Skip</option>
        </select>
      </section>

      <div className="table-card">
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Thay đổi</th>
                <th>Marketplace</th>
                <th>Sản phẩm</th>
                <th>Listing</th>
                <th>Giá</th>
                <th className="status-th">
                  <StatusHeaderFilter
                    options={statuses}
                    value={selectedStatuses}
                    onChange={(next) => { setSelectedStatuses(next); setPage(1) }}
                  />
                </th>
                <th>Seller</th>
                <th>Đồng bộ gần nhất</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((item) => (
                <tr key={item.id} onClick={() => navigate(`/listings/${item.id}`)}>
                  <td><ActionDot action={item.last_sync_action}/></td>
                  <td><span className="marketplace-pill">{item.marketplace || '-'}</span></td>
                  <td>
                    <strong>{item.brand} {item.model}</strong>
                    <small>{item.product_id}</small>
                  </td>
                  <td>
                    <div className="title-cell">
                      {item.image_url && <img src={item.image_url} alt=""/>}
                      <span>
                        {item.listing_title}
                        <small>{item.listing_id}</small>
                      </span>
                    </div>
                  </td>
                  <td>{item.total_price ? `${Number(item.total_price).toLocaleString()} ${item.currency || ''}` : '-'}</td>
                  <td><span className="status-pill">{item.listing_status || '-'}</span></td>
                  <td>{item.seller_or_shop || '-'}</td>
                  <td>
                    {item.last_seen_at
                      ? new Date(item.last_seen_at).toLocaleString('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh', hour12: false })
                      : '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="pagination">
        <button disabled={page <= 1} onClick={() => setPage(page - 1)}>Trước</button>
        <span>Trang {page}/{data.pages || 1}</span>
        <button disabled={page >= data.pages} onClick={() => setPage(page + 1)}>Sau</button>
      </div>
    </>
  )
}
