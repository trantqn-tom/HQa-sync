import { useMemo, useState } from "react";
import { Download, FileSpreadsheet, X } from "lucide-react";

import {
  exportListingsToExcel,
  exportListingsToGoogleSheet,
  previewGoogleSheet,
} from "../api/exportApi";

const EXPORT_COLUMNS = [
  {
    key: "marketplace",
    label: "Marketplace",
  },
  {
    key: "listing_id",
    label: "Listing ID",
  },
  {
    key: "product_id",
    label: "Product ID",
  },
  {
    key: "keyword",
    label: "Keyword",
  },
  {
    key: "brand",
    label: "Brand",
  },
  {
    key: "model",
    label: "Model",
  },
  {
    key: "category_name",
    label: "Category",
  },
  {
    key: "listing_title",
    label: "Listing title",
  },
  {
    key: "listing_url",
    label: "Listing URL",
  },
  {
    key: "seller_or_shop",
    label: "Seller / Shop",
  },
  {
    key: "price",
    label: "Price",
  },
  {
    key: "shipping_price",
    label: "Shipping price",
  },
  {
    key: "total_price",
    label: "Total price",
  },
  {
    key: "currency",
    label: "Currency",
  },
  {
    key: "listing_status",
    label: "Status",
  },
  {
    key: "condition",
    label: "Condition",
  },
  {
    key: "location",
    label: "Location",
  },
  {
    key: "quantity",
    label: "Quantity",
  },
  {
    key: "last_sync_action",
    label: "Sync action",
  },
  {
    key: "last_seen_at",
    label: "Last seen",
  },
];

const DEFAULT_COLUMNS = EXPORT_COLUMNS.map((item) => item.key);

export default function ExportModal({
  open,
  onClose,
  filters,
  page,
  pageSize = 30,
}) {
  const [exportType, setExportType] = useState("EXCEL");

  const [scope, setScope] = useState("FILTERED");

  const [selectedColumns, setSelectedColumns] = useState(DEFAULT_COLUMNS);

  const [spreadsheetUrl, setSpreadsheetUrl] = useState("");

  const [targetTabName, setTargetTabName] = useState("");

  const [writeMode, setWriteMode] = useState("NEW_TAB");

  const [preview, setPreview] = useState(null);

  const [loadingPreview, setLoadingPreview] = useState(false);

  const [exporting, setExporting] = useState(false);

  const [error, setError] = useState("");

  const [success, setSuccess] = useState("");

  const payloadFilters = useMemo(
    () => ({
      q: filters?.q || null,

      statuses: filters?.statuses || [],

      marketplaces: filters?.marketplaces || [],

      sellers: filters?.sellers || [],

      action: filters?.action || null,

      product_id: filters?.product_id || null,

      brand: filters?.brand || null,

      category_name: filters?.category_name || null,

      condition: filters?.condition || null,

      price_min: filters?.price_min ?? null,

      price_max: filters?.price_max ?? null,
    }),
    [filters],
  );

  if (!open) {
    return null;
  }

  const toggleColumn = (columnKey) => {
    setSelectedColumns((current) => {
      if (current.includes(columnKey)) {
        return current.filter((item) => item !== columnKey);
      }

      return [...current, columnKey];
    });
  };

  const selectAllColumns = () => {
    setSelectedColumns(EXPORT_COLUMNS.map((item) => item.key));
  };

  const clearColumns = () => {
    setSelectedColumns([]);
  };

  const handlePreviewGoogleSheet = async () => {
    setError("");
    setSuccess("");
    setPreview(null);

    if (!spreadsheetUrl.trim()) {
      setError("Vui lòng nhập Google Sheet URL");
      return;
    }

    setLoadingPreview(true);

    try {
      const result = await previewGoogleSheet(spreadsheetUrl.trim());

      setPreview(result);
    } catch (previewError) {
      setError(previewError.message);
    } finally {
      setLoadingPreview(false);
    }
  };

  const buildCommonPayload = () => ({
    scope,

    filters: payloadFilters,

    columns: selectedColumns,

    sort: {
      field: "last_seen_at",
      order: "desc",
    },

    page,
    page_size: pageSize,
  });

  const handleExport = async () => {
    setError("");
    setSuccess("");

    if (selectedColumns.length === 0) {
      setError("Vui lòng chọn ít nhất một cột export");
      return;
    }

    if (exportType === "GOOGLE_SHEET" && !spreadsheetUrl.trim()) {
      setError("Vui lòng nhập Google Sheet URL");
      return;
    }

    setExporting(true);

    try {
      if (exportType === "EXCEL") {
        const result = await exportListingsToExcel({
          ...buildCommonPayload(),

          filename: null,
        });

        setSuccess(
          result.exportedRows
            ? `Đã export ${Number(result.exportedRows).toLocaleString()} dòng`
            : "Export Excel thành công",
        );
      } else {
        const result = await exportListingsToGoogleSheet({
          ...buildCommonPayload(),

          spreadsheet_url: spreadsheetUrl.trim(),

          target_tab_name: targetTabName.trim() || null,

          write_mode: writeMode,
        });

        setSuccess(
          `Đã export ${Number(result.exported_rows).toLocaleString()} dòng`,
        );

        if (result.output_url) {
          window.open(result.output_url, "_blank", "noopener,noreferrer");
        }
      }
    } catch (exportError) {
      setError(exportError.message);
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="export-modal-backdrop" onMouseDown={onClose}>
      <div
        className="export-modal"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="export-modal-header">
          <div>
            <h2>Export dữ liệu</h2>
            <p>Xuất danh sách theo bộ lọc hiện tại</p>
          </div>

          <button
            type="button"
            className="icon-button"
            onClick={onClose}
            aria-label="Đóng"
          >
            <X size={20} />
          </button>
        </div>

        <div className="export-modal-body">
          <section className="export-section">
            <h3>1. Chọn định dạng</h3>

            <div className="export-type-grid">
              <button
                type="button"
                className={
                  exportType === "EXCEL"
                    ? "export-type-card active"
                    : "export-type-card"
                }
                onClick={() => setExportType("EXCEL")}
              >
                <Download size={22} />

                <span>
                  <strong>Excel</strong>
                  <small>Tải file .xlsx về máy</small>
                </span>
              </button>

              <button
                type="button"
                className={
                  exportType === "GOOGLE_SHEET"
                    ? "export-type-card active"
                    : "export-type-card"
                }
                onClick={() => setExportType("GOOGLE_SHEET")}
              >
                <FileSpreadsheet size={22} />

                <span>
                  <strong>Google Sheet</strong>
                  <small>Ghi vào file được chỉ định</small>
                </span>
              </button>
            </div>
          </section>

          <section className="export-section">
            <h3>2. Phạm vi export</h3>

            <label className="export-radio">
              <input
                type="radio"
                name="export-scope"
                value="FILTERED"
                checked={scope === "FILTERED"}
                onChange={(event) => setScope(event.target.value)}
              />

              <span>
                <strong>Toàn bộ kết quả sau lọc</strong>

                <small>
                  Export tất cả bản ghi phù hợp với search, marketplace, status,
                  seller và action hiện tại.
                </small>
              </span>
            </label>

            <label className="export-radio">
              <input
                type="radio"
                name="export-scope"
                value="CURRENT_PAGE"
                checked={scope === "CURRENT_PAGE"}
                onChange={(event) => setScope(event.target.value)}
              />

              <span>
                <strong>Chỉ trang hiện tại</strong>

                <small>Export tối đa {pageSize} bản ghi đang hiển thị.</small>
              </span>
            </label>
          </section>

          <section className="export-section">
            <div className="export-section-title">
              <h3>3. Chọn cột</h3>

              <div>
                <button
                  type="button"
                  className="text-button"
                  onClick={selectAllColumns}
                >
                  Chọn tất cả
                </button>

                <button
                  type="button"
                  className="text-button"
                  onClick={clearColumns}
                >
                  Bỏ chọn
                </button>
              </div>
            </div>

            <div className="export-columns-grid">
              {EXPORT_COLUMNS.map((column) => (
                <label key={column.key} className="export-checkbox">
                  <input
                    type="checkbox"
                    checked={selectedColumns.includes(column.key)}
                    onChange={() => toggleColumn(column.key)}
                  />

                  <span>{column.label}</span>
                </label>
              ))}
            </div>
          </section>

          {exportType === "GOOGLE_SHEET" && (
            <section className="export-section">
              <h3>4. Google Sheet đích</h3>

              <label className="export-field">
                <span>Google Sheet URL</span>

                <input
                  value={spreadsheetUrl}
                  onChange={(event) => {
                    setSpreadsheetUrl(event.target.value);
                    setPreview(null);
                  }}
                  placeholder="https://docs.google.com/spreadsheets/d/..."
                />
              </label>

              <div className="export-inline-fields">
                <label className="export-field">
                  <span>Tên tab</span>

                  <input
                    value={targetTabName}
                    onChange={(event) => setTargetTabName(event.target.value)}
                    placeholder="Marketplace Export"
                  />
                </label>

                <label className="export-field">
                  <span>Chế độ ghi</span>

                  <select
                    value={writeMode}
                    onChange={(event) => setWriteMode(event.target.value)}
                  >
                    <option value="NEW_TAB">Tạo tab mới</option>

                    <option value="OVERWRITE">Ghi đè tab hiện tại</option>

                    <option value="APPEND">Ghi nối tiếp</option>
                  </select>
                </label>
              </div>

              <button
                type="button"
                className="secondary-button"
                onClick={handlePreviewGoogleSheet}
                disabled={loadingPreview}
              >
                {loadingPreview ? "Đang kiểm tra..." : "Kiểm tra Google Sheet"}
              </button>

              {preview && (
                <div className="sheet-preview">
                  <strong>{preview.spreadsheet_title}</strong>

                  <p>{preview.tabs?.length || 0} tab được tìm thấy</p>

                  <div className="sheet-tab-list">
                    {preview.tabs?.map((tab) => (
                      <button
                        key={tab.sheet_id}
                        type="button"
                        onClick={() => {
                          setTargetTabName(tab.title);

                          if (writeMode === "NEW_TAB") {
                            setWriteMode("OVERWRITE");
                          }
                        }}
                      >
                        {tab.title}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </section>
          )}

          {error && <div className="export-message error">{error}</div>}

          {success && <div className="export-message success">{success}</div>}
        </div>

        <div className="export-modal-footer">
          <button
            type="button"
            className="ghost"
            onClick={onClose}
            disabled={exporting}
          >
            Hủy
          </button>

          <button
            className="secondary-button"
            type="button"
            onClick={handleExport}
            disabled={exporting || selectedColumns.length === 0}
          >
            {exporting
              ? "Đang export..."
              : exportType === "EXCEL"
                ? "Tải file Excel"
                : "Export Google Sheet"}
          </button>
        </div>
      </div>
    </div>
  );
}
