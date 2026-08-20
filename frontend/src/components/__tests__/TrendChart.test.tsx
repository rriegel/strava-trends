import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import TrendChart from '../TrendChart'
import type { TrendData } from '../../types'

const mockTrendData: TrendData = {
  metric_type: 'average_speed',
  data_points: [
    { date: '2024-01-01', value: 3.2 },
    { date: '2024-01-08', value: 3.3 },
    { date: '2024-01-15', value: 3.4 },
    { date: '2024-01-22', value: 3.5 },
  ],
  aggregated_data: [
    { period: '2024-01-07', value: 3.25, min: 3.2, max: 3.3, count: 2 },
    { period: '2024-01-21', value: 3.45, min: 3.4, max: 3.5, count: 2 },
  ],
  trend: { slope: 0.015, direction: 'increasing', r_squared: 0.92 },
}

describe('TrendChart', () => {
  it('renders chart title', () => {
    render(<TrendChart data={mockTrendData} title="Average Speed" />)
    expect(screen.getByText('Average Speed')).toBeInTheDocument()
  })

  it('renders without errors when data is present', () => {
    const { container } = render(<TrendChart data={mockTrendData} title="Speed" />)
    // ResponsiveContainer renders a div wrapper in jsdom (no SVG without real dimensions)
    expect(container.firstChild).toBeInTheDocument()
  })

  it('shows empty state when no data points', () => {
    const emptyData: TrendData = {
      metric_type: 'average_speed',
      data_points: [],
      aggregated_data: [],
      trend: { slope: 0, direction: 'stable', r_squared: 0 },
    }
    render(<TrendChart data={emptyData} title="Speed" />)
    expect(screen.getByText(/no data/i)).toBeInTheDocument()
  })

  it('shows trend direction indicator', () => {
    render(<TrendChart data={mockTrendData} title="Speed" showTrend />)
    expect(screen.getByText(/increasing/i)).toBeInTheDocument()
  })

  it('renders aggregated mode without errors', () => {
    const { container } = render(
      <TrendChart data={mockTrendData} title="Speed" showAggregated />
    )
    expect(container.firstChild).toBeInTheDocument()
  })
})
