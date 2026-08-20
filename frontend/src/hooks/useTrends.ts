import { useQuery } from '@tanstack/react-query'
import { getTrend, getPercentileBands, type TrendParams, type PercentileParams } from '../api/trends'

export function useTrend(params: TrendParams) {
  return useQuery({
    queryKey: ['trend', params],
    queryFn: () => getTrend(params),
    enabled: !!params.metric_type,
  })
}

export function usePercentileBands(params: PercentileParams) {
  return useQuery({
    queryKey: ['percentile-bands', params],
    queryFn: () => getPercentileBands(params),
    enabled: !!params.metric_type && !!params.activity_type,
  })
}
