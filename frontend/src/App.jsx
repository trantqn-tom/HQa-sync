import { NavLink, Navigate, Route, Routes } from 'react-router-dom'
import { Database, History, LogOut, Settings } from 'lucide-react'
import { AuthProvider, useAuth } from './auth/AuthContext'
import Listings from './pages/Listings'
import ListingDetail from './pages/ListingDetail'
import SyncHistory from './pages/SyncHistory'
import SettingsPage from './pages/SettingsPage'
import LoginPage from './pages/LoginPage'

function ProtectedLayout() {
  const { isAuthenticated, loading, user, logout } = useAuth()

  if (loading) {
    return <div className="login-page"><p className="muted">Đang kiểm tra phiên đăng nhập...</p></div>
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">HQa sync</div>
        <NavLink to="/" end>
          <Database size={18} /> Listings
        </NavLink>
        <NavLink to="/sync-history">
          <History size={18} /> Lịch sử đồng bộ
        </NavLink>
        <NavLink to="/settings">
          <Settings size={18} /> Cấu hình
        </NavLink>
        <div className="sidebar-footer">
          <div className="sidebar-user">{user?.username}</div>
          <button type="button" className="logout-btn" onClick={logout}>
            <LogOut size={16} /> Đăng xuất
          </button>
        </div>
      </aside>
      <main className="main">
        <Routes>
          <Route path="/" element={<Listings />} />
          <Route path="/listings/:id" element={<ListingDetail />} />
          <Route path="/sync-history" element={<SyncHistory />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/*" element={<ProtectedLayout />} />
      </Routes>
    </AuthProvider>
  )
}
