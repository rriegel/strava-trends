import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

// vi.mock is hoisted, so we use vi.hoisted for the mock references
const { mockGetCurrentUser, mockApiLogout } = vi.hoisted(() => ({
  mockGetCurrentUser: vi.fn(),
  mockApiLogout: vi.fn(),
}))

vi.mock('../../api/auth', () => ({
  getCurrentUser: mockGetCurrentUser,
  logout: mockApiLogout,
}))

vi.mock('../../api/client', () => ({
  getAccessToken: () => localStorage.getItem('auth_token'),
  getRefreshToken: () => localStorage.getItem('refresh_token'),
  setTokens: (access: string, refresh: string) => {
    localStorage.setItem('auth_token', access)
    localStorage.setItem('refresh_token', refresh)
  },
  clearTokens: () => {
    localStorage.removeItem('auth_token')
    localStorage.removeItem('refresh_token')
  },
}))

const { useAuth } = await import('../useAuth')

function renderHookInRouter() {
  return renderHook(() => useAuth(), {
    wrapper: ({ children }: { children: React.ReactNode }) => (
      <MemoryRouter>{children}</MemoryRouter>
    ),
  })
}

describe('useAuth', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
    mockGetCurrentUser.mockResolvedValue({ data: null })
  })

  afterEach(() => {
    localStorage.clear()
  })

  it('returns authentication state shape', () => {
    const { result } = renderHookInRouter()

    expect(result.current).toHaveProperty('user')
    expect(result.current).toHaveProperty('loading')
    expect(result.current).toHaveProperty('isAuthenticated')
    expect(result.current).toHaveProperty('login')
    expect(result.current).toHaveProperty('register')
    expect(result.current).toHaveProperty('logout')
  })

  it('is not authenticated when no token', async () => {
    const { result } = renderHookInRouter()

    await act(async () => {})

    expect(result.current.isAuthenticated).toBe(false)
    expect(result.current.user).toBeNull()
    expect(result.current.loading).toBe(false)
  })

  it('login stores both tokens', async () => {
    const { result } = renderHookInRouter()

    act(() => {
      result.current.login('access-token', 'refresh-token')
    })

    expect(localStorage.getItem('auth_token')).toBe('access-token')
    expect(localStorage.getItem('refresh_token')).toBe('refresh-token')
  })

  it('logout clears tokens and user', async () => {
    localStorage.setItem('auth_token', 'test-token')
    localStorage.setItem('refresh_token', 'test-refresh')
    const { result } = renderHookInRouter()

    await act(async () => {})

    await act(async () => {
      await result.current.logout()
    })

    expect(localStorage.getItem('auth_token')).toBeNull()
    expect(localStorage.getItem('refresh_token')).toBeNull()
    expect(result.current.user).toBeNull()
    expect(result.current.isAuthenticated).toBe(false)
  })

  it('logout calls the server-side revocation endpoint', async () => {
    localStorage.setItem('auth_token', 'test-token')
    localStorage.setItem('refresh_token', 'test-refresh')
    const { result } = renderHookInRouter()

    await act(async () => {})

    await act(async () => {
      await result.current.logout()
    })

    expect(mockApiLogout).toHaveBeenCalledWith('test-refresh')
  })

  it('logout still clears local state when server revocation fails', async () => {
    localStorage.setItem('auth_token', 'test-token')
    localStorage.setItem('refresh_token', 'test-refresh')
    mockApiLogout.mockRejectedValue(new Error('network down'))
    const { result } = renderHookInRouter()

    await act(async () => {})

    await act(async () => {
      await result.current.logout()
    })

    expect(localStorage.getItem('auth_token')).toBeNull()
    expect(localStorage.getItem('refresh_token')).toBeNull()
    expect(result.current.isAuthenticated).toBe(false)
  })
})
