import type { ActivitySummary, Pagination } from '../api/activities'
import ActivityCard from './ActivityCard'

interface ActivityListProps {
  activities: ActivitySummary[]
  pagination: Pagination | null
  isLoading: boolean
  onActivityClick?: (activity: ActivitySummary) => void
  onActivityDelete?: (activityId: number) => void
  onPageChange?: (page: number) => void
}

export default function ActivityList({
  activities,
  pagination,
  isLoading,
  onActivityClick,
  onActivityDelete,
  onPageChange,
}: ActivityListProps) {
  if (isLoading) {
    return (
      <div className="space-y-4">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="bg-white rounded-lg shadow-sm border p-4 animate-pulse">
            <div className="flex items-start space-x-3 mb-3">
              <div className="w-8 h-8 bg-gray-200 rounded"></div>
              <div className="flex-1">
                <div className="h-5 bg-gray-200 rounded w-3/4 mb-2"></div>
                <div className="h-4 bg-gray-200 rounded w-1/2"></div>
              </div>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {[...Array(4)].map((_, j) => (
                <div key={j}>
                  <div className="h-3 bg-gray-200 rounded w-12 mb-1"></div>
                  <div className="h-4 bg-gray-200 rounded w-16"></div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    )
  }

  if (activities.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-sm border p-12 text-center">
        <svg
          className="mx-auto h-12 w-12 text-gray-400"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
          />
        </svg>
        <h3 className="mt-2 text-sm font-medium text-gray-900">No activities</h3>
        <p className="mt-1 text-sm text-gray-500">
          Get started by uploading your first activity file.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="space-y-4">
        {activities.map((activity) => (
          <ActivityCard
            key={activity.id}
            activity={activity}
            onClick={onActivityClick}
            onDelete={onActivityDelete}
          />
        ))}
      </div>

      {pagination && pagination.total_pages > 1 && (
        <div className="flex items-center justify-between bg-white rounded-lg shadow-sm border p-4">
          <div className="text-sm text-gray-700">
            Showing {((pagination.page - 1) * pagination.per_page) + 1} to{' '}
            {Math.min(pagination.page * pagination.per_page, pagination.total)} of{' '}
            {pagination.total} activities
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={() => onPageChange?.(pagination.page - 1)}
              disabled={pagination.page === 1}
              className="px-3 py-1 text-sm border border-gray-300 rounded-md disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
            >
              Previous
            </button>
            <span className="text-sm text-gray-700">
              Page {pagination.page} of {pagination.total_pages}
            </span>
            <button
              onClick={() => onPageChange?.(pagination.page + 1)}
              disabled={pagination.page === pagination.total_pages}
              className="px-3 py-1 text-sm border border-gray-300 rounded-md disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
