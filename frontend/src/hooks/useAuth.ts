import { useState, useEffect } from 'react'
import apiClient from '../api/client'
import type { User } from '../types'

export function useAuth() {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('auth_token')
    if (token) {
      apiClient.get('/users/me')
        .then((res) => setUser(res.data))
        .catch(() => localStorage.removeItem('auth_token'))
        .finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [])

  const login = (token: string) => {
    localStorage.setItem('auth_token', token)
    apiClient.get('/users/me').then((res) => setUser(res.data))
  }

  const logout = () => {
    localStorage.removeItem('auth_token')
    setUser(null)
  }

  return { user, loading, login, logout, isAuthenticated: !!user }
}
