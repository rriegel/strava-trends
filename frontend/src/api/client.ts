import axios from 'axios'
import type { InternalAxiosRequestConfig, AxiosResponse, AxiosError } from 'axios'

const ACCESS_TOKEN_KEY = 'auth_token'
const REFRESH_TOKEN_KEY = 'refresh_token'

export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_TOKEN_KEY)
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_TOKEN_KEY)
}

export function setTokens(accessToken: string, refreshToken: string): void {
  localStorage.setItem(ACCESS_TOKEN_KEY, accessToken)
  localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken)
}

export function clearTokens(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY)
  localStorage.removeItem(REFRESH_TOKEN_KEY)
}

const apiClient = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Attach the access token to every request
apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = getAccessToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// --- 401 handling: silent refresh, queued concurrent requests, single retry ---

// Endpoints that must never trigger a refresh (they are pre-auth, or the
// refresh call itself — a failed refresh must not loop).
const REFRESH_EXEMPT_PATHS = ['/auth/login', '/auth/register', '/auth/refresh', '/auth/logout']

let refreshPromise: Promise<string | null> | null = null

async function refreshAccessToken(): Promise<string | null> {
  const refreshToken = getRefreshToken()
  if (!refreshToken) return null
  try {
    // Use a bare axios instance so the request interceptor doesn't attach the
    // (expired) access token, and the response interceptor doesn't recurse.
    const response = await axios.post(
      '/api/auth/refresh',
      { refresh_token: refreshToken },
      { headers: { 'Content-Type': 'application/json' } }
    )
    const { access_token, refresh_token } = response.data
    setTokens(access_token, refresh_token)
    return access_token
  } catch {
    // Refresh failed — revoked, expired, or replayed. Clear tokens; the
    // caller (redirect on retry) sends the user to login.
    clearTokens()
    return null
  }
}

apiClient.interceptors.response.use(
  (response: AxiosResponse) => response,
  async (error: AxiosError) => {
    const original = error.config as InternalAxiosRequestConfig & { _retry?: boolean }
    const path = original?.url ?? ''

    if (
      error.response?.status === 401 &&
      original &&
      !original._retry &&
      !REFRESH_EXEMPT_PATHS.some((p) => path.includes(p))
    ) {
      original._retry = true

      // Queue concurrent 401s behind a single shared refresh promise so
      // parallel requests don't trigger parallel refreshes (a refresh rotates
      // the refresh token; a second concurrent refresh would replay the
      // already-rotated token and revoke ALL user sessions).
      if (!refreshPromise) {
        refreshPromise = refreshAccessToken().finally(() => {
          refreshPromise = null
        })
      }
      const newToken = await refreshPromise

      if (newToken) {
        original.headers.Authorization = `Bearer ${newToken}`
        return apiClient(original)
      }

      // Refresh failed — clear tokens and redirect to login, preserving the
      // current location so the user can come back after signing in.
      clearTokens()
      const currentPath = window.location.pathname + window.location.search
      if (window.location.pathname !== '/login') {
        window.location.href = `/login?redirect=${encodeURIComponent(currentPath)}`
      }
    }

    return Promise.reject(error)
  }
)

export default apiClient
