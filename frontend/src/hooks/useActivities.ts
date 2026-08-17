import { useState, useEffect, useCallback } from 'react'
import { activitiesApi, type ActivitySummary, type ActivityFilters, type Pagination } from '../api/activities'

interface UseActivitiesState {
  activities: ActivitySummary[]
  pagination: Pagination | null
  isLoading: boolean
  error: string | null
}

export function useActivities(initialFilters: ActivityFilters = {}) {
  const [filters, setFilters] = useState<ActivityFilters>(initialFilters)
  const [state, setState] = useState<UseActivitiesState>({
    activities: [],
    pagination: null,
    isLoading: true,
    error: null,
  })

  const fetchActivities = useCallback(async (currentFilters: ActivityFilters) => {
    setState((prev) => ({ ...prev, isLoading: true, error: null }))
    
    try {
      const response = await activitiesApi.list(currentFilters)
      setState({
        activities: response.activities,
        pagination: response.pagination,
        isLoading: false,
        error: null,
      })
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load activities'
      setState((prev) => ({
        ...prev,
        isLoading: false,
        error: message,
      }))
    }
  }, [])

  useEffect(() => {
    fetchActivities(filters)
  }, [filters, fetchActivities])

  const updateFilters = useCallback((newFilters: Partial<ActivityFilters>) => {
    setFilters((prev) => ({ ...prev, ...newFilters, page: 1 }))
  }, [])

  const setPage = useCallback((page: number) => {
    setFilters((prev) => ({ ...prev, page }))
  }, [])

  const deleteActivity = useCallback(async (activityId: number) => {
    try {
      await activitiesApi.delete(activityId)
      // Remove from local state
      setState((prev) => ({
        ...prev,
        activities: prev.activities.filter((a) => a.id !== activityId),
        pagination: prev.pagination
          ? {
              ...prev.pagination,
              total: prev.pagination.total - 1,
              total_pages: Math.max(
                1,
                Math.ceil((prev.pagination.total - 1) / prev.pagination.per_page)
              ),
            }
          : null,
      }))
    } catch (err) {
      throw new Error(err instanceof Error ? err.message : 'Failed to delete activity')
    }
  }, [])

  const refresh = useCallback(() => {
    fetchActivities(filters)
  }, [filters, fetchActivities])

  return {
    ...state,
    filters,
    updateFilters,
    setPage,
    deleteActivity,
    refresh,
  }
}
