import { useEffect, useState } from "react";
import { api } from "../api/client";

export default function SettingsPage() {
  const [status, setStatus] = useState({
    connected: false,
    email: null,
    spreadsheet_id: "",
    spreadsheet_url: "",
    sheet_name: "",
    auto_clear_after_sync: false,
  });

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = async () => {
    setLoading(true);
    setError("");

    try {
      const response = await api.get("/google/status");
      setStatus(response.data);
    } catch (loadError) {
      setError(
        loadError?.response?.data?.detail ||
          "Không thể đọc cấu hình Google Sheets.",
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const connect = async () => {
    try {
      const response = await api.get("/google/connect");
      window.location.href = response.data.authorization_url;
    } catch (connectError) {
      setError(
        connectError?.response?.data?.detail ||
          "Không thể kết nối tài khoản Google.",
      );
    }
  };

  return (
    <>
      <header className="page-header">
        <div>
          <h1>Cấu hình Google Sheets</h1>
          <p>Đồng bộ listing đa marketplace từ Google Sheet qua OAuth 2.0.</p>
        </div>
      </header>

      <div className="settings-card">
        <h3>Google OAuth</h3>

        {loading ? (
          <p>Đang tải cấu hình...</p>
        ) : (
          <>
            <p>
              Trạng thái:{" "}
              <b>{status.connected ? "Đã kết nối" : "Chưa kết nối"}</b>
            </p>

            {status.email && (
              <p>
                Tài khoản: <b>{status.email}</b>
              </p>
            )}
          </>
        )}

        <button type="button" onClick={connect} disabled={loading}>
          {status.connected ? "Kết nối lại" : "Kết nối Google"}
        </button>

        <hr />

        <h3>Spreadsheet nguồn</h3>

        {status.spreadsheet_id ? (
          <>
            <p>
              Spreadsheet ID:{" "}
              <a href={status.spreadsheet_url} target="_blank" rel="noreferrer">
                <code>{status.spreadsheet_id}</code>
              </a>
            </p>

            <p>
              Tab: <b>{status.sheet_name}</b>
            </p>

            <p>
              Xóa dữ liệu sau đồng bộ:{" "}
              <b>{status.auto_clear_after_sync ? "Có" : "Không"}</b>
            </p>
          </>
        ) : (
          <p>Chưa đọc được cấu hình nguồn đồng bộ.</p>
        )}

        {error && <p className="error-text">{error}</p>}
      </div>
    </>
  );
}
