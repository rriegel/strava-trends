import StatCard from '../components/StatCard'

export default function Dashboard() {
  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Dashboard</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard title="This Week" value="--" subtitle="Activities" />
        <StatCard title="Avg Pace" value="--:--" subtitle="/km" />
        <StatCard title="Total Distance" value="0 km" subtitle="Last 7 days" />
        <StatCard title="Fitness Trend" value="--" subtitle="vs last month" />
      </div>
    </div>
  )
}
