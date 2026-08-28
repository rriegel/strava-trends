interface TrendFiltersProps {
  activityType: string
  distanceBucket: string
  aggregation: string
  startDate: string
  endDate: string
  onActivityTypeChange: (value: string) => void
  onDistanceBucketChange: (value: string) => void
  onAggregationChange: (value: string) => void
  onStartDateChange: (value: string) => void
  onEndDateChange: (value: string) => void
  onClearFilters: () => void
}

export default function TrendFilters({
  activityType,
  distanceBucket,
  aggregation,
  startDate,
  endDate,
  onActivityTypeChange,
  onDistanceBucketChange,
  onAggregationChange,
  onStartDateChange,
  onEndDateChange,
  onClearFilters,
}: TrendFiltersProps) {
  const hasActiveFilters = activityType || distanceBucket || startDate || endDate

  const setDateRange = (days: number) => {
    const end = new Date()
    const start = new Date()
    start.setDate(start.getDate() - days)
    onStartDateChange(start.toISOString().split('T')[0])
    onEndDateChange(end.toISOString().split('T')[0])
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="flex flex-col gap-2">
          <label htmlFor="trend-activity-type" className="text-sm font-medium text-gray-700">Activity Type</label>
          <select
            id="trend-activity-type"
            value={activityType}
            onChange={(e) => onActivityTypeChange(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-lg bg-white text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">All Activities</option>
            <option value="Run">Run</option>
            <option value="Ride">Ride</option>
            <option value="Swim">Swim</option>
          </select>
        </div>

        <div className="flex flex-col gap-2">
          <label htmlFor="trend-distance" className="text-sm font-medium text-gray-700">Distance</label>
          <select
            id="trend-distance"
            value={distanceBucket}
            onChange={(e) => onDistanceBucketChange(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-lg bg-white text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">All Distances</option>
            <option value="5K">5K</option>
            <option value="10K">10K</option>
            <option value="Half">Half Marathon</option>
            <option value="Marathon">Marathon</option>
          </select>
        </div>

        <div className="flex flex-col gap-2">
          <label htmlFor="trend-aggregation" className="text-sm font-medium text-gray-700">Aggregation</label>
          <select
            id="trend-aggregation"
            value={aggregation}
            onChange={(e) => onAggregationChange(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-lg bg-white text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="daily">Daily</option>
            <option value="weekly">Weekly</option>
            <option value="monthly">Monthly</option>
          </select>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="flex flex-col gap-2">
          <label htmlFor="trend-start-date" className="text-sm font-medium text-gray-700">Start Date</label>
          <input
            id="trend-start-date"
            type="date"
            value={startDate}
            onChange={(e) => onStartDateChange(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-lg bg-white text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div className="flex flex-col gap-2">
          <label htmlFor="trend-end-date" className="text-sm font-medium text-gray-700">End Date</label>
          <input
            id="trend-end-date"
            type="date"
            value={endDate}
            onChange={(e) => onEndDateChange(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-lg bg-white text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>

      <div className="flex flex-wrap gap-2 items-center">
        <span className="text-sm font-medium text-gray-700">Quick presets:</span>
        <button
          type="button"
          onClick={() => setDateRange(30)}
          className="px-3 py-1 text-sm border border-gray-300 rounded-lg bg-white text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          Last 30 days
        </button>
        <button
          type="button"
          onClick={() => setDateRange(90)}
          className="px-3 py-1 text-sm border border-gray-300 rounded-lg bg-white text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          Last 3 months
        </button>
        <button
          type="button"
          onClick={() => setDateRange(365)}
          className="px-3 py-1 text-sm border border-gray-300 rounded-lg bg-white text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          Last year
        </button>
        <button
          type="button"
          onClick={() => {
            onStartDateChange('')
            onEndDateChange('')
          }}
          className="px-3 py-1 text-sm border border-gray-300 rounded-lg bg-white text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          All time
        </button>

        {hasActiveFilters && (
          <button
            type="button"
            onClick={onClearFilters}
            className="ml-auto px-3 py-1 text-sm border border-red-300 rounded-lg bg-white text-red-700 hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-red-500"
          >
            Clear filters
          </button>
        )}
      </div>
    </div>
  )
}
