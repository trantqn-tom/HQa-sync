import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Download, RefreshCw, Search } from "lucide-react";
import { api } from "../api/client";
import ActionDot from "../components/ActionDot";
import StatusHeaderFilter from "../components/StatusHeaderFilter";
import Pagination from "../components/Pagination";
import ExportModal from "../components/ExportModal";

export default function Listings() {
  const navigate = useNavigate();
  const [data, setData] = useState({ items: [], total: 0, pages: 0 });
  const [page, setPage] = useState(1);
  const [q, setQ] = useState("");
  const [appliedQ, setAppliedQ] = useState("");
  const [selectedStatuses, setSelectedStatuses] = useState([]);
  const [selectedMarketplaces, setSelectedMarketplaces] = useState([]);
  const [selectedSellers, setSelectedSellers] = useState([]);
  const [action, setAction] = useState("");
  const [statuses, setStatuses] = useState([]);
  const [marketplaces, setMarketplaces] = useState([]);
  const [sellers, setSellers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [exportOpen, setExportOpen] = useState(false);
  const loadMeta = async () => {
    try {
      const [statusRes, marketplaceRes, sellerRes] = await Promise.all([
        api.get("/listings/meta/statuses"),
        api.get("/listings/meta/marketplaces"),
        api.get("/listings/meta/sellers"),
      ]);

      setStatuses(statusRes.data.statuses || []);

      setMarketplaces(marketplaceRes.data.marketplaces || []);

      setSellers(sellerRes.data.sellers || []);
    } catch {
      setStatuses([]);
      setMarketplaces([]);
      setSellers([]);
    }
  };

  const load = async () => {
    setLoading(true);
    try {
      const res = await api.get("/listings", {
        params: {
          page,
          page_size: 30,
          q: appliedQ || undefined,
          status: selectedStatuses.length ? selectedStatuses : undefined,

          marketplace: selectedMarketplaces.length
            ? selectedMarketplaces
            : undefined,

          seller: selectedSellers.length ? selectedSellers : undefined,

          action: action || undefined,
        },
        paramsSerializer: {
          indexes: null,
        },
      });
      setData(res.data);
    } finally {
      setLoading(false);
    }
  };

  const applySearch = () => {
    setPage(1);
    setAppliedQ(q.trim());
  };

  const resetToFirst = (updater) => {
    setPage(1);
    updater();
  };

  useEffect(() => {
    loadMeta();
  }, []);
  useEffect(() => {
    load();
  }, [
    page,
    appliedQ,
    selectedStatuses,
    selectedMarketplaces,
    selectedSellers,
    action,
  ]);

  return (
    <>
      <header className="page-header">
        <div>
          <h1>Listings</h1>
          <p>{data.total.toLocaleString()} bản ghi marketplace đã đồng bộ</p>
        </div>
        <div className="page-header-actions">
          <button
            type="button"
            className="ghost"
            onClick={() => {
              loadMeta();
              load();
            }}
            disabled={loading}
          >
            <RefreshCw size={16} />

            {loading ? "Đang tải" : "Làm mới"}
          </button>

          <button
            type="button"
            onClick={() => setExportOpen(true)}
            disabled={loading || data.total === 0}
          >
            <Download size={16} />
            Export
          </button>
        </div>
      </header>

      <section className="toolbar">
        <div className="search">
          <Search size={17} />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && applySearch()}
            placeholder="Listing ID, tiêu đề, thương hiệu..."
          />
        </div>

        <select
          value={action}
          onChange={(e) => resetToFirst(() => setAction(e.target.value))}
        >
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
                <th className="filter-th">
                  <StatusHeaderFilter
                    label="Marketplace"
                    options={marketplaces}
                    value={selectedMarketplaces}
                    searchPlaceholder="Tìm marketplace"
                    onChange={(next) =>
                      resetToFirst(() => setSelectedMarketplaces(next))
                    }
                  />
                </th>
                <th>Sản phẩm</th>
                <th>Listing</th>
                <th>Giá</th>
                <th className="filter-th">
                  <StatusHeaderFilter
                    label="Status"
                    options={statuses}
                    value={selectedStatuses}
                    searchPlaceholder="Tìm status"
                    onChange={(next) =>
                      resetToFirst(() => setSelectedStatuses(next))
                    }
                  />
                </th>
                <th className="filter-th">
                  <StatusHeaderFilter
                    label="Seller"
                    options={sellers}
                    value={selectedSellers}
                    searchPlaceholder="Tìm seller / shop"
                    onChange={(next) =>
                      resetToFirst(() => setSelectedSellers(next))
                    }
                  />
                </th>
                <th>Đồng bộ gần nhất</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((item) => (
                <tr
                  key={item.id}
                  onClick={() => navigate(`/listings/${item.id}`)}
                >
                  <td>
                    <ActionDot action={item.last_sync_action} />
                  </td>
                  <td>
                    <span className="marketplace-pill">
                      {item.marketplace || "-"}
                    </span>
                  </td>
                  <td>
                    <strong>
                      {item.brand} {item.model}
                    </strong>
                    <small>{item.product_id}</small>
                  </td>
                  <td>
                    <div className="title-cell">
                      {item.image_url && <img src={item.image_url} alt="" />}
                      <span>
                        {item.listing_title}
                        <small>{item.listing_id}</small>
                      </span>
                    </div>
                  </td>
                  <td>
                    {item.total_price
                      ? `${Number(item.total_price).toLocaleString()} ${item.currency || ""}`
                      : "-"}
                  </td>
                  <td>
                    <span className="status-pill">
                      {item.listing_status || "-"}
                    </span>
                  </td>
                  <td>{item.seller_or_shop || "-"}</td>
                  <td>
                    {item.last_seen_at
                      ? new Date(item.last_seen_at).toLocaleString("vi-VN", {
                          timeZone: "Asia/Ho_Chi_Minh",
                          hour12: false,
                        })
                      : "-"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <Pagination page={page} pages={data.pages || 1} onChange={setPage} />
      <ExportModal
        open={exportOpen}
        onClose={() => setExportOpen(false)}
        page={page}
        pageSize={30}
        filters={{
          q: appliedQ,

          statuses: selectedStatuses,

          marketplaces: selectedMarketplaces,

          sellers: selectedSellers,
          action: action || null,

          product_id: null,
          brand: null,
          category_name: null,
          condition: null,
          price_min: null,
          price_max: null,
        }}
      />
    </>
  );
}
