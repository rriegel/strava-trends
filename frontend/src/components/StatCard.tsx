import { cn } from '../utils/classnames'

interface StatCardProps {
  title: string
  value: string
  subtitle?: string
  trend?: { direction: string; value: string }
}

export default function StatCard({ title, value, subtitle, trend }: StatCardProps) {
  return (
    <div className="bg-white rounded-lg shadow-sm border p-6">
      <p className="text-sm font-medium text-gray-500">{title}</p>
      <p className="mt-2 text-3xl font-bold text-gray-900">{value}</p>
      {subtitle && <p className="mt-1 text-sm text-gray-500">{subtitle}</p>}
      {trend && (
        <p className={cn(
          'mt-2 text-sm font-medium',
          trend.direction === 'increasing' ? 'text-green-600' :
          trend.direction === 'decreasing' ? 'text-red-600' : 'text-gray-500'
        )}>
          {trend.value}
        </p>
      )}
    </div>
  )
}
