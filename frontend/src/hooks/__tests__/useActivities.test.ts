import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act, waitFor } from '@testing-library/react'
import { useActivities } from '../useActivities'
import { activitiesApi, type ActivitySummary, type ActivitiesResponse } from '../../api/activities'

vi.mock('../../api/activities', () => ({
  activitiesApi: {
    list: vi.fn(),
    delete: vi.fn(),
  },
}))

const mockActivitiesApi = vi.mocked(activitiesApi)

const makeActivity = (overrides: Partial<ActivitySummary> = {}): ActivitySummary => ({
  id: 1,
  strava_id: null,
  name: 'Morning Run',
  type: 'Run',
  sport_type: 'Run',
  start_date: '2026-01-01T10:00:00Z',
  start_date_local: '2026-01-01T10:00:00Z',
  moving_time: 3600,
  distance: 10000,
  total_elevation_gain: 150,
  average_speed: 2.78,
  average_heartrate: 145,
  max_heartrate: null,
  average_cadence: null,
  average_watts: null,
  suffer_score: null,
  device_name: null,
  distance_bucket: null,
  effort_zone: null,
  terrain_type: null,
  route_id: null,
  has_streams: false,
  ...overrides,
})

describe('useActivities', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('fetches activities on mount', async () => {
    const mockResponse: ActivitiesResponse = {
      activities: [makeActivity()],
      pagination: { page: 1, per_page: 20, total: 1, total_pages: 1 },
    }
    mockActivitiesApi.list.mockResolvedValue(mockResponse)

    const { result } = renderHook(() => useActivities())

    expect(result.current.isLoading).toBe(true)

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    expect(result.current.activities).toEqual(mockResponse.activities)
    expect(result.current.pagination).toEqual(mockResponse.pagination)
    expect(mockActivitiesApi.list).toHaveBeenCalledWith({})
  })

  it('fetches activities with initial filters', async () => {
    const mockResponse: ActivitiesResponse = {
      activities: [],
      pagination: { page: 1, per_page: 10, total: 0, total_pages: 0 },
    }
    mockActivitiesApi.list.mockResolvedValue(mockResponse)

    const initialFilters = { per_page: 10, type: 'Run' }
    renderHook(() => useActivities(initialFilters))

    await waitFor(() => {
      expect(mockActivitiesApi.list).toHaveBeenCalledWith(initialFilters)
    })
  })

  it('updates filters and resets page', async () => {
    const mockResponse: ActivitiesResponse = {
      activities: [],
      pagination: { page: 1, per_page: 20, total: 0, total_pages: 0 },
    }
    mockActivitiesApi.list.mockResolvedValue(mockResponse)

    const { result } = renderHook(() => useActivities({ page: 3, per_page: 20 }))

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    act(() => {
      result.current.updateFilters({ type: 'Run' })
    })

    await waitFor(() => {
      expect(mockActivitiesApi.list).toHaveBeenCalledWith({
        page: 1,
        per_page: 20,
        type: 'Run',
      })
    })
  })

  it('changes page', async () => {
    const mockResponse: ActivitiesResponse = {
      activities: [],
      pagination: { page: 1, per_page: 20, total: 0, total_pages: 0 },
    }
    mockActivitiesApi.list.mockResolvedValue(mockResponse)

    const { result } = renderHook(() => useActivities({ per_page: 20 }))

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    act(() => {
      result.current.setPage(2)
    })

    await waitFor(() => {
      expect(mockActivitiesApi.list).toHaveBeenCalledWith({ page: 2, per_page: 20 })
    })
  })

  it('deletes activity and updates local state', async () => {
    const mockResponse: ActivitiesResponse = {
      activities: [
        makeActivity({ id: 1, name: 'Run 1' }),
        makeActivity({ id: 2, name: 'Run 2' }),
      ],
      pagination: { page: 1, per_page: 20, total: 2, total_pages: 1 },
    }
    mockActivitiesApi.list.mockResolvedValue(mockResponse)
    mockActivitiesApi.delete.mockResolvedValue()

    const { result } = renderHook(() => useActivities())

    await waitFor(() => {
      expect(result.current.activities).toHaveLength(2)
    })

    await act(async () => {
      await result.current.deleteActivity(1)
    })

    expect(mockActivitiesApi.delete).toHaveBeenCalledWith(1)
    expect(result.current.activities).toHaveLength(1)
    expect(result.current.activities[0].id).toBe(2)
    expect(result.current.pagination?.total).toBe(1)
  })

  it('handles fetch error', async () => {
    mockActivitiesApi.list.mockRejectedValue(new Error('Network error'))

    const { result } = renderHook(() => useActivities())

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
      expect(result.current.error).toBe('Network error')
    })
  })

  it('refreshes activities', async () => {
    const mockResponse: ActivitiesResponse = {
      activities: [],
      pagination: { page: 1, per_page: 20, total: 0, total_pages: 0 },
    }
    mockActivitiesApi.list.mockResolvedValue(mockResponse)

    const { result } = renderHook(() => useActivities())

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    act(() => {
      result.current.refresh()
    })

    await waitFor(() => {
      expect(mockActivitiesApi.list).toHaveBeenCalledTimes(2)
    })
  })
})
