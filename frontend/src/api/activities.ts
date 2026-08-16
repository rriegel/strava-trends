import apiClient from './client'
import type { Activity, ActivityStream, Pagination } from '../types'

export interface ActivitiesResponse {
  activities: Activity[]
  pagination: Pagination
}

export async function getActivities(params: {
  page?: number
  per_page?: number
  type?: string
  distance_bucket?: string
  effort_zone?: string
  terrain_type?: string
  start_date?: string
  end_date?: string
}): Promise<ActivitiesResponse> {
  const response = await apiClient.get('/activities', { params })
  return response.data
}

export async function getActivity(id: number): Promise<Activity> {
  const response = await apiClient.get(`/activities/${id}`)
  return response.data
}

export async function getActivityStreams(id: number): Promise<ActivityStream[]> {
  const response = await apiClient.get(`/activities/${id}/streams`)
  return response.data
}
