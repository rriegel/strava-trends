import apiClient from './client'
import type { TrendData } from '../types'

export async function getTrends(params: {
  metric_type: string
  distance_bucket?: string
  effort_zone?: string
  terrain_type?: string
  start_date?: string
  end_date?: string
  aggregation?: 'day' | 'week' | 'month' | 'year'
}): Promise<TrendData> {
  const response = await apiClient.get('/trends', { params })
  return response.data
}

export async function getPercentiles(params: {
  metric_type: string
  distance_bucket?: string
  effort_zone?: string
  terrain_type?: string
  start_date?: string
  end_date?: string
}): Promise<{
  metric_type: string
  percentiles: { [key: string]: number }
  count: number
}> {
  const response = await apiClient.get('/trends/percentiles', { params })
  return response.data
}
