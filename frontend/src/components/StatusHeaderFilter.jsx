import { useEffect, useMemo, useRef, useState } from "react";
import { Filter, Search } from "lucide-react";

export default function StatusHeaderFilter({
  label = "Status",
  options = [],
  value = [],
  onChange,
  searchPlaceholder = "Search values",
}) {
  const rootRef = useRef(null);
  const triggerRef = useRef(null);
  const menuRef = useRef(null);

  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [draft, setDraft] = useState(value);
  const [menuPos, setMenuPos] = useState({
    top: 0,
    left: 0,
  });

  /**
   * Chuẩn hóa dữ liệu:
   * - Bỏ null, undefined và chuỗi rỗng.
   * - Chuyển tất cả thành chuỗi.
   * - Loại bỏ giá trị trùng.
   */
  const normalizedOptions = useMemo(
    () => [...new Set(options.filter(Boolean).map((item) => String(item)))],
    [options],
  );

  /**
   * value = [] được hiểu là đang chọn tất cả.
   */
  const allSelected =
    value.length === 0 ||
    (normalizedOptions.length > 0 && value.length === normalizedOptions.length);

  const active = !allSelected;

  /**
   * Tính vị trí popup.
   *
   * Popup tự động:
   * - Không vượt khỏi mép phải màn hình.
   * - Mở lên trên nếu bên dưới không đủ chỗ.
   */
  const updateMenuPos = () => {
    const rect = triggerRef.current?.getBoundingClientRect();

    if (!rect) {
      return;
    }

    const viewportPadding = 8;
    const menuWidth = menuRef.current?.offsetWidth || 280;
    const menuHeight = menuRef.current?.offsetHeight || 340;

    const maxLeft = Math.max(
      viewportPadding,
      window.innerWidth - menuWidth - viewportPadding,
    );

    const left = Math.min(Math.max(rect.left, viewportPadding), maxLeft);

    const hasRoomBelow =
      window.innerHeight - rect.bottom >= menuHeight + viewportPadding;

    const top = hasRoomBelow
      ? rect.bottom + 6
      : Math.max(viewportPadding, rect.top - menuHeight - 6);

    setMenuPos({
      top,
      left,
    });
  };

  /**
   * Khi mở bộ lọc:
   * - Nếu chưa lọc thì đánh dấu toàn bộ option.
   * - Nếu đang lọc thì lấy danh sách đã chọn.
   * - Xóa từ khóa tìm kiếm cũ.
   */
  useEffect(() => {
    if (!open) {
      return undefined;
    }

    setDraft(value.length ? value : [...normalizedOptions]);

    setQuery("");
    updateMenuPos();

    const frameId = window.requestAnimationFrame(updateMenuPos);

    return () => {
      window.cancelAnimationFrame(frameId);
    };
  }, [open, value, normalizedOptions]);

  /**
   * Đóng popup khi click ra ngoài.
   * Cập nhật lại vị trí khi scroll hoặc resize.
   */
  useEffect(() => {
    if (!open) {
      return undefined;
    }

    const onDoc = (event) => {
      if (rootRef.current && !rootRef.current.contains(event.target)) {
        setOpen(false);
      }
    };

    const onReposition = () => {
      updateMenuPos();
    };

    document.addEventListener("mousedown", onDoc);

    window.addEventListener("resize", onReposition);

    window.addEventListener("scroll", onReposition, true);

    return () => {
      document.removeEventListener("mousedown", onDoc);

      window.removeEventListener("resize", onReposition);

      window.removeEventListener("scroll", onReposition, true);
    };
  }, [open]);

  /**
   * Tìm kiếm option không phân biệt hoa thường.
   */
  const filtered = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();

    if (!normalizedQuery) {
      return normalizedOptions;
    }

    return normalizedOptions.filter((item) =>
      item.toLowerCase().includes(normalizedQuery),
    );
  }, [normalizedOptions, query]);

  const toggle = (item) => {
    setDraft((current) =>
      current.includes(item)
        ? current.filter((selectedItem) => selectedItem !== item)
        : [...current, item],
    );
  };

  const apply = () => {
    /**
     * Không chọn gì hoặc chọn toàn bộ:
     * gửi [] để backend hiểu là không lọc.
     */
    if (draft.length === 0 || draft.length === normalizedOptions.length) {
      onChange([]);
    } else {
      onChange(draft);
    }

    setOpen(false);
  };

  return (
    <div ref={rootRef} className={`sheet-filter ${active ? "is-active" : ""}`}>
      <button
        ref={triggerRef}
        type="button"
        className="sheet-filter-trigger"
        aria-expanded={open}
        aria-label={`Lọc theo ${label}`}
        onClick={(event) => {
          event.stopPropagation();
          setOpen((current) => !current);
        }}
      >
        <span>{label}</span>
        <Filter size={14} />
      </button>

      {open && (
        <div
          ref={menuRef}
          className="sheet-filter-menu"
          style={{
            top: menuPos.top,
            left: menuPos.left,
          }}
          onClick={(event) => {
            event.stopPropagation();
          }}
        >
          <div className="sheet-filter-actions">
            <button
              type="button"
              className="linkish"
              onClick={() => setDraft([...normalizedOptions])}
            >
              Select all {normalizedOptions.length}
            </button>

            <button
              type="button"
              className="linkish"
              onClick={() => setDraft([])}
            >
              Clear
            </button>

            <span className="sheet-filter-count">
              Displaying {filtered.length}
            </span>
          </div>

          <div className="sheet-filter-search">
            <Search size={14} />

            <input
              value={query}
              placeholder={searchPlaceholder}
              autoFocus
              onChange={(event) => setQuery(event.target.value)}
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

            {!filtered.length && (
              <div className="sheet-filter-empty">Không có giá trị</div>
            )}
          </div>

          <div className="sheet-filter-footer">
            <button
              type="button"
              className="sheet-btn cancel"
              onClick={() => setOpen(false)}
            >
              Cancel
            </button>

            <button type="button" className="sheet-btn ok" onClick={apply}>
              OK
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
