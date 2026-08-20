import { useState } from 'react'
import { useTrend, usePercentileBands } from '../hooks/useTrends'
import TrendChart from '../components/TrendChart'
import MetricSelector from '../components/MetricSelector'
import TrendFilters from '../components/TrendFilters'
import StatCard from '../components/StatCard'
import { formatPace } from '../utils/format'

const METRICS = [
  { value: 'average_speed', label: 'Average Speed' },
  { value: 'average_heartrate', label: 'Heart Rate' },
  { value: 'hr_pace_ratio', label: 'HR/Pace Ratio' },
  { value: 'pace_variance', label: 'Pace Variance' },
  { value: 'elevation_gain', label: 'Elevation Gain' },
]

export default function Trends() {
  const [metricType, setMetricType] = useState('average_speed')
  const [activityType, setActivityType] = useState('')
  const [distanceBucket, setDistanceBucket] = useState('')
  const [aggregation, setAggregation] = useState<'daily' | 'weekly' | 'monthly'>('weekly')

  const trendParams = {
    metric_type: metricType,
    activity_type: activityType || undefined,
    distance_bucket: distanceBucket || undefined,
    aggregation,
  }

  const percentileParams = {
    metric_type: metricType,
    activity_type: activityType || 'Run',
    distance_bucket: distanceBucket || undefined,
  }

  const { data: trendData, isLoading: trendLoading, error: trendError } = useTrend(trendParams)
  const { data: percentileData } = usePercentileBands(percentileParams)

  const metricLabel = METRICS.find(m => m.value === metricType)?.label || metricType

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Trends</h1>
        <p className="text-gray-600 mt-1">
          Analyze your performance over time and track improvements
        </p>
      </div>

      <div className="bg-white rounded-lg shadow-sm border p-6 space-y-4">
        <MetricSelector
          metrics={METRICS}
          value={metricType}
          onChange={setMetricType}
          label="Metric"
        />
        <TrendFilters
          activityType={activityType}
          distanceBucket={distanceBucket}
          aggregation={aggregation}
          onActivityTypeChange={setActivityType}
          onDistanceBucketChange={setDistanceBucket}
          onAggregationChange={(v) => setAggregation(v as 'daily' | 'weekly' | 'monthly')}
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

      {trendData && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <StatCard
              title="Trend"
              value={trendData.trend.direction}
              subtitle={`R²: ${trendData.trend.r_squared.toFixed(2)}`}
            />
            <StatCard
              title="Data Points"
              value={trendData.data_points.length.toString()}
              subtitle="activities analyzed"
            />
            <StatCard
              title="Slope"
              value={trendData.trend.slope.toFixed(3)}
              subtitle="rate of change"
            />
          </div>

          <TrendChart
            data={trendData}
            title={`${metricLabel} Over Time`}
            showTrend
            showAggregated={aggregation !== 'daily'}
          />

          {percentileData && percentileData.bands.length > 0 && (
            <div className="bg-white rounded-lg shadow-sm border p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">
                Percentile Distribution
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
                          {formatMetricValue(band.p10, metricType)}
                        </td>
                        <td className="px-4 py-2 text-sm text-gray-900 font-medium text-right">
                          {formatMetricValue(band.p50, metricType)}
                        </td>
                        <td className="px-4 py-2 text-sm text-gray-600 text-right">
                          {formatMetricValue(band.p90, metricType)}
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
  if (metricType === 'average_speed') {
    return formatPace(value)
  }
  if (metricType === 'elevation_gain') {
    return `${value.toFixed(0)}m`
  }
  return value.toFixed(1)
}
