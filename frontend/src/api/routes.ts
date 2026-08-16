import apiClient from './client'
import type { Route } from '../types'

export async function getRoutes(params?: {
  limit?: number
  offset?: number
}): Promise<Route[]> {
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
