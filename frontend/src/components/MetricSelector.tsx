interface MetricSelectorProps {
  metrics: { value: string; label: string }[]
  value: string
  onChange: (value: string) => void
  label?: string
}

export default function MetricSelector({ metrics, value, onChange, label }: MetricSelectorProps) {
  return (
    <div className="flex flex-col gap-2">
      {label && (
        <label className="text-sm font-medium text-gray-700">{label}</label>
      )}
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="px-3 py-2 border border-gray-300 rounded-lg bg-white text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
      >
        {metrics.map((metric) => (
          <option key={metric.value} value={metric.value}>
            {metric.label}
          </option>
        ))}
      </select>
    </div>
  )
}
