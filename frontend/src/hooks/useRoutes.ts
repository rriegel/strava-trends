import { useQuery } from '@tanstack/react-query'
import { getRoutes, getRoute, type RoutesResponse } from '../api/routes'
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
