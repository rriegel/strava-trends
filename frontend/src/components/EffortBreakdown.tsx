import { useEffect, useState } from 'react'
import { activitiesApi, type EffortData } from '../api/activities'

interface EffortBreakdownProps {
  activityId: number
  hasHeartrate: boolean
}

const ZONE_COLORS: Record<string, string> = {
  easy: 'bg-green-500',
  moderate: 'bg-blue-500',
  threshold: 'bg-yellow-500',
  vo2max: 'bg-orange-500',
  anaerobic: 'bg-red-500',
}

const ZONE_TEXT_COLORS: Record<string, string> = {
  easy: 'text-green-700',
  moderate: 'text-blue-700',
  threshold: 'text-yellow-700',
  vo2max: 'text-orange-700',
  anaerobic: 'text-red-700',
}

function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  if (mins >= 60) {
    const hrs = Math.floor(mins / 60)
    const remainMins = mins % 60
    return `${hrs}h ${remainMins}m`
  }
  return `${mins}m ${secs}s`
}

export default function EffortBreakdown({ activityId, hasHeartrate }: EffortBreakdownProps) {
  const [effort, setEffort] = useState<EffortData | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!hasHeartrate) return

    const fetchEffort = async () => {
      setIsLoading(true)
      setError(null)
      try {
        const data = await activitiesApi.getEffort(activityId)
        setEffort(data)
      } catch (err) {
        // 404 means no HR data — silently skip
        if (err instanceof Error && err.message.includes('404')) {
          setError(null)
        } else {
          setError(err instanceof Error ? err.message : 'Failed to load effort data')
        }
      } finally {
        setIsLoading(false)
      }
    }

    fetchEffort()
  }, [activityId, hasHeartrate])

  if (!hasHeartrate) return null

  if (isLoading) {
    return (
      <div className="border-t pt-4">
        <h3 className="font-semibold text-gray-900 mb-3">Effort Breakdown</h3>
        <div className="animate-pulse space-y-2">
          <div className="h-8 bg-gray-200 rounded"></div>
          <div className="grid grid-cols-5 gap-2">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-12 bg-gray-200 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  if (error || !effort) return null

  return (
    <div className="border-t pt-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold text-gray-900">Effort Breakdown</h3>
        <span className="text-sm text-gray-500">Max HR: {effort.max_hr} bpm</span>
      </div>

      {/* Stacked bar chart */}
      <div className="flex rounded-lg overflow-hidden h-8 mb-4">
        {effort.zone_breakdown.map((zone) => {
          if (zone.percentage === 0) return null
          return (
            <div
              key={zone.zone}
              className={`${ZONE_COLORS[zone.zone]} flex items-center justify-center`}
              style={{ width: `${zone.percentage}%` }}
              title={`${zone.label}: ${zone.percentage.toFixed(1)}%`}
            >
              {zone.percentage > 10 && (
                <span className="text-white text-xs font-medium">
                  {zone.percentage.toFixed(0)}%
                </span>
              )}
            </div>
          )
        })}
      </div>

      {/* Zone details */}
      <div className="grid grid-cols-5 gap-2">
        {effort.zone_breakdown.map((zone) => (
          <div key={zone.zone} className="text-center">
            <div className={`text-xs font-medium ${ZONE_TEXT_COLORS[zone.zone]}`}>
              {zone.label.split(' - ')[1] || zone.label}
            </div>
            <div className="text-sm font-bold text-gray-900">
              {formatTime(zone.time_seconds)}
            </div>
            <div className="text-xs text-gray-500">
              {zone.percentage.toFixed(1)}%
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
