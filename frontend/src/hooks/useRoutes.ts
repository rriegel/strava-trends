import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getRoutes, getRoute, renameRoute, compareRouteActivities, type RoutesResponse } from '../api/routes'
import type { Route } from '../types'

export function useRoutes(params?: {
  page?: number
  per_page?: number
  sort_by?: string
  sort_order?: string
  min_activity_count?: number
}) {
  return useQuery<RoutesResponse>({
    queryKey: ['routes', params],
    queryFn: () => getRoutes(params),
  })
}

export function useRoute(id: number) {
  return useQuery<Route>({
    queryKey: ['route', id],
    queryFn: () => getRoute(id),
    enabled: id > 0,
  })
}

/**
 * Route comparison payload (GPS overlay + race plot + splits). Disabled
 * until 2+ activities are selected — the endpoint 422s below that.
 */
export function useRouteCompare(
  routeId: number,
  activityIds: number[],
  checkpointIntervalM: number = 1000
) {
  return useQuery({
    queryKey: ['route-compare', routeId, activityIds, checkpointIntervalM],
    queryFn: () => compareRouteActivities(routeId, activityIds, checkpointIntervalM),
    enabled: routeId > 0 && activityIds.length >= 2,
  })
}

/**
 * Rename a route. Optimistically patches the cached routes list so the
 * sidebar updates instantly; rolls back on failure.
 */
export function useRenameRoute() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, name }: { id: number; name: string }) => renameRoute(id, name),
    onMutate: async ({ id, name }) => {
      // Optimistic update across any cached routes queries
      const keys: unknown[][] = queryClient
        .getQueryCache()
        .getAll()
        .map((q) => [...q.queryKey] as unknown[])
        .filter((key) => key[0] === 'routes')
      const snapshots = keysWithValue(queryClient, keys)
      keys.forEach((key) => {
        queryClient.setQueryData<RoutesResponse>(key, (old) =>
          old
            ? {
                ...old,
                routes: old.routes.map((r) => (r.id === id ? { ...r, name } : r)),
              }
            : old
        )
      })
      return { snapshots }
    },
    onError: (_err, _vars, context) => {
      context?.snapshots.forEach(([key, data]) => queryClient.setQueryData(key, data))
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['routes'] })
      queryClient.invalidateQueries({ queryKey: ['route'] })
    },
  })
}

function keysWithValue(
  queryClient: ReturnType<typeof useQueryClient>,
  keys: unknown[][]
): [unknown[], unknown][] {
  return keys
    .map((key) => [key, queryClient.getQueryData(key)] as [unknown[], unknown])
    .filter(([, data]) => data !== undefined)
}
