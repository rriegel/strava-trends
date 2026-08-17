import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'

// vi.mock is hoisted, so we use vi.hoisted for the mock reference
const { mockGet } = vi.hoisted(() => ({ mockGet: vi.fn() }))

vi.mock('../../api/client', () => ({
  default: {
    get: mockGet,
  },
}))

const { useAuth } = await import('../useAuth')

describe('useAuth', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
    mockGet.mockResolvedValue({ data: null })
  })

  afterEach(() => {
    localStorage.clear()
  })

  it('returns authentication state shape', () => {
    const { result } = renderHook(() => useAuth())
    
    expect(result.current).toHaveProperty('user')
    expect(result.current).toHaveProperty('loading')
    expect(result.current).toHaveProperty('isAuthenticated')
    expect(result.current).toHaveProperty('login')
    expect(result.current).toHaveProperty('logout')
  })

  it('is not authenticated when no token', async () => {
    const { result } = renderHook(() => useAuth())
    
    await act(async () => {})
    
    expect(result.current.isAuthenticated).toBe(false)
    expect(result.current.user).toBeNull()
    expect(result.current.loading).toBe(false)
  })

  it('login stores token', () => {
    const { result } = renderHook(() => useAuth())
    
    act(() => {
      result.current.login('test-token')
    })
    
    expect(localStorage.getItem('auth_token')).toBe('test-token')
  })

  it('logout clears token and user', async () => {
    localStorage.setItem('auth_token', 'test-token')
    const { result } = renderHook(() => useAuth())
    
    await act(async () => {})
    
    act(() => {
      result.current.logout()
    })
    
    expect(localStorage.getItem('auth_token')).toBeNull()
    expect(result.current.user).toBeNull()
    expect(result.current.isAuthenticated).toBe(false)
  })
})
