import apiClient from './client'
import type { Route, Pagination } from '../types'

export interface RoutesResponse {
  routes: Route[]
  pagination: Pagination
}

export async function getRoutes(params?: {
  page?: number
  per_page?: number
  sort_by?: string
  sort_order?: string
  min_activity_count?: number
  start_lat?: number
  start_lng?: number
  radius_km?: number
}): Promise<RoutesResponse> {
  const response = await apiClient.get('/routes', { params })
  return response.data
}

export async function getRoute(id: number): Promise<Route> {
  const response = await apiClient.get(`/routes/${id}`)
  return response.data
}

export async function getRouteClusters(): Promise<any[]> {
  const response = await apiClient.get('/routes/clusters')
  return response.data
}
