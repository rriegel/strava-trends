import { useState } from 'react'
import { useMultiTrend, usePercentileBands } from '../hooks/useTrends'
import MultiMetricChart from '../components/MultiMetricChart'
import MultiMetricSelector, { AVAILABLE_METRICS } from '../components/MultiMetricSelector'
import TrendFilters from '../components/TrendFilters'
import StatCard from '../components/StatCard'
import { formatPace, isPaceMetric } from '../utils/format'

export default function Trends() {
  const [selectedMetrics, setSelectedMetrics] = useState<string[]>(['average_speed'])
  const [activityType, setActivityType] = useState('')
  const [distanceBucket, setDistanceBucket] = useState('')
  const [aggregation, setAggregation] = useState<'daily' | 'weekly' | 'monthly'>('weekly')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')

  const trendParams = {
    activity_type: activityType || undefined,
    distance_bucket: distanceBucket || undefined,
    aggregation,
    start_date: startDate || undefined,
    end_date: endDate || undefined,
  }

  const clearFilters = () => {
    setActivityType('')
    setDistanceBucket('')
    setStartDate('')
    setEndDate('')
  }

  // Use the first selected metric for percentile bands
  const primaryMetric = selectedMetrics[0]
  const percentileParams = {
    metric_type: primaryMetric,
    activity_type: activityType || 'Run',
    distance_bucket: distanceBucket || undefined,
  }

  const { data: multiTrendData, isLoading: trendLoading, error: trendError } = useMultiTrend(
    selectedMetrics,
    trendParams
  )
  const { data: percentileData } = usePercentileBands(percentileParams)

  // Calculate summary stats from the first metric
  const primaryTrendData = multiTrendData?.[primaryMetric]
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
              value={primaryTrendData?.trend.direction || 'stable'}
              subtitle={`R²: ${primaryTrendData?.trend.r_squared.toFixed(2) || '0.00'}`}
            />
            <StatCard
              title="Data Points"
              value={totalDataPoints.toString()}
              subtitle="activities analyzed"
            />
            <StatCard
              title="Slope"
              value={primaryTrendData?.trend.slope.toFixed(3) || '0.000'}
              subtitle="rate of change"
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

function formatMetricValue(value: number, metricType: string): string {
  if (isPaceMetric(metricType)) {
    return formatPace(value)
  }
  if (metricType === 'elevation_gain') {
    return `${value.toFixed(0)}m`
  }
  return value.toFixed(1)
}
