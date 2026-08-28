import { describe, it, expect, vi, beforeEach } from 'vitest'
import { activitiesApi } from '../activities'
import apiClient from '../client'

vi.mock('../client', () => ({
  default: {
    get: vi.fn(),
    delete: vi.fn(),
  },
}))

const mockGet = vi.mocked(apiClient.get)
const mockDelete = vi.mocked(apiClient.delete)

describe('activitiesApi', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('list', () => {
    it('fetches activities with default parameters', async () => {
      const mockResponse = {
        data: {
          activities: [],
          pagination: { page: 1, per_page: 20, total: 0, total_pages: 0 },
        },
      }
      mockGet.mockResolvedValue(mockResponse)

      const result = await activitiesApi.list()

      expect(mockGet).toHaveBeenCalledWith('/activities/?')
      expect(result).toEqual(mockResponse.data)
    })

    it('fetches activities with filters', async () => {
      const mockResponse = {
        data: {
          activities: [{ id: 1, name: 'Morning Run' }],
          pagination: { page: 1, per_page: 20, total: 1, total_pages: 1 },
        },
      }
      mockGet.mockResolvedValue(mockResponse)

      const filters = {
        type: 'Run',
        start_date: '2026-01-01',
        page: 2,
        per_page: 10,
      }

      const result = await activitiesApi.list(filters)

      expect(mockGet).toHaveBeenCalledWith(
        '/activities/?type=Run&start_date=2026-01-01&page=2&per_page=10'
      )
      expect(result).toEqual(mockResponse.data)
    })

    it('filters out undefined and empty values', async () => {
      const mockResponse = {
        data: {
          activities: [],
          pagination: { page: 1, per_page: 20, total: 0, total_pages: 0 },
        },
      }
      mockGet.mockResolvedValue(mockResponse)

      await activitiesApi.list({
        type: undefined,
        distance_bucket: '',
        page: 1,
      })

      expect(mockGet).toHaveBeenCalledWith('/activities/?page=1')
    })
  })

  describe('getDetail', () => {
    it('fetches activity detail by ID', async () => {
      const mockResponse = {
        data: {
          id: 1,
          name: 'Morning Run',
          distance: 10000,
          moving_time: 3600,
        },
      }
      mockGet.mockResolvedValue(mockResponse)

      const result = await activitiesApi.getDetail(1)

      expect(mockGet).toHaveBeenCalledWith('/activities/1')
      expect(result).toEqual(mockResponse.data)
    })
  })

  describe('delete', () => {
    it('deletes activity by ID', async () => {
      mockDelete.mockResolvedValue({})

      await activitiesApi.delete(1)

      expect(mockDelete).toHaveBeenCalledWith('/activities/1')
    })
  })
})
