import { useState, useCallback } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { activitiesApi, type ActivityFilters } from '../api/activities'

/**
 * Activities list state via react-query.
 *
 * History: this hook was hand-rolled useState+useEffect, which meant it did
 * NOT subscribe to the query cache — every invalidateQueries(['activities'])
 * (uploads via UPLOAD_INVALIDATED_KEYS, Garmin sync via SYNC_INVALIDATED_KEYS)
 * was a no-op for this page and the list only updated on mount/filter change
 * (bug: synced activities didn't appear until a manual page reload).
 *
 * Now a proper useQuery keyed on the active filters: any cache invalidation
 * of ['activities', ...] refetches whatever is mounted. placeholderData
 * keeps the previous page's list visible while filters change (no flash).
 * The public surface (activities, pagination, isLoading, filters,
 * updateFilters, setPage, deleteActivity, refresh) is unchanged.
 */
export function useActivities(initialFilters: ActivityFilters = {}) {
  const queryClient = useQueryClient()
  const [filters, setFilters] = useState<ActivityFilters>(initialFilters)

  const query = useQuery({
    queryKey: ['activities', 'list', filters],
    queryFn: () => activitiesApi.list(filters),
    placeholderData: (prev) => prev,
  })

  const updateFilters = useCallback((newFilters: Partial<ActivityFilters>) => {
    setFilters((prev) => ({ ...prev, ...newFilters, page: 1 }))
  }, [])

  const setPage = useCallback((page: number) => {
    setFilters((prev) => ({ ...prev, page }))
  }, [])

  const deleteActivity = useCallback(
    async (activityId: number) => {
      try {
        await activitiesApi.delete(activityId)
        // Refetch the list (and any other mounted activity-derived queries)
        await queryClient.invalidateQueries({ queryKey: ['activities'] })
      } catch (err) {
        throw new Error(err instanceof Error ? err.message : 'Failed to delete activity')
      }
    },
    [queryClient]
  )

  const refresh = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['activities'] })
  }, [queryClient])

  return {
    activities: query.data?.activities ?? [],
    pagination: query.data?.pagination ?? null,
    isLoading: query.isPending,
    error: query.error ? (query.error as Error).message : null,
    filters,
    updateFilters,
    setPage,
    deleteActivity,
    refresh,
  }
}
