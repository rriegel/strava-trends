import StatCard from '../components/StatCard'
import CalendarHeatmap from '../components/CalendarHeatmap'
import { useCalendar } from '../hooks/useCalendar'
import { formatDistance, formatDuration } from '../utils/format'

export default function Dashboard() {
  // Rolling last-365-days window matches the heatmap's built-in range
  const { data, isLoading, error } = useCalendar()
  const summary = data?.summary

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Dashboard</h1>
      {isLoading && (
        <div className="flex items-center justify-center py-12 mb-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
        </div>
      )}
      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg mb-8">
          <p className="text-red-800 text-sm">Failed to load dashboard stats</p>
        </div>
      )}
      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <StatCard
            title="Total Activities"
            value={summary.total_activities.toString()}
            subtitle="last 12 months"
          />
          <StatCard
            title="Total Distance"
            value={formatDistance(summary.total_distance)}
            subtitle="last 12 months"
          />
          <StatCard
            title="Longest Streak"
            value={`${summary.longest_streak} day${summary.longest_streak === 1 ? '' : 's'}`}
            subtitle="consecutive activities"
          />
          <StatCard
            title="Most Active Day"
            value={summary.most_active_day || '--'}
            subtitle={`time: ${formatDuration(summary.total_moving_time)}`}
          />
        </div>
      )}
      <CalendarHeatmap />
    </div>
  )
}
