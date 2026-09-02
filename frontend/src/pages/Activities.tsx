import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import FileUpload from '../components/FileUpload'
import ActivityList from '../components/ActivityList'
import ActivityFilters from '../components/ActivityFilters'
import ActivityDetail from '../components/ActivityDetail'
import { useActivities } from '../hooks/useActivities'
import type { ActivitySummary } from '../api/activities'

export default function Activities() {
  const [showUpload, setShowUpload] = useState(false)
  const [selectedActivityId, setSelectedActivityId] = useState<number | null>(null)
  const [searchParams, setSearchParams] = useSearchParams()

  // Support deep links like /activities?route_id=3 (from the route map popup)
  const routeIdParam = searchParams.get('route_id')
  const { activities, pagination, isLoading, filters, updateFilters, setPage, deleteActivity, refresh } =
    useActivities({
      per_page: 20,
      sort_by: 'start_date',
      sort_order: 'desc',
      route_id: routeIdParam ? parseInt(routeIdParam, 10) : undefined,
    })

  // Show a dismissible banner when activities are filtered by route
  const [routeFilterActive, setRouteFilterActive] = useState(false)
  useEffect(() => {
    setRouteFilterActive(!!routeIdParam)
  }, [routeIdParam])

  const clearRouteFilter = () => {
    searchParams.delete('route_id')
    setSearchParams(searchParams, { replace: true })
    updateFilters({ route_id: undefined })
  }

  const handleActivityClick = (activity: ActivitySummary) => {
    setSelectedActivityId(activity.id)
  }

  const handleActivityDelete = async (activityId: number) => {
    try {
      await deleteActivity(activityId)
    } catch (err) {
      console.error('Failed to delete activity:', err)
      alert('Failed to delete activity')
    }
  }

  const handleUploadComplete = () => {
    refresh()
    setShowUpload(false)
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Activities</h1>
        <button
          onClick={() => setShowUpload(!showUpload)}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
        >
          {showUpload ? 'Hide Upload' : 'Upload Files'}
        </button>
      </div>

      {showUpload && (
        <div className="bg-white rounded-lg shadow-sm border p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Import Activities</h2>
          <FileUpload onUploadComplete={handleUploadComplete} />
        </div>
      )}

      <div className="mb-4">
        {routeFilterActive && (
          <div className="flex items-center justify-between bg-blue-50 border border-blue-200 rounded-lg px-4 py-2 mb-3">
            <p className="text-sm text-blue-800">
              Showing activities on the selected route
            </p>
            <button
              type="button"
              onClick={clearRouteFilter}
              className="text-sm text-blue-600 hover:text-blue-800 font-medium"
            >
              Show all activities
            </button>
          </div>
        )}
        <ActivityFilters filters={filters} onFilterChange={updateFilters} />
      </div>

      <ActivityList
        activities={activities}
        pagination={pagination}
        isLoading={isLoading}
        onActivityClick={handleActivityClick}
        onActivityDelete={handleActivityDelete}
        onPageChange={setPage}
      />

      {selectedActivityId && (
        <ActivityDetail
          activityId={selectedActivityId}
          onClose={() => setSelectedActivityId(null)}
        />
      )}
    </div>
  )
}
