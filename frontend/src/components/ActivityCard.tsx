import { useState } from 'react'
import { formatDistance, formatDuration, formatPace, formatElevation, formatHeartrate } from '../utils/format'
import type { ActivitySummary } from '../api/activities'
import ConfirmDialog from './ConfirmDialog'

interface ActivityCardProps {
  activity: ActivitySummary
  onClick?: (activity: ActivitySummary) => void
  onDelete?: (activityId: number) => void
}

export default function ActivityCard({ activity, onClick, onDelete }: ActivityCardProps) {
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)

  const activityTypeIcons: Record<string, string> = {
    Run: '🏃',
    Ride: '🚴',
    Swim: '🏊',
    Walk: '🚶',
    Hike: '🥾',
    AlpineSki: '⛷️',
    BackcountrySki: '🎿',
    Snowboard: '🏂',
    Workout: '💪',
    WeightTraining: '🏋️',
  }

  const icon = activityTypeIcons[activity.type] || '🏅'

  const handleDeleteClick = (e: React.MouseEvent) => {
    e.stopPropagation()
    setShowDeleteConfirm(true)
  }

  const handleConfirmDelete = () => {
    setShowDeleteConfirm(false)
    onDelete?.(activity.id)
  }

  return (
    <>
      <div className="bg-white rounded-lg shadow-sm border p-4 hover:shadow-md transition-shadow">
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-start space-x-3 flex-1 min-w-0">
            <span className="text-2xl">{icon}</span>
            <div className="flex-1 min-w-0">
              <h3
                className="font-semibold text-gray-900 truncate cursor-pointer hover:text-blue-600"
                onClick={() => onClick?.(activity)}
              >
                {activity.name}
              </h3>
              <div className="flex items-center space-x-2 text-sm text-gray-500 mt-1">
                <span>{new Date(activity.start_date_local).toLocaleDateString()}</span>
                {activity.type && <span>• {activity.type}</span>}
              </div>
            </div>
          </div>
          {onDelete && (
            <button
              onClick={handleDeleteClick}
              className="text-gray-400 hover:text-red-600 transition-colors p-1"
              aria-label="Delete activity"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                />
              </svg>
            </button>
          )}
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
          {activity.distance && (
            <div>
              <div className="text-gray-500 text-xs">Distance</div>
              <div className="font-semibold text-gray-900">
                {formatDistance(activity.distance)}
              </div>
            </div>
          )}

          {activity.moving_time && (
            <div>
              <div className="text-gray-500 text-xs">Time</div>
              <div className="font-semibold text-gray-900">
                {formatDuration(activity.moving_time)}
              </div>
            </div>
          )}

          {activity.average_speed && (
            <div>
              <div className="text-gray-500 text-xs">Pace</div>
              <div className="font-semibold text-gray-900">
                {formatPace(activity.average_speed)}/km
              </div>
            </div>
          )}

          {activity.total_elevation_gain && activity.total_elevation_gain > 0 && (
            <div>
              <div className="text-gray-500 text-xs">Elevation</div>
              <div className="font-semibold text-gray-900">
                {formatElevation(activity.total_elevation_gain)}
              </div>
            </div>
          )}

          {activity.average_heartrate && (
            <div>
              <div className="text-gray-500 text-xs">Avg HR</div>
              <div className="font-semibold text-gray-900">
                {formatHeartrate(activity.average_heartrate)}
              </div>
            </div>
          )}

          {activity.suffer_score && (
            <div>
              <div className="text-gray-500 text-xs">Suffer Score</div>
              <div className="font-semibold text-gray-900">{activity.suffer_score}</div>
            </div>
          )}

          {activity.distance_bucket && (
            <div>
              <div className="text-gray-500 text-xs">Distance Bucket</div>
              <div className="font-semibold text-gray-900">{activity.distance_bucket}</div>
            </div>
          )}

          {activity.effort_zone && (
            <div>
              <div className="text-gray-500 text-xs">Effort Zone</div>
              <div className="font-semibold text-gray-900 capitalize">{activity.effort_zone}</div>
            </div>
          )}
        </div>

        {activity.device_name && (
          <div className="mt-3 pt-3 border-t text-xs text-gray-500">
            {activity.device_name}
          </div>
        )}
      </div>

      <ConfirmDialog
        isOpen={showDeleteConfirm}
        title="Delete Activity"
        message="Are you sure you want to delete this activity? This action cannot be undone."
        confirmLabel="Delete"
        cancelLabel="Cancel"
        onConfirm={handleConfirmDelete}
        onCancel={() => setShowDeleteConfirm(false)}
        variant="danger"
      />
    </>
  )
}
