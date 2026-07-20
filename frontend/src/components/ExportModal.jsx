import { useEffect, useMemo, useState } from "react";

import { Download, FileSpreadsheet, FileText, X } from "lucide-react";

import {
  exportListingsToExcel,
  exportListingsToGoogleSheet,
  exportListingsToPdf,
  getExportColumns,
  previewGoogleSheet,
} from "../api/exportApi";

export default function ExportModal({
  open,
  onClose,
  filters,
  page,
  pageSize = 30,
}) {
  const [exportType, setExportType] = useState("EXCEL");
  const [scope, setScope] = useState("FILTERED");

  const [columnOptions, setColumnOptions] = useState([]);
  const [selectedColumns, setSelectedColumns] = useState([]);
  const [loadingColumns, setLoadingColumns] = useState(false);
  const [columnSearch, setColumnSearch] = useState("");

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

  const visibleColumnOptions = useMemo(() => {
    const query = columnSearch.trim().toLowerCase();

    if (!query) {
      return columnOptions;
    }

    return columnOptions.filter((column) =>
      String(column?.label || "")
        .toLowerCase()
        .includes(query),
    );
  }, [columnOptions, columnSearch]);

  useEffect(() => {
    if (!open) {
      return undefined;
    }

    let active = true;

    const loadColumns = async () => {
      setLoadingColumns(true);
      setError("");
      setSuccess("");

      try {
        const result = await getExportColumns();

        if (!active) {
          return;
        }

        const columns = Array.isArray(result?.columns) ? result.columns : [];
        const defaultColumns = Array.isArray(result?.default_columns)
          ? result.default_columns
          : [];

        setColumnOptions(columns);
        setSelectedColumns(defaultColumns);
      } catch (loadError) {
        if (active) {
          setColumnOptions([]);
          setSelectedColumns([]);
          setError(
            loadError?.message || "Không thể tải danh sách trường export.",
          );
        }
      } finally {
        if (active) {
          setLoadingColumns(false);
        }
      }
    };

    loadColumns();

    return () => {
      active = false;
    };
  }, [open]);

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
    setSelectedColumns(
      columnOptions.map((column) => column?.key).filter(Boolean),
    );
  };

  const selectAllSourceColumns = () => {
    setSelectedColumns(
      columnOptions
        .filter((column) => column?.source === "google_sheet")
        .map((column) => column?.key)
        .filter(Boolean),
    );
  };

  const clearColumns = () => {
    setSelectedColumns([]);
  };

  const handlePreviewGoogleSheet = async () => {
    setError("");
    setSuccess("");
    setPreview(null);

    if (!spreadsheetUrl.trim()) {
      setError("Vui lòng nhập Google Sheet URL.");
      return;
    }

    setLoadingPreview(true);

    try {
      const result = await previewGoogleSheet(spreadsheetUrl.trim());
      setPreview(result);
    } catch (previewError) {
      setError(previewError?.message || "Không thể kiểm tra Google Sheet.");
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
      setError("Vui lòng chọn ít nhất một trường để export.");
      return;
    }

    if (exportType === "GOOGLE_SHEET" && !spreadsheetUrl.trim()) {
      setError("Vui lòng nhập Google Sheet URL.");
      return;
    }

    setExporting(true);

    try {
      const commonPayload = buildCommonPayload();

      if (exportType === "EXCEL") {
        const result = await exportListingsToExcel({
          ...commonPayload,
          filename: null,
        });

        const exportedRows = Number(result?.exportedRows || 0);

        setSuccess(
          exportedRows > 0
            ? `Đã xuất Excel ${exportedRows.toLocaleString("vi-VN")} dòng.`
            : "Xuất file Excel thành công.",
        );

        return;
      }

      if (exportType === "PDF") {
        const result = await exportListingsToPdf({
          ...commonPayload,
          title: "Báo cáo Marketplace Listings",
          filename: null,
        });

        const exportedRows = Number(result?.exportedRows || 0);

        setSuccess(
          exportedRows > 0
            ? `Đã xuất PDF ${exportedRows.toLocaleString("vi-VN")} dòng.`
            : "Xuất file PDF thành công.",
        );

        return;
      }

      if (exportType === "GOOGLE_SHEET") {
        const result = await exportListingsToGoogleSheet({
          ...commonPayload,
          spreadsheet_url: spreadsheetUrl.trim(),
          target_tab_name: targetTabName.trim() || null,
          write_mode: writeMode,
        });

        const exportedRows = Number(result?.exported_rows || 0);

        setSuccess(
          exportedRows > 0
            ? `Đã xuất Google Sheet ${exportedRows.toLocaleString(
                "vi-VN",
              )} dòng.`
            : "Xuất Google Sheet thành công.",
        );

        if (result?.output_url) {
          window.open(result.output_url, "_blank", "noopener,noreferrer");
        }

        return;
      }

      throw new Error(`Định dạng export không được hỗ trợ: ${exportType}`);
    } catch (exportError) {
      console.error("Export listings error:", exportError);

      setError(
        exportError?.message || "Không thể export dữ liệu. Vui lòng thử lại.",
      );
    } finally {
      setExporting(false);
    }
  };

  const exportButtonLabel = exporting
    ? "Đang export..."
    : exportType === "EXCEL"
      ? "Tải file Excel"
      : exportType === "PDF"
        ? "Tải file PDF"
        : "Export Google Sheet";

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

              <button
                type="button"
                className={
                  exportType === "PDF"
                    ? "export-type-card active"
                    : "export-type-card"
                }
                onClick={() => setExportType("PDF")}
              >
                <FileText size={22} />

                <span>
                  <strong>PDF</strong>
                  <small>Xuất kết quả thành file PDF</small>
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
              <h3>3. Chọn trường xuất</h3>

              <div>
                <button
                  type="button"
                  className="text-button"
                  onClick={selectAllSourceColumns}
                  disabled={loadingColumns}
                >
                  Chọn trường Google Sheet
                </button>

                <button
                  type="button"
                  className="text-button"
                  onClick={selectAllColumns}
                  disabled={loadingColumns}
                >
                  Chọn tất cả
                </button>

                <button
                  type="button"
                  className="text-button"
                  onClick={clearColumns}
                  disabled={loadingColumns}
                >
                  Bỏ chọn
                </button>
              </div>
            </div>

            <label className="export-field">
              <span>Tìm trường</span>

              <input
                className="mb-[12px]"
                value={columnSearch}
                onChange={(event) => setColumnSearch(event.target.value)}
                placeholder="listing_id, condition_id..."
                disabled={loadingColumns}
              />
            </label>

            {loadingColumns ? (
              <p>Đang đọc trường từ nguồn đồng bộ...</p>
            ) : columnOptions.length === 0 ? (
              <p>Không tìm thấy trường dữ liệu để export.</p>
            ) : visibleColumnOptions.length === 0 ? (
              <p>Không có trường phù hợp với từ khóa tìm kiếm.</p>
            ) : (
              <div className="export-columns-grid">
                {visibleColumnOptions.map((column) => (
                  <label key={column.key} className="export-checkbox">
                    <input
                      type="checkbox"
                      checked={selectedColumns.includes(column.key)}
                      onChange={() => toggleColumn(column.key)}
                    />

                    <span>
                      {column.label}

                      <small>
                        {column.source === "google_sheet"
                          ? "Google Sheet"
                          : "Hệ thống"}
                      </small>
                    </span>
                  </label>
                ))}
              </div>
            )}
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
            disabled={
              exporting || loadingColumns || selectedColumns.length === 0
            }
          >
            {exportButtonLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
