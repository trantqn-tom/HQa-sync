import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import { api } from '../api/client'

const AuthContext = createContext(null)
const TOKEN_KEY = 'bhq_access_token'

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY) || '')
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  const logout = () => {
    localStorage.removeItem(TOKEN_KEY)
    setToken('')
    setUser(null)
  }

  const login = async (username, password) => {
    const res = await api.post('/auth/login', { username, password })
    const nextToken = res.data.access_token
    localStorage.setItem(TOKEN_KEY, nextToken)
    setToken(nextToken)
    setUser({ username: res.data.username })
    return res.data
  }

  useEffect(() => {
    if (!token) {
      setUser(null)
      setLoading(false)
      return
    }
    let alive = true
    setLoading(true)
    api.get('/auth/me')
      .then((res) => { if (alive) setUser(res.data) })
      .catch(() => { if (alive) logout() })
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [token])

  const value = useMemo(
    () => ({
      token,
      user,
      loading,
      isAuthenticated: Boolean(token && user),
      login,
      logout,
    }),
    [token, user, loading],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
