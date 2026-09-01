import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'
import type { TrendData } from '../types'
import { METRIC_COLORS, AVAILABLE_METRICS } from './MultiMetricSelector'
import { formatDateTime } from '../utils/formatDate'
import { convertSpeedToPace, formatPaceDecimal, isPaceMetric, isPaceDisplay } from '../utils/format'

interface MultiMetricChartProps {
  data: Record<string, TrendData>
  metricTypes: string[]
  title: string
  showAggregated?: boolean
  height?: number
}

export default function MultiMetricChart({
  data,
  metricTypes,
  title,
  showAggregated = false,
  height = 400,
}: MultiMetricChartProps) {
  // Check if we have any data
  const hasData = metricTypes.some(
    (metric) => data[metric]?.data_points?.length > 0
  )

  if (!hasData) {
    return (
      <div className="bg-white rounded-lg shadow-sm border p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">{title}</h3>
        <div className="flex items-center justify-center" style={{ height }}>
          <p className="text-gray-500">No data available</p>
        </div>
      </div>
    )
  }

  // Build chart data by merging all metrics on the same date
  const dateMap = new Map<string, Record<string, number | string>>()

  metricTypes.forEach((metricType) => {
    const metricData = data[metricType]
    if (!metricData) return

    const points = showAggregated && metricData.aggregated_data.length > 0
      ? metricData.aggregated_data.map((d) => ({ date: d.period, value: d.value }))
      : metricData.data_points.map((d) => ({ date: d.date, value: d.value }))

    points.forEach(({ date, value }) => {
      if (!dateMap.has(date)) {
        dateMap.set(date, { date })
      }
      const entry = dateMap.get(date)!
      
      // Convert speed (m/s) to pace (min/km) for display
      // Note: grade_adjusted_pace is already stored as min/km, so only convert average_speed
      let displayValue = value
      if (isPaceMetric(metricType)) {
        displayValue = typeof value === 'number' && value > 0 ? convertSpeedToPace(value) : 0
      }
      
      entry[metricType] = displayValue
    })
  })

  const chartData = Array.from(dateMap.values()).sort((a, b) =>
    String(a.date).localeCompare(String(b.date))
  )

  // Determine if we need dual Y-axis (metrics have very different scales)
  const needsDualAxis = metricTypes.length >= 2

  // Get metric labels and colors
  const getMetricInfo = (metricType: string) => {
    const metric = AVAILABLE_METRICS.find((m) => m.value === metricType)
    return {
      label: metric?.label || metricType,
      color: METRIC_COLORS[metricType] || '#6b7280',
      unit: metric?.unit || '',
    }
  }

  // Custom tooltip showing all metrics
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload || payload.length === 0) return null

    return (
      <div className="bg-white border border-gray-200 rounded-lg shadow-lg p-3">
        <p className="text-sm font-medium text-gray-900 mb-2">{formatDateTime(label)}</p>
        {payload.map((entry: any) => {
          const info = getMetricInfo(entry.dataKey)
          
          // Format value based on metric type
          let displayValue: string
          if (typeof entry.value === 'number') {
            if (isPaceDisplay(entry.dataKey)) {
              displayValue = formatPaceDecimal(entry.value)
            } else {
              displayValue = entry.value.toFixed(2)
            }
          } else {
            displayValue = entry.value
          }
          
          return (
            <div key={entry.dataKey} className="flex items-center gap-2 text-sm">
              <div
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: entry.color }}
              />
              <span className="text-gray-600">{info.label}:</span>
              <span className="font-medium text-gray-900">
                {displayValue}
                {info.unit && <span className="text-gray-500 ml-1">{info.unit}</span>}
              </span>
            </div>
          )
        })}
      </div>
    )
  }

  // Custom legend with trend indicators
  const CustomLegend = () => (
    <div className="flex flex-wrap gap-4 mt-4 justify-center">
      {metricTypes.map((metricType) => {
        const info = getMetricInfo(metricType)
        const trend = data[metricType]?.trend
        
        // For pace metrics, invert the direction (lower pace is better)
        let direction = trend?.direction || 'stable'
        if (isPaceDisplay(metricType) && trend?.direction) {
          direction = trend.direction === 'increasing' ? 'decreasing' : 
                     trend.direction === 'decreasing' ? 'increasing' : 'stable'
        }
        
        const trendColor =
          direction === 'increasing'
            ? 'text-green-600'
            : direction === 'decreasing'
            ? 'text-red-600'
            : 'text-gray-500'

        return (
          <div key={metricType} className="flex items-center gap-2">
            <div
              className="w-4 h-0.5 rounded"
              style={{ backgroundColor: info.color }}
            />
            <span className="text-sm font-medium text-gray-700">{info.label}</span>
            {trend && (
              <span className={`text-xs ${trendColor}`}>
                {direction} (R²: {trend.r_squared.toFixed(2)})
              </span>
            )}
          </div>
        )
      })}
    </div>
  )

  return (
    <div className="bg-white rounded-lg shadow-sm border p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">{title}</h3>

      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis
            dataKey="date"
            stroke="#9ca3af"
            fontSize={12}
            tick={{ fill: '#6b7280' }}
            tickFormatter={(value) => formatDateTime(value)}
          />

          {needsDualAxis ? (
            <>
              {/* Left Y-axis for first metric */}
              <YAxis
                yAxisId="left"
                stroke={METRIC_COLORS[metricTypes[0]] || '#6b7280'}
                fontSize={12}
                tick={{ fill: '#6b7280' }}
                tickFormatter={(value) => {
                  if (isPaceDisplay(metricTypes[0])) {
                    return formatPaceDecimal(value)
                  }
                  return value.toFixed(1)
                }}
                label={{
                  value: getMetricInfo(metricTypes[0]).label,
                  angle: -90,
                  position: 'insideLeft',
                  style: { fill: METRIC_COLORS[metricTypes[0]] || '#6b7280' },
                }}
              />
              {/* Right Y-axis for second metric */}
              {metricTypes.length >= 2 && (
                <YAxis
                  yAxisId="right"
                  orientation="right"
                  stroke={METRIC_COLORS[metricTypes[1]] || '#6b7280'}
                  fontSize={12}
                  tick={{ fill: '#6b7280' }}
                  tickFormatter={(value) => {
                    if (isPaceDisplay(metricTypes[1])) {
                      return formatPaceDecimal(value)
                    }
                    return value.toFixed(1)
                  }}
                  label={{
                    value: getMetricInfo(metricTypes[1]).label,
                    angle: 90,
                    position: 'insideRight',
                    style: { fill: METRIC_COLORS[metricTypes[1]] || '#6b7280' },
                  }}
                />
              )}
            </>
          ) : (
            <YAxis 
              stroke="#9ca3af" 
              fontSize={12} 
              tick={{ fill: '#6b7280' }}
              tickFormatter={(value) => {
                if (isPaceDisplay(metricTypes[0])) {
                  return formatPaceDecimal(value)
                }
                return value.toFixed(1)
              }}
            />
          )}

          <Tooltip content={<CustomTooltip />} />
          <Legend content={<CustomLegend />} />

          {metricTypes.map((metricType, index) => {
            const info = getMetricInfo(metricType)
            const yAxisId = needsDualAxis ? (index === 0 ? 'left' : 'right') : undefined

            return (
              <Line
                key={metricType}
                yAxisId={yAxisId}
                type="monotone"
                dataKey={metricType}
                stroke={info.color}
                strokeWidth={2}
                dot={{ fill: info.color, r: 3 }}
                activeDot={{ r: 5 }}
                name={info.label}
              />
            )
          })}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
