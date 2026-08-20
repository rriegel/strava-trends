interface TrendFiltersProps {
  activityType: string
  distanceBucket: string
  aggregation: string
  onActivityTypeChange: (value: string) => void
  onDistanceBucketChange: (value: string) => void
  onAggregationChange: (value: string) => void
}

export default function TrendFilters({
  activityType,
  distanceBucket,
  aggregation,
  onActivityTypeChange,
  onDistanceBucketChange,
  onAggregationChange,
}: TrendFiltersProps) {
  return (
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
  )
}
