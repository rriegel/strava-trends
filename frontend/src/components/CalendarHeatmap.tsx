import { useMemo, useState } from 'react'
import { useCalendar } from '../hooks/useCalendar'
import { cn } from '../utils/classnames'

type MetricType = 'distance' | 'count' | 'moving_time'

const METRIC_LABELS: Record<MetricType, string> = {
  distance: 'Distance',
  count: 'Activities',
  moving_time: 'Time',
}

const COLORS = {
  distance: ['#ebedf0', '#9be9a8', '#40c463', '#30a14e', '#216e39'],
  count: ['#ebedf0', '#c6e48b', '#7bc96f', '#239a3b', '#196127'],
  moving_time: ['#ebedf0', '#79a8f7', '#4a8af4', '#1f69e3', '#0d47a1'],
}

function formatValue(value: number, metric: MetricType): string {
  if (metric === 'distance') {
    return `${(value / 1000).toFixed(1)} km`
  }
  if (metric === 'moving_time') {
    const hours = Math.floor(value / 3600)
    const minutes = Math.floor((value % 3600) / 60)
    return hours > 0 ? `${hours}h ${minutes}m` : `${minutes}m`
  }
  return `${value}`
}

function getColorIndex(value: number, maxValue: number): number {
  if (value === 0) return 0
  const ratio = value / maxValue
  if (ratio < 0.25) return 1
  if (ratio < 0.5) return 2
  if (ratio < 0.75) return 3
  return 4
}

interface DayData {
  date: Date
  value: number
  count: number
}

export default function CalendarHeatmap() {
  const [metric, setMetric] = useState<MetricType>('distance')
  const { data, isLoading, error } = useCalendar({ metric })

  // Build a map of date -> data
  const dataMap = useMemo(() => {
    if (!data?.data) return new Map<string, DayData>()
    const map = new Map<string, DayData>()
    data.data.forEach((d) => {
      map.set(d.date, {
        date: new Date(d.date),
        value: d.value,
        count: d.count,
      })
    })
    return map
  }, [data])

  // Generate all days in the last year
  const days = useMemo(() => {
    const result: DayData[] = []
    const end = new Date()
    const start = new Date()
    start.setFullYear(start.getFullYear() - 1)

    const current = new Date(start)
    while (current <= end) {
      const dateStr = current.toISOString().split('T')[0]
      const existing = dataMap.get(dateStr)
      result.push({
        date: new Date(current),
        value: existing?.value || 0,
        count: existing?.count || 0,
      })
      current.setDate(current.getDate() + 1)
    }
    return result
  }, [dataMap])

  // Find max value for color scaling
  const maxValue = useMemo(() => {
    return Math.max(...days.map((d) => d.value), 1)
  }, [days])

  // Organize into weeks for grid layout
  const weeks = useMemo(() => {
    const result: DayData[][] = []
    let currentWeek: DayData[] = []

    // Pad first week if it doesn't start on Sunday
    const firstDay = days[0]?.date.getDay() || 0
    for (let i = 0; i < firstDay; i++) {
      currentWeek.push({ date: new Date(0), value: 0, count: 0 })
    }

    days.forEach((day) => {
      currentWeek.push(day)
      if (currentWeek.length === 7) {
        result.push(currentWeek)
        currentWeek = []
      }
    })

    if (currentWeek.length > 0) {
      result.push(currentWeek)
    }

    return result
  }, [days])

  // Generate month labels
  const monthLabels = useMemo(() => {
    const labels: { label: string; weekIndex: number }[] = []
    let lastMonth = -1

    weeks.forEach((week, weekIndex) => {
      const firstValidDay = week.find((d) => d.date.getFullYear() > 1970)
      if (firstValidDay) {
        const month = firstValidDay.date.getMonth()
        if (month !== lastMonth) {
          labels.push({
            label: firstValidDay.date.toLocaleDateString('en-US', { month: 'short' }),
            weekIndex,
          })
          lastMonth = month
        }
      }
    })

    return labels
  }, [weeks])

  const [hoveredDay, setHoveredDay] = useState<DayData | null>(null)
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 })

  const colors = COLORS[metric]

  return (
    <div className="bg-white rounded-lg shadow-sm border p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-gray-900">Activity Calendar</h3>
        <div className="flex gap-2">
          {(['distance', 'count', 'moving_time'] as MetricType[]).map((m) => (
            <button
              key={m}
              onClick={() => setMetric(m)}
              className={cn(
                'px-3 py-1 text-sm rounded-lg transition-colors',
                metric === m
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              )}
            >
              {METRIC_LABELS[m]}
            </button>
          ))}
        </div>
      </div>

      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
        </div>
      )}

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-red-800 text-sm">Failed to load calendar data</p>
        </div>
      )}

      {!isLoading && !error && (
        <div className="relative">
          {/* Month labels */}
          <div className="flex mb-2 text-xs text-gray-500" style={{ paddingLeft: '32px' }}>
            {monthLabels.map((label, i) => (
              <div
                key={i}
                style={{
                  position: 'absolute',
                  left: `${32 + label.weekIndex * 14}px`,
                }}
              >
                {label.label}
              </div>
            ))}
          </div>

          <div className="flex mt-6">
            {/* Day labels */}
            <div className="flex flex-col text-xs text-gray-500 mr-2" style={{ width: '28px' }}>
              {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map((day, i) => (
                <div key={day} style={{ height: '14px', lineHeight: '14px' }}>
                  {i % 2 === 1 ? day : ''}
                </div>
              ))}
            </div>

            {/* Grid */}
            <div className="flex gap-[2px] relative">
              {weeks.map((week, weekIndex) => (
                <div key={weekIndex} className="flex flex-col gap-[2px]">
                  {week.map((day, dayIndex) => {
                    const colorIndex = getColorIndex(day.value, maxValue)
                    const isEmpty = day.date.getFullYear() < 1970

                    return (
                      <div
                        key={dayIndex}
                        className={cn(
                          'w-[12px] h-[12px] rounded-sm transition-all cursor-pointer',
                          isEmpty && 'invisible'
                        )}
                        style={{
                          backgroundColor: isEmpty ? 'transparent' : colors[colorIndex],
                        }}
                        onMouseEnter={(e) => {
                          if (!isEmpty) {
                            setHoveredDay(day)
                            const rect = e.currentTarget.getBoundingClientRect()
                            setTooltipPos({
                              x: rect.left + rect.width / 2,
                              y: rect.top - 8,
                            })
                          }
                        }}
                        onMouseLeave={() => setHoveredDay(null)}
                      />
                    )
                  })}
                </div>
              ))}
            </div>
          </div>

          {/* Legend */}
          <div className="flex items-center justify-end mt-4 gap-2 text-xs text-gray-600">
            <span>Less</span>
            {colors.map((color, i) => (
              <div
                key={i}
                className="w-[12px] h-[12px] rounded-sm"
                style={{ backgroundColor: color }}
              />
            ))}
            <span>More</span>
          </div>

          {/* Tooltip */}
          {hoveredDay && (
            <div
              className="fixed z-50 px-3 py-2 bg-gray-900 text-white text-xs rounded-lg shadow-lg pointer-events-none"
              style={{
                left: tooltipPos.x,
                top: tooltipPos.y,
                transform: 'translate(-50%, -100%)',
              }}
            >
              <div className="font-semibold">
                {hoveredDay.date.toLocaleDateString('en-US', {
                  month: 'short',
                  day: 'numeric',
                  year: 'numeric',
                })}
              </div>
              <div className="text-gray-300">
                {formatValue(hoveredDay.value, metric)}
                {hoveredDay.count > 0 && ` • ${hoveredDay.count} activit${hoveredDay.count === 1 ? 'y' : 'ies'}`}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
