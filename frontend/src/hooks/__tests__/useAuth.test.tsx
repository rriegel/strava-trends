import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClientProvider, QueryClient } from '@tanstack/react-query'

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
  const queryClient = new QueryClient()
  return renderHook(() => useAuth(), {
    wrapper: ({ children }: { children: React.ReactNode }) => (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>{children}</MemoryRouter>
      </QueryClientProvider>
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

  it('clears the React Query cache on login (account switch must not leak user A data)', async () => {
    // Simulates: user A logged in, queries cached, then user B logs in.
    // The cache must be dropped, or user B's pages render user A's data
    // (staleTime 5min would serve it without refetching).
    localStorage.setItem('auth_token', 'old-access')
    localStorage.setItem('refresh_token', 'old-refresh')
    mockGetCurrentUser.mockResolvedValue({
      id: 99, username: 'user-b', firstname: '', lastname: '',
    })

    const cacheKeys: unknown[][] = []
    const queryClient = new QueryClient()
    const clearSpy = vi.spyOn(queryClient, 'clear')
    const setQueryDataSpy = vi.spyOn(queryClient, 'setQueryData')
    setQueryDataSpy.mockImplementation((key: unknown) => cacheKeys.push(key as unknown[]))

    function renderWithCache() {
      return renderHook(() => useAuth(), {
        wrapper: ({ children }: { children: React.ReactNode }) => (
          <QueryClientProvider client={queryClient}>
            <MemoryRouter>{children}</MemoryRouter>
          </QueryClientProvider>
        ),
      })
    }

    // user A session populates the cache (activities etc.)
    const first = renderWithCache()
    await act(async () => {})
    // eslint-disable-next-line testing-library/no-node-access
    queryClient.setQueryData(['activities'], [{ id: 1 }])
    queryClient.setQueryData(['routes'], [{ id: 2 }])
    first.unmount()

    // user B logs in
    const second = renderWithCache()
    await act(async () => {
      second.result.current.login('new-access', 'new-refresh')
    })

    expect(clearSpy).toHaveBeenCalled()
  })

  it('logout clears the React Query cache', async () => {
    localStorage.setItem('auth_token', 't')
    localStorage.setItem('refresh_token', 'r')
    renderHookInRouter()
    await act(async () => {})

    const qc = new QueryClient()
    const clearSpy = vi.spyOn(qc, 'clear')
    // Re-render the hook with our spy client to observe clear() on logout
    const utils = renderHook(() => useAuth(), {
      wrapper: ({ children }: { children: React.ReactNode }) => (
        <QueryClientProvider client={qc}>
          <MemoryRouter>{children}</MemoryRouter>
        </QueryClientProvider>
      ),
    })
    await act(async () => {})
    await act(async () => {
      await utils.result.current.logout()
    })
    expect(clearSpy).toHaveBeenCalled()
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
