import { useState } from 'react'
import type { ActivityFilters as Filters } from '../api/activities'

interface ActivityFiltersProps {
  filters: Filters
  onFilterChange: (filters: Partial<Filters>) => void
}

export default function ActivityFilters({ filters, onFilterChange }: ActivityFiltersProps) {
  const [isExpanded, setIsExpanded] = useState(false)

  const activityTypes = ['Run', 'Ride', 'Swim', 'Walk', 'Hike', 'Workout']
  const distanceBuckets = ['5K', '10K', 'Half Marathon', 'Marathon', 'Ultra']
  const effortZones = ['easy', 'moderate', 'hard', 'very_hard']

  const hasActiveFilters =
    filters.type ||
    filters.distance_bucket ||
    filters.effort_zone ||
    filters.start_date ||
    filters.end_date

  const clearFilters = () => {
    onFilterChange({
      type: undefined,
      distance_bucket: undefined,
      effort_zone: undefined,
      start_date: undefined,
      end_date: undefined,
    })
  }

  return (
    <div className="bg-white rounded-lg shadow-sm border p-4">
      <div className="flex items-center justify-between mb-3">
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="flex items-center space-x-2 text-sm font-medium text-gray-700 hover:text-gray-900"
        >
          <svg
            className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-90' : ''}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 5l7 7-7 7"
            />
          </svg>
          <span>Filters</span>
          {hasActiveFilters && (
            <span className="bg-blue-100 text-blue-800 text-xs px-2 py-0.5 rounded-full">
              Active
            </span>
          )}
        </button>
        {hasActiveFilters && (
          <button
            onClick={clearFilters}
            className="text-sm text-gray-500 hover:text-gray-700"
          >
            Clear all
          </button>
        )}
      </div>

      {isExpanded && (
        <div className="space-y-4 pt-3 border-t">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Activity Type
            </label>
            <select
              value={filters.type || ''}
              onChange={(e) => onFilterChange({ type: e.target.value || undefined })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">All Types</option>
              {activityTypes.map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Distance Bucket
            </label>
            <select
              value={filters.distance_bucket || ''}
              onChange={(e) =>
                onFilterChange({ distance_bucket: e.target.value || undefined })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">All Distances</option>
              {distanceBuckets.map((bucket) => (
                <option key={bucket} value={bucket}>
                  {bucket}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Effort Zone
            </label>
            <select
              value={filters.effort_zone || ''}
              onChange={(e) => onFilterChange({ effort_zone: e.target.value || undefined })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">All Zones</option>
              {effortZones.map((zone) => (
                <option key={zone} value={zone} className="capitalize">
                  {zone.charAt(0).toUpperCase() + zone.slice(1)}
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="start-date" className="block text-sm font-medium text-gray-700 mb-1">
                Start Date
              </label>
              <input
                id="start-date"
                type="date"
                value={filters.start_date || ''}
                onChange={(e) =>
                  onFilterChange({ start_date: e.target.value || undefined })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label htmlFor="end-date" className="block text-sm font-medium text-gray-700 mb-1">
                End Date
              </label>
              <input
                id="end-date"
                type="date"
                value={filters.end_date || ''}
                onChange={(e) =>
                  onFilterChange({ end_date: e.target.value || undefined })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
