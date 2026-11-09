import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { getCurrentUser, logout as apiLogout } from '../api/auth'
import { getAccessToken, getRefreshToken, setTokens, clearTokens } from '../api/client'
import type { User } from '../types'

export function useAuth() {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    const token = getAccessToken()
    if (token) {
      getCurrentUser()
        .then((res) => setUser(res))
        .catch(() => clearTokens())
        .finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [])

  const login = (accessToken: string, refreshToken: string) => {
    setTokens(accessToken, refreshToken)
    getCurrentUser()
      .then((res) => setUser(res))
      .catch(() => clearTokens())
  }

  const register = (accessToken: string, refreshToken: string) => {
    setTokens(accessToken, refreshToken)
    getCurrentUser()
      .then((res) => setUser(res))
      .catch(() => clearTokens())
  }

  const logout = async () => {
    const refreshToken = getRefreshToken()
    if (refreshToken) {
      try {
        await apiLogout(refreshToken)
      } catch {
        // Token already revoked or expired — the client clears state either way.
      }
    }
    clearTokens()
    setUser(null)
    navigate('/login', { replace: true })
  }

  return { user, loading, login, register, logout, isAuthenticated: !!user }
}
