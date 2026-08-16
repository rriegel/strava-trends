import { useQuery } from '@tanstack/react-query'
import { getRoutes, getRoute, getRouteClusters } from '../api/routes'
import type { Route } from '../types'

export function useRoutes(params?: {
  limit?: number
  offset?: number
}) {
  return useQuery<Route[]>({
    queryKey: ['routes', params],
    queryFn: () => getRoutes(params),
  })
}

export function useRoute(id: number) {
  return useQuery<Route>({
    queryKey: ['route', id],
    queryFn: () => getRoute(id),
    enabled: !!id,
  })
}

export function useRouteClusters() {
  return useQuery({
    queryKey: ['route-clusters'],
    queryFn: getRouteClusters,
  })
}
