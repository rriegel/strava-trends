import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { AxiosError } from 'axios'
import type { AxiosResponse, InternalAxiosRequestConfig } from 'axios'

// The refresh path in client.ts calls bare axios.post('/api/auth/refresh', ...).
// We mock axios.post while keeping axios.create real, so the apiClient
// instance is a genuine axios instance whose adapter we control.
const { mockAdapter, mockPost } = vi.hoisted(() => ({
  mockAdapter: vi.fn(),
  mockPost: vi.fn(),
}))

vi.mock('axios', async (importOriginal) => {
  const actual = await importOriginal<typeof import('axios')>()
  return {
    ...actual,
    default: {
      ...actual.default,
      post: mockPost,
    },
  }
})

import apiClient, { setTokens, getAccessToken, getRefreshToken, clearTokens } from '../client'

// jsdom doesn't implement navigation; replace window.location with a plain
// object so the redirect-on-refresh-failure can be asserted.
const realLocation = window.location
beforeEach(() => {
  apiClient.defaults.adapter = mockAdapter as never
  const mockLoc = {
    href: 'http://localhost/',
    pathname: '/',
    search: '',
    assign: vi.fn(),
    replace: vi.fn(),
  } as unknown as Location
  // @ts-expect-error - replacing jsdom's read-only location
  window.location = mockLoc
})

afterEach(() => {
  // @ts-expect-error - restoring jsdom's read-only location
  window.location = realLocation
  localStorage.clear()
  vi.clearAllMocks()
})

function make401(config: InternalAxiosRequestConfig): AxiosError {
  const response = {
    status: 401,
    statusText: 'Unauthorized',
    config,
    headers: {},
  } as unknown as AxiosResponse
  return new AxiosError('Unauthorized', 'ERR_BAD_REQUEST', config, null, response)
}

function make200(config: InternalAxiosRequestConfig): AxiosResponse {
  return { data: {}, status: 200, statusText: 'OK', config, headers: {} } as AxiosResponse
}

function stubRefresh(): void {
  mockPost.mockResolvedValue({
    data: { access_token: 'new-access', refresh_token: 'new-refresh', token_type: 'Bearer', expires_in: 900 },
    status: 200,
  })
}

describe('api client request interceptor', () => {
  it('attaches the access token from localStorage', async () => {
    setTokens('access-1', 'refresh-1')
    mockAdapter.mockImplementation(async (config) => make200(config))

    await apiClient.get('/activities')

    const config = mockAdapter.mock.calls[0][0] as InternalAxiosRequestConfig
    expect(config.headers.Authorization).toBe('Bearer access-1')
  })

  it('sends no Authorization header when no token is stored', async () => {
    clearTokens()
    mockAdapter.mockImplementation(async (config) => make200(config))

    await apiClient.get('/activities')

    const config = mockAdapter.mock.calls[0][0] as InternalAxiosRequestConfig
    expect(config.headers.Authorization).toBeUndefined()
  })
})

describe('api client 401 refresh interceptor', () => {
  beforeEach(() => {
    setTokens('old-access', 'old-refresh')
  })

  it('refreshes once and retries with the new token', async () => {
    stubRefresh()
    mockAdapter.mockImplementation(async (config) => {
      if (config.headers.Authorization === 'Bearer old-access') {
        throw make401(config)
      }
      return make200(config)
    })

    const response = await apiClient.get('/activities')

    expect(response.status).toBe(200)
    expect(mockPost).toHaveBeenCalledTimes(1)
    expect(mockPost).toHaveBeenCalledWith('/api/auth/refresh', { refresh_token: 'old-refresh' }, expect.anything())
    expect(getAccessToken()).toBe('new-access')
    expect(getRefreshToken()).toBe('new-refresh')
    // The retry carried the new token
    const retryConfig = mockAdapter.mock.calls[1][0] as InternalAxiosRequestConfig
    expect(retryConfig.headers.Authorization).toBe('Bearer new-access')
  })

  it('queues concurrent 401s behind a single refresh', async () => {
    stubRefresh()
    mockAdapter.mockImplementation(async (config) => {
      if (config.headers.Authorization === 'Bearer old-access') {
        throw make401(config)
      }
      return make200(config)
    })

    const [a, b] = await Promise.all([
      apiClient.get('/activities'),
      apiClient.get('/trends'),
    ])

    expect(a.status).toBe(200)
    expect(b.status).toBe(200)
    // Exactly one refresh call despite two concurrent 401s
    expect(mockPost).toHaveBeenCalledTimes(1)
    // Both retries carried the new token
    expect(mockAdapter.mock.calls.length).toBe(4)
    expect(mockAdapter.mock.calls[2][0].headers.Authorization).toBe('Bearer new-access')
    expect(mockAdapter.mock.calls[3][0].headers.Authorization).toBe('Bearer new-access')
  })

  it('clears tokens and redirects to login when refresh fails', async () => {
    mockPost.mockRejectedValue(new Error('401'))
    mockAdapter.mockImplementation(async (config) => {
      throw make401(config)
    })

    await expect(apiClient.get('/activities')).rejects.toThrow()

    expect(getAccessToken()).toBeNull()
    expect(getRefreshToken()).toBeNull()
    expect(mockPost).toHaveBeenCalledTimes(1)
    expect(window.location.href).toContain('/login')
  })

  it('does not refresh on /auth/login 401s', async () => {
    mockAdapter.mockImplementation(async (config) => {
      throw make401(config)
    })

    await expect(apiClient.post('/auth/login', { email: 'x', password: 'y' })).rejects.toThrow()

    expect(mockPost).not.toHaveBeenCalled()
    expect(getAccessToken()).toBe('old-access')
  })

  it('does not refresh on /auth/refresh 401s', async () => {
    // The refresh call itself is a bare axios.post (mocked), but if a client
    // instance call to /auth/refresh ever 401s, it must not loop.
    mockAdapter.mockImplementation(async (config) => {
      throw make401(config)
    })

    await expect(apiClient.post('/auth/refresh', { refresh_token: 'x' })).rejects.toThrow()

    expect(mockPost).not.toHaveBeenCalled()
  })

  it('retries only once per request', async () => {
    stubRefresh()
    // Every request fails with 401 — the retry must not trigger another refresh.
    mockAdapter.mockImplementation(async (config) => {
      throw make401(config)
    })

    await expect(apiClient.get('/activities')).rejects.toThrow()

    expect(mockPost).toHaveBeenCalledTimes(1)
    expect(mockAdapter.mock.calls.length).toBe(2)
  })
})
