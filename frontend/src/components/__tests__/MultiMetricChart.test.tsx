import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import type { TrendData } from '../../types'

/**
 * Recharts' ResponsiveContainer measures the DOM; jsdom reports 0x0 so the
 * chart never mounts. Mock it (vi.mock is hoisted above all imports) with a
 * pass-through that injects fixed dimensions, and disable line animation so
 * dots render synchronously. The component under test is unchanged.
 */
vi.mock('recharts', async (importOriginal) => {
  const actual = await importOriginal<typeof import('recharts')>()
  const React = await import('react')
  return {
    ...actual,
    ResponsiveContainer: ({ children }: { children: React.ReactElement }) =>
      React.cloneElement(React.Children.only(children), { width: 800, height: 400 }),
  }
})

import MultiMetricChart from '../MultiMetricChart'

// pace value equivalent of 3.0 m/s
const PACE_3_MS = 1000 / 3.0 / 60 // 5.555... decimal min/km

function makeTrendData(overrides: Partial<TrendData> = {}): TrendData {
  return {
    metric_type: 'average_speed',
    unit: 'min/km',
    data_points: [
      { date: '2024-01-01T00:00:00+00:00', value: PACE_3_MS },
      { date: '2024-01-08T00:00:00+00:00', value: 5.4 },
      { date: '2024-01-15T00:00:00+00:00', value: 5.3 },
    ],
    aggregated_data: [],
    trend: { slope: -0.02, direction: 'decreasing', r_squared: 0.9 },
    ...overrides,
  }
}

describe('MultiMetricChart', () => {
  it('renders the title and no-data state', () => {
    render(<MultiMetricChart data={{}} metricTypes={['average_speed']} title="Multi-Metric Trend" />)
    expect(screen.getByText('Multi-Metric Trend')).toBeInTheDocument()
    expect(screen.getByText('No data available')).toBeInTheDocument()
  })

  it('renders chart with data and legend trend from API', () => {
    const data = { average_speed: makeTrendData() }
    const { container } = render(
      <MultiMetricChart data={data} metricTypes={['average_speed']} title="Multi-Metric Trend" />
    )
    expect(screen.getByText('Multi-Metric Trend')).toBeInTheDocument()
    // Legend shows API-provided trend direction and R²
    expect(screen.getByText(/decreasing/i)).toBeInTheDocument()
    expect(screen.getByText(/R²: 0.90/)).toBeInTheDocument()
    expect(container.querySelector('.recharts-line')).not.toBeNull()
  })

  it('colors pace-metric decreasing trend as improving (green)', () => {
    const data = { average_speed: makeTrendData() }
    render(<MultiMetricChart data={data} metricTypes={['average_speed']} title="T" />)
    const badge = screen.getByText(/decreasing/i)
    expect(badge.className).toContain('text-green-600')
  })

  it('colors pace-metric increasing trend as worsening (red)', () => {
    const data = {
      average_speed: makeTrendData({
        trend: { slope: 0.02, direction: 'increasing', r_squared: 0.8 },
      }),
    }
    render(<MultiMetricChart data={data} metricTypes={['average_speed']} title="T" />)
    const badge = screen.getByText(/increasing/i)
    expect(badge.className).toContain('text-red-600')
  })

  it('colors non-pace increasing trend as improving (green)', () => {
    const data = {
      average_heartrate: makeTrendData({
        metric_type: 'average_heartrate',
        data_points: [
          { date: '2024-01-01T00:00:00+00:00', value: 150 },
          { date: '2024-01-08T00:00:00+00:00', value: 152 },
        ],
        trend: { slope: 0.2, direction: 'increasing', r_squared: 0.7 },
      }),
    }
    render(<MultiMetricChart data={data} metricTypes={['average_heartrate']} title="T" />)
    const badge = screen.getByText(/increasing/i)
    expect(badge.className).toContain('text-green-600')
  })

  it('shows stable trend in gray', () => {
    const data = {
      average_speed: makeTrendData({
        trend: { slope: 0.0, direction: 'stable', r_squared: 0.0 },
      }),
    }
    render(<MultiMetricChart data={data} metricTypes={['average_speed']} title="T" />)
    const badge = screen.getByText(/stable/i)
    expect(badge.className).toContain('text-gray-500')
  })

  it('excludes zero pace values from chart data', () => {
    const data = {
      average_speed: makeTrendData({
        data_points: [
          { date: '2024-01-01T00:00:00+00:00', value: PACE_3_MS },
          { date: '2024-01-08T00:00:00+00:00', value: 0 }, // bad data point
          { date: '2024-01-15T00:00:00+00:00', value: 5.3 },
        ],
      }),
    }
    const { container } = render(
      <MultiMetricChart data={data} metricTypes={['average_speed']} title="T" />
    )
    // The zero-valued date must not be plotted: only 2 ticks render
    // (X-axis ticks come from the merged chart data; count is timezone-safe)
    const ticks = Array.from(container.querySelectorAll('.recharts-xAxis .recharts-cartesian-axis-tick'))
    expect(ticks.length).toBe(2)
  })

  it('supports dual Y-axis for two metrics', () => {
    const data = {
      average_speed: makeTrendData(),
      average_heartrate: makeTrendData({
        metric_type: 'average_heartrate',
        data_points: [
          { date: '2024-01-01T00:00:00+00:00', value: 150 },
          { date: '2024-01-08T00:00:00+00:00', value: 152 },
          { date: '2024-01-15T00:00:00+00:00', value: 151 },
        ],
        trend: { slope: 0.1, direction: 'increasing', r_squared: 0.5 },
      }),
    }
    const { container } = render(
      <MultiMetricChart data={data} metricTypes={['average_speed', 'average_heartrate']} title="T" />
    )
    expect(container.querySelectorAll('.recharts-yAxis').length).toBe(2)
    // Both legend labels present (each also appears as a Y-axis label)
    expect(screen.getAllByText('Avg Pace').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('Avg Heart Rate').length).toBeGreaterThanOrEqual(1)
  })
})
