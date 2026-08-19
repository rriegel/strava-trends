import { useEffect, useState } from 'react'
import { activitiesApi, type ActivityDetail as ActivityDetailType } from '../api/activities'
import { formatDistance, formatDuration, formatPace, formatElevation, formatHeartrate } from '../utils/format'
import ActivityMap from './ActivityMap'
import EffortBreakdown from './EffortBreakdown'

interface ActivityDetailProps {
  activityId: number
  onClose: () => void
}

export default function ActivityDetail({ activityId, onClose }: ActivityDetailProps) {
  const [activity, setActivity] = useState<ActivityDetailType | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchDetail = async () => {
      setIsLoading(true)
      setError(null)
      try {
        const data = await activitiesApi.getDetail(activityId)
        setActivity(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load activity')
      } finally {
        setIsLoading(false)
      }
    }

    fetchDetail()
  }, [activityId])

  // Close on escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleEscape)
    return () => document.removeEventListener('keydown', handleEscape)
  }, [onClose])

  if (isLoading) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
        <div className="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] flex flex-col">
          <div className="p-6 animate-pulse space-y-4">
            <div className="h-8 bg-gray-200 rounded w-3/4"></div>
            <div className="h-4 bg-gray-200 rounded w-1/2"></div>
            <div className="grid grid-cols-2 gap-4">
              {[...Array(6)].map((_, i) => (
                <div key={i} className="h-16 bg-gray-200 rounded"></div>
              ))}
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (error || !activity) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
        <div className="bg-white rounded-lg max-w-md w-full p-6">
          <h2 className="text-lg font-semibold text-red-600 mb-2">Error</h2>
          <p className="text-gray-700 mb-4">{error || 'Activity not found'}</p>
          <button
            onClick={onClose}
            className="w-full bg-gray-200 text-gray-800 py-2 rounded-md hover:bg-gray-300"
          >
            Close
          </button>
        </div>
      </div>
    )
  }

  return (
    <div 
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
      onClick={onClose}
    >
      <div 
        className="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Sticky header */}
        <div className="sticky top-0 bg-white border-b px-6 py-4 flex items-center justify-between rounded-t-lg">
          <h2 className="text-xl font-bold text-gray-900">{activity.name}</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
            aria-label="Close"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        {/* Scrollable content */}
        <div className="overflow-y-auto flex-1 p-6 space-y-6">
          {/* Route Map */}
          <ActivityMap activityId={activity.id} hasStreams={activity.has_streams} />

          <div className="flex items-center space-x-4 text-sm text-gray-600">
            <span>{new Date(activity.start_date_local).toLocaleString()}</span>
            <span>•</span>
            <span>{activity.type}</span>
            {activity.sport_type && activity.sport_type !== activity.type && (
              <>
                <span>•</span>
                <span>{activity.sport_type}</span>
              </>
            )}
          </div>

          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {activity.distance && (
              <div className="bg-gray-50 rounded-lg p-4">
                <div className="text-sm text-gray-500">Distance</div>
                <div className="text-2xl font-bold text-gray-900">
                  {formatDistance(activity.distance)}
                </div>
              </div>
            )}

            {activity.moving_time && (
              <div className="bg-gray-50 rounded-lg p-4">
                <div className="text-sm text-gray-500">Moving Time</div>
                <div className="text-2xl font-bold text-gray-900">
                  {formatDuration(activity.moving_time)}
                </div>
              </div>
            )}

            {activity.elapsed_time && activity.elapsed_time !== activity.moving_time && (
              <div className="bg-gray-50 rounded-lg p-4">
                <div className="text-sm text-gray-500">Elapsed Time</div>
                <div className="text-2xl font-bold text-gray-900">
                  {formatDuration(activity.elapsed_time)}
                </div>
              </div>
            )}

            {activity.average_speed && (
              <div className="bg-gray-50 rounded-lg p-4">
                <div className="text-sm text-gray-500">Avg Pace</div>
                <div className="text-2xl font-bold text-gray-900">
                  {formatPace(activity.average_speed)}/km
                </div>
              </div>
            )}

            {activity.total_elevation_gain && activity.total_elevation_gain > 0 && (
              <div className="bg-gray-50 rounded-lg p-4">
                <div className="text-sm text-gray-500">Elevation Gain</div>
                <div className="text-2xl font-bold text-gray-900">
                  {formatElevation(activity.total_elevation_gain)}
                </div>
              </div>
            )}

            {activity.average_heartrate && (
              <div className="bg-gray-50 rounded-lg p-4">
                <div className="text-sm text-gray-500">Avg Heart Rate</div>
                <div className="text-2xl font-bold text-gray-900">
                  {formatHeartrate(activity.average_heartrate)}
                </div>
              </div>
            )}

            {activity.max_heartrate && (
              <div className="bg-gray-50 rounded-lg p-4">
                <div className="text-sm text-gray-500">Max Heart Rate</div>
                <div className="text-2xl font-bold text-gray-900">
                  {formatHeartrate(activity.max_heartrate)}
                </div>
              </div>
            )}

            {activity.average_cadence && (
              <div className="bg-gray-50 rounded-lg p-4">
                <div className="text-sm text-gray-500">Avg Cadence</div>
                <div className="text-2xl font-bold text-gray-900">
                  {activity.average_cadence} spm
                </div>
              </div>
            )}

            {activity.average_watts && (
              <div className="bg-gray-50 rounded-lg p-4">
                <div className="text-sm text-gray-500">Avg Power</div>
                <div className="text-2xl font-bold text-gray-900">
                  {Math.round(activity.average_watts)} W
                </div>
              </div>
            )}

            {activity.suffer_score && (
              <div className="bg-gray-50 rounded-lg p-4">
                <div className="text-sm text-gray-500">Suffer Score</div>
                <div className="text-2xl font-bold text-gray-900">
                  {activity.suffer_score}
                </div>
              </div>
            )}

            {activity.kilojoules && (
              <div className="bg-gray-50 rounded-lg p-4">
                <div className="text-sm text-gray-500">Energy</div>
                <div className="text-2xl font-bold text-gray-900">
                  {Math.round(activity.kilojoules)} kJ
                </div>
              </div>
            )}
          </div>

          {(activity.distance_bucket || activity.effort_zone || activity.terrain_type) && (
            <div className="border-t pt-4">
              <h3 className="font-semibold text-gray-900 mb-2">Classifications</h3>
              <div className="flex flex-wrap gap-2">
                {activity.distance_bucket && (
                  <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm">
                    {activity.distance_bucket}
                  </span>
                )}
                {activity.effort_zone && (
                  <span className="px-3 py-1 bg-purple-100 text-purple-800 rounded-full text-sm capitalize">
                    {activity.effort_zone}
                  </span>
                )}
                {activity.terrain_type && (
                  <span className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm capitalize">
                    {activity.terrain_type}
                  </span>
                )}
              </div>
            </div>
          )}

          <EffortBreakdown activityId={activity.id} hasHeartrate={activity.has_heartrate} />

          {activity.device_name && (
            <div className="border-t pt-4 text-sm text-gray-600">
              <span className="font-medium">Device:</span> {activity.device_name}
            </div>
          )}

          {activity.computed_metrics && activity.computed_metrics.length > 0 && (
            <div className="border-t pt-4">
              <h3 className="font-semibold text-gray-900 mb-2">Computed Metrics</h3>
              <div className="space-y-2">
                {activity.computed_metrics.map((metric, idx) => (
                  <div key={idx} className="flex justify-between text-sm">
                    <span className="text-gray-600">{metric.metric_type}</span>
                    <span className="font-medium text-gray-900">{metric.value}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
