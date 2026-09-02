import apiClient from './client'
import type { TrendData, PercentileData } from '../types'

export interface TrendParams {
  metric_type: string
  activity_type?: string
  distance_bucket?: string
  start_date?: string
  end_date?: string
  aggregation?: 'daily' | 'weekly' | 'monthly'
  user_id?: number
}

export interface PercentileParams {
  metric_type: string
  activity_type: string
  distance_bucket?: string
  start_date?: string
  end_date?: string
  percentiles?: string
  period?: 'weekly' | 'monthly'
  user_id?: number
}

export async function getMultiMetricTrend(
  metricTypes: string[],
  params: Omit<TrendParams, 'metric_type'>
): Promise<Record<string, TrendData>> {
  const response = await apiClient.get('/trends/metrics/multi', {
    params: { ...params, metric_types: metricTypes.join(',') },
  })
  return response.data.metrics
}

export async function getPercentileBands(params: PercentileParams): Promise<PercentileData> {
  const response = await apiClient.get('/trends/percentiles', { params })
  return response.data
}
