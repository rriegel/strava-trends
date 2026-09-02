import { cn } from '../utils/classnames'

export interface MetricOption {
  value: string
  label: string
  unit: string
}

export const AVAILABLE_METRICS: MetricOption[] = [
  { value: 'average_speed', label: 'Avg Pace', unit: 'min/km' },
  { value: 'average_heartrate', label: 'Avg Heart Rate', unit: 'bpm' },
  { value: 'average_cadence', label: 'Avg Cadence', unit: 'spm' },
  { value: 'total_elevation_gain', label: 'Elevation Gain', unit: 'm' },
  { value: 'distance', label: 'Distance', unit: 'm' },
  { value: 'hr_pace_ratio', label: 'HR/Pace Ratio', unit: '' },
  { value: 'grade_adjusted_pace', label: 'Grade-Adj Pace', unit: 'min/km' },
  { value: 'heart_rate_drift', label: 'HR Drift', unit: '%' },
]

// Consistent color palette for metrics
export const METRIC_COLORS: Record<string, string> = {
  average_speed: '#3b82f6',      // blue
  average_heartrate: '#ef4444',  // red
  average_cadence: '#10b981',    // green
  total_elevation_gain: '#f59e0b', // amber
  distance: '#8b5cf6',           // purple
  hr_pace_ratio: '#ec4899',      // pink
  grade_adjusted_pace: '#06b6d4', // cyan
  heart_rate_drift: '#f97316',   // orange
}

interface MultiMetricSelectorProps {
  metrics: MetricOption[]
  selected: string[]
  onChange: (selected: string[]) => void
  maxSelections?: number
  label?: string
}

export default function MultiMetricSelector({
  metrics,
  selected,
  onChange,
  maxSelections = 3,
  label = 'Metrics',
}: MultiMetricSelectorProps) {
  const toggle = (value: string) => {
    if (selected.includes(value)) {
      // Don't allow deselecting the last metric
      if (selected.length <= 1) return
      onChange(selected.filter((m) => m !== value))
    } else {
      if (selected.length >= maxSelections) return
      onChange([...selected, value])
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <label className="text-sm font-medium text-gray-700">{label}</label>
        <span className="text-xs text-gray-400">
          {selected.length}/{maxSelections} selected
        </span>
      </div>
      <div className="flex flex-wrap gap-2">
        {metrics.map((metric) => {
          const isSelected = selected.includes(metric.value)
          const isDisabled = !isSelected && selected.length >= maxSelections
          const color = METRIC_COLORS[metric.value] || '#6b7280'

          return (
            <button
              key={metric.value}
              type="button"
              disabled={isDisabled}
              onClick={() => toggle(metric.value)}
              className={cn(
                'px-3 py-1.5 rounded-lg text-sm font-medium border transition-all',
                isSelected
                  ? 'text-white border-transparent shadow-sm'
                  : 'bg-white text-gray-600 border-gray-300 hover:border-gray-400',
                isDisabled && 'opacity-40 cursor-not-allowed hover:border-gray-300'
              )}
              style={
                isSelected
                  ? { backgroundColor: color, borderColor: color }
                  : undefined
              }
            >
              {metric.label}
              {metric.unit && (
                <span className={cn('ml-1 text-xs', isSelected ? 'opacity-80' : 'text-gray-400')}>
                  ({metric.unit})
                </span>
              )}
            </button>
          )
        })}
      </div>
    </div>
  )
}
