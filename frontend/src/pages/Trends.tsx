import { useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useMultiTrend, usePercentileBands } from '../hooks/useTrends'
import MultiMetricChart from '../components/MultiMetricChart'
import MultiMetricSelector, { AVAILABLE_METRICS } from '../components/MultiMetricSelector'
import TrendFilters from '../components/TrendFilters'
import StatCard from '../components/StatCard'
import { formatPaceDecimal, isPaceDisplay } from '../utils/format'

const VALID_METRICS = new Set(AVAILABLE_METRICS.map((m) => m.value))
const VALID_AGGREGATIONS = new Set(['daily', 'weekly', 'monthly'])

/**
 * Read filter state from URL query params (shareable links / back button).
 * Invalid or missing values fall back to the same defaults as before.
 */
function filtersFromParams(params: URLSearchParams): {
  metrics: string[]
  activityType: string
  distanceBucket: string
  aggregation: 'daily' | 'weekly' | 'monthly'
  startDate: string
  endDate: string
} {
  const metrics = (params.get('metrics') || 'average_speed')
    .split(',')
    .filter((m) => VALID_METRICS.has(m))
  const aggregationParam = params.get('aggregation') || 'weekly'

  return {
    metrics: metrics.length > 0 ? metrics : ['average_speed'],
    activityType: params.get('type') || '',
    distanceBucket: params.get('bucket') || '',
    aggregation: (VALID_AGGREGATIONS.has(aggregationParam) ? aggregationParam : 'weekly') as 'daily' | 'weekly' | 'monthly',
    startDate: params.get('start') || '',
    endDate: params.get('end') || '',
  }
}

export default function Trends() {
  const [searchParams, setSearchParams] = useSearchParams()
  const filters = filtersFromParams(searchParams)

  const selectedMetrics = filters.metrics
  const activityType = filters.activityType
  const distanceBucket = filters.distanceBucket
  const aggregation = filters.aggregation
  const startDate = filters.startDate
  const endDate = filters.endDate

  // Sync filter state -> URL (shareable links, back/forward works)
  const setFilters = (updates: Record<string, string | string[]>) => {
    const next = new URLSearchParams(searchParams)
    Object.entries(updates).forEach(([key, value]) => {
      const serialized = Array.isArray(value) ? value.join(',') : value
      if (serialized) {
        next.set(key, serialized)
      } else {
        next.delete(key)
      }
    })
    setSearchParams(next, { replace: true })
  }

  const setSelectedMetrics = (metrics: string[]) => setFilters({ metrics })
  const setActivityType = (type: string) => setFilters({ type })
  const setDistanceBucket = (bucket: string) => setFilters({ bucket })
  const setAggregation = (agg: string) => setFilters({ aggregation: agg })
  const setStartDate = (start: string) => setFilters({ start })
  const setEndDate = (end: string) => setFilters({ end })

  // Keep the URL in sync on first mount if params are missing entirely,
  // so a bare /trends link immediately becomes shareable
  useEffect(() => {
    if (![...searchParams.keys()].some((k) => ['metrics', 'type', 'bucket', 'aggregation', 'start', 'end'].includes(k))) {
      setSearchParams(new URLSearchParams({ metrics: selectedMetrics.join(',') }), { replace: true })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const clearFilters = () => {
    setSearchParams(new URLSearchParams({ metrics: selectedMetrics.join(',') }), { replace: true })
  }

  // Use the first selected metric for the summary stat cards
  const primaryMetric = selectedMetrics[0]
  const percentileParams = {
    metric_type: primaryMetric,
    activity_type: activityType || 'Run',
    distance_bucket: distanceBucket || undefined,
  }

  const trendParams = {
    activity_type: activityType || undefined,
    distance_bucket: distanceBucket || undefined,
    aggregation,
    start_date: startDate || undefined,
    end_date: endDate || undefined,
  }

  const { data: multiTrendData, isLoading: trendLoading, error: trendError } = useMultiTrend(
    selectedMetrics,
    trendParams
  )
  const { data: percentileData } = usePercentileBands(percentileParams)

  // Summary stats come from the primary metric's API trend.
  // Values/trends arrive in display units (pace metrics = min/km) from the
  // backend, so no client-side recalculation is needed.
  const primaryTrendData = multiTrendData?.[primaryMetric]
  const primaryTrend = primaryTrendData?.trend
  const totalDataPoints = primaryTrendData?.data_points?.length || 0

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Trends</h1>
        <p className="text-gray-600 mt-1">
          Analyze your performance over time and track improvements
        </p>
      </div>

      <div className="bg-white rounded-lg shadow-sm border p-6 space-y-4">
        <MultiMetricSelector
          metrics={AVAILABLE_METRICS}
          selected={selectedMetrics}
          onChange={setSelectedMetrics}
          maxSelections={3}
          label="Metrics"
        />
        <TrendFilters
          activityType={activityType}
          distanceBucket={distanceBucket}
          aggregation={aggregation}
          startDate={startDate}
          endDate={endDate}
          onActivityTypeChange={setActivityType}
          onDistanceBucketChange={setDistanceBucket}
          onAggregationChange={(v) => setAggregation(v as 'daily' | 'weekly' | 'monthly')}
          onStartDateChange={setStartDate}
          onEndDateChange={setEndDate}
          onClearFilters={clearFilters}
        />
      </div>

      {trendLoading && (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
        </div>
      )}

      {trendError && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800">Failed to load trend data. Please try again.</p>
        </div>
      )}

      {multiTrendData && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <StatCard
              title="Trend"
              value={primaryTrend?.direction || 'stable'}
              subtitle={`R²: ${primaryTrend?.r_squared.toFixed(2) || '0.00'}`}
            />
            <StatCard
              title="Data Points"
              value={totalDataPoints.toString()}
              subtitle="activities analyzed"
            />
            <StatCard
              title="Slope"
              value={primaryTrend?.slope.toFixed(3) || '0.000'}
              subtitle={primaryMetric === 'average_speed' || primaryMetric === 'grade_adjusted_pace'
                ? 'min/km per day'
                : 'per day'}
            />
          </div>

          <MultiMetricChart
            data={multiTrendData}
            metricTypes={selectedMetrics}
            title="Multi-Metric Trend"
            showAggregated={aggregation !== 'daily'}
          />

          {percentileData && percentileData.bands.length > 0 && (
            <div className="bg-white rounded-lg shadow-sm border p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">
                Percentile Distribution ({AVAILABLE_METRICS.find(m => m.value === primaryMetric)?.label || primaryMetric})
              </h3>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Period</th>
                      <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase">P10</th>
                      <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase">P50</th>
                      <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase">P90</th>
                      <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase">Count</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {percentileData.bands.slice(-10).map((band) => (
                      <tr key={band.date}>
                        <td className="px-4 py-2 text-sm text-gray-900">{band.date}</td>
                        <td className="px-4 py-2 text-sm text-gray-600 text-right">
                          {formatMetricValue(band.p10, primaryMetric)}
                        </td>
                        <td className="px-4 py-2 text-sm text-gray-900 font-medium text-right">
                          {formatMetricValue(band.p50, primaryMetric)}
                        </td>
                        <td className="px-4 py-2 text-sm text-gray-600 text-right">
                          {formatMetricValue(band.p90, primaryMetric)}
                        </td>
                        <td className="px-4 py-2 text-sm text-gray-500 text-right">{band.count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}

/**
 * Format a percentile-band value for display.
 * Percentile values arrive in display units (pace = min/km decimal minutes),
 * so pace metrics use formatPaceDecimal; everything else is a plain number.
 */
function formatMetricValue(value: number, metricType: string): string {
  if (isPaceDisplay(metricType)) {
    return formatPaceDecimal(value)
  }
  if (metricType === 'total_elevation_gain') {
    return `${value.toFixed(0)}m`
  }
  if (metricType === 'distance') {
    return `${(value / 1000).toFixed(2)}km`
  }
  return value.toFixed(1)
}
