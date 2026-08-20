import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, AreaChart } from 'recharts'
import type { TrendData } from '../types'
import { cn } from '../utils/classnames'

interface TrendChartProps {
  data: TrendData
  title: string
  showTrend?: boolean
  showAggregated?: boolean
  height?: number
}

export default function TrendChart({ 
  data, 
  title, 
  showTrend = false, 
  showAggregated = false,
  height = 300 
}: TrendChartProps) {
  const hasData = data.data_points.length > 0

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

  const chartData = showAggregated && data.aggregated_data.length > 0
    ? data.aggregated_data.map(d => ({ date: d.period, value: d.value, min: d.min, max: d.max }))
    : data.data_points.map(d => ({ date: d.date, value: d.value }))

  const trendColor = data.trend.direction === 'increasing' 
    ? '#10b981' 
    : data.trend.direction === 'decreasing' 
    ? '#ef4444' 
    : '#6b7280'

  return (
    <div className="bg-white rounded-lg shadow-sm border p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
        {showTrend && (
          <div className="flex items-center gap-2">
            <span 
              className={cn(
                'text-sm font-medium',
                data.trend.direction === 'increasing' && 'text-green-600',
                data.trend.direction === 'decreasing' && 'text-red-600',
                data.trend.direction === 'stable' && 'text-gray-500'
              )}
            >
              {data.trend.direction}
            </span>
            <span className="text-xs text-gray-400">
              R²: {data.trend.r_squared.toFixed(2)}
            </span>
          </div>
        )}
      </div>

      <ResponsiveContainer width="100%" height={height}>
        {showAggregated ? (
          <AreaChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis 
              dataKey="date" 
              stroke="#9ca3af"
              fontSize={12}
              tick={{ fill: '#6b7280' }}
            />
            <YAxis 
              stroke="#9ca3af"
              fontSize={12}
              tick={{ fill: '#6b7280' }}
            />
            <Tooltip 
              contentStyle={{ 
                backgroundColor: '#fff', 
                border: '1px solid #e5e7eb',
                borderRadius: '6px'
              }}
            />
            <Area 
              type="monotone" 
              dataKey="value" 
              stroke={trendColor}
              strokeWidth={2}
              fill="#3b82f6"
              fillOpacity={0.1}
            />
          </AreaChart>
        ) : (
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis 
              dataKey="date" 
              stroke="#9ca3af"
              fontSize={12}
              tick={{ fill: '#6b7280' }}
            />
            <YAxis 
              stroke="#9ca3af"
              fontSize={12}
              tick={{ fill: '#6b7280' }}
            />
            <Tooltip 
              contentStyle={{ 
                backgroundColor: '#fff', 
                border: '1px solid #e5e7eb',
                borderRadius: '6px'
              }}
            />
            <Line 
              type="monotone" 
              dataKey="value" 
              stroke="#3b82f6"
              strokeWidth={2}
              dot={{ fill: '#3b82f6', r: 3 }}
              activeDot={{ r: 5 }}
            />
          </LineChart>
        )}
      </ResponsiveContainer>
    </div>
  )
}
