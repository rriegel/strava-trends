import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { getMultiMetricTrend, getPercentileBands, type TrendParams, type PercentileParams } from '../api/trends'

export function useMultiTrend(
  metricTypes: string[],
  params: Omit<TrendParams, 'metric_type'>
) {
  return useQuery({
    queryKey: ['multi-trend', metricTypes, params],
    queryFn: () => getMultiMetricTrend(metricTypes, params),
    enabled: metricTypes.length > 0,
    // Keep the previous filter combo's data rendered while the new combo
    // fetches — the chart stays up and updates in place instead of
    // unmounting to a spinner on every filter change.
    placeholderData: keepPreviousData,
  })
}

export function usePercentileBands(params: PercentileParams) {
  return useQuery({
    queryKey: ['percentile-bands', params],
    queryFn: () => getPercentileBands(params),
    enabled: !!params.metric_type && !!params.activity_type,
    placeholderData: keepPreviousData,
  })
}
