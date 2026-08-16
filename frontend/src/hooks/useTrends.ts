import { useQuery } from '@tanstack/react-query'
import { getTrends, getPercentiles } from '../api/trends'
import type { TrendData } from '../types'

export function useTrends(params: {
  metric_type: string
  distance_bucket?: string
  effort_zone?: string
  terrain_type?: string
  start_date?: string
  end_date?: string
  aggregation?: 'day' | 'week' | 'month' | 'year'
}) {
  return useQuery<TrendData>({
    queryKey: ['trends', params],
    queryFn: () => getTrends(params),
    enabled: !!params.metric_type,
  })
}

export function usePercentiles(params: {
  metric_type: string
  distance_bucket?: string
  effort_zone?: string
  terrain_type?: string
  start_date?: string
  end_date?: string
}) {
  return useQuery({
    queryKey: ['percentiles', params],
    queryFn: () => getPercentiles(params),
    enabled: !!params.metric_type,
  })
}
