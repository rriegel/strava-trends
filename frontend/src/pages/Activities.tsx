import { useState } from 'react'
import FileUpload from '../components/FileUpload'
import ActivityList from '../components/ActivityList'
import ActivityFilters from '../components/ActivityFilters'
import ActivityDetail from '../components/ActivityDetail'
import { useActivities } from '../hooks/useActivities'
import type { ActivitySummary } from '../api/activities'

export default function Activities() {
  const [showUpload, setShowUpload] = useState(false)
  const [selectedActivityId, setSelectedActivityId] = useState<number | null>(null)
  const { activities, pagination, isLoading, filters, updateFilters, setPage, deleteActivity, refresh } =
    useActivities({ per_page: 20, sort_by: 'start_date', sort_order: 'desc' })

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
