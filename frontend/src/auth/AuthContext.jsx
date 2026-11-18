import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import api from '../api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [token, setToken] = useState(() => localStorage.getItem('token'))
  const [loading, setLoading] = useState(() => Boolean(localStorage.getItem('token')))

  useEffect(() => {
    if (!token) {
      setUser(null)
      return
    }
    api
      .get('/auth/me')
      .then((u) => setUser(u))
      .catch(() => {
        localStorage.removeItem('token')
        setToken(null)
        setUser(null)
      })
      .finally(() => setLoading(false))
  }, [token])

  const applySession = useCallback(async (data) => {
    localStorage.setItem('token', data.access_token)
    setToken(data.access_token)
    const u = await api.get('/auth/me')
    setUser(u)
    setLoading(false)
    return u
  }, [])

  const login = useCallback(
    async (email, password) => applySession(await api.login(email, password)),
    [applySession],
  )

  const register = useCallback(
    async (email, username, password) =>
      applySession(await api.register(email, username, password)),
    [applySession],
  )

  const logout = useCallback(() => {
    localStorage.removeItem('token')
    setToken(null)
    setUser(null)
    setLoading(false)
  }, [])

  return (
    <AuthContext.Provider value={{ user, token, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth должен использоваться внутри <AuthProvider>')
  return ctx
}
