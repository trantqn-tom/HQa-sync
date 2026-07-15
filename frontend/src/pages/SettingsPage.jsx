import { useEffect, useState } from "react";
import { api } from "../api/client";

export default function SettingsPage() {
  const [status, setStatus] = useState({ connected: false });
  const load = () => api.get("/google/status").then((r) => setStatus(r.data));
  useEffect(() => {
    load();
  }, []);
  const connect = async () => {
    const r = await api.get("/google/connect");
    window.location.href = r.data.authorization_url;
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
        <p>
          Trạng thái: <b>{status.connected ? "Đã kết nối" : "Chưa kết nối"}</b>
        </p>
        {status.email && <p>Tài khoản: {status.email}</p>}
        <button onClick={connect}>
          {status.connected ? "Kết nối lại" : "Kết nối Google"}
        </button>
        <hr />
        <h3>Spreadsheet nguồn</h3>
        <p>
          <code>1pEqo3jFB6Ii8SSfCFHmh9ZtxuOPiRqYEyRwjOOQm1dg</code>
        </p>
        <p>
          Tab: <b>Raw data ebay</b>
        </p>
        {/* <p className="muted">Marketplace được lấy theo cột <code>marketplace</code> trong Sheet (không gắn cứng một sàn).</p> */}
      </div>
    </>
  );
}
