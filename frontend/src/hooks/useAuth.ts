import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { getCurrentUser, logout as apiLogout } from '../api/auth'
import { getAccessToken, getRefreshToken, setTokens, clearTokens } from '../api/client'
import type { User } from '../types'

export function useAuth() {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()
  const queryClient = useQueryClient()

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

  const adoptSession = (accessToken: string, refreshToken: string) => {
    // Account switch in the same tab: the previous user's cached queries
    // (staleTime 5min) would render for the new user. Drop everything.
    queryClient.clear()
    setTokens(accessToken, refreshToken)
    getCurrentUser()
      .then((res) => setUser(res))
      .catch(() => clearTokens())
  }

  const login = (accessToken: string, refreshToken: string) =>
    adoptSession(accessToken, refreshToken)

  const register = (accessToken: string, refreshToken: string) =>
    adoptSession(accessToken, refreshToken)

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
    queryClient.clear()
    navigate('/login', { replace: true })
  }

  return { user, loading, login, register, logout, isAuthenticated: !!user }
}
