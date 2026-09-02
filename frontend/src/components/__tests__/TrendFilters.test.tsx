import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import TrendFilters from '../TrendFilters'

describe('TrendFilters', () => {
  const defaultProps = {
    activityType: '',
    distanceBucket: '',
    aggregation: 'weekly',
    startDate: '',
    endDate: '',
    onActivityTypeChange: vi.fn(),
    onDistanceBucketChange: vi.fn(),
    onAggregationChange: vi.fn(),
    onStartDateChange: vi.fn(),
    onEndDateChange: vi.fn(),
    onDateRangeChange: vi.fn(),
    onClearFilters: vi.fn(),
  }

  it('renders activity type selector', () => {
    render(<TrendFilters {...defaultProps} />)
    expect(screen.getByText(/activity type/i)).toBeInTheDocument()
  })

  it('renders distance bucket selector', () => {
    render(<TrendFilters {...defaultProps} />)
    expect(screen.getByLabelText(/distance/i)).toBeInTheDocument()
  })

  it('renders aggregation selector', () => {
    render(<TrendFilters {...defaultProps} />)
    expect(screen.getByText(/aggregation/i)).toBeInTheDocument()
  })

  it('calls onActivityTypeChange when activity type changes', () => {
    render(<TrendFilters {...defaultProps} />)
    const activitySelect = screen.getAllByRole('combobox')[0]
    fireEvent.change(activitySelect, { target: { value: 'Run' } })
    expect(defaultProps.onActivityTypeChange).toHaveBeenCalledWith('Run')
  })

  it('calls onDistanceBucketChange when distance bucket changes', () => {
    render(<TrendFilters {...defaultProps} />)
    const distanceSelect = screen.getAllByRole('combobox')[1]
    fireEvent.change(distanceSelect, { target: { value: '5K' } })
    expect(defaultProps.onDistanceBucketChange).toHaveBeenCalledWith('5K')
  })

  it('calls onAggregationChange when aggregation changes', () => {
    render(<TrendFilters {...defaultProps} />)
    const aggregationSelect = screen.getAllByRole('combobox')[2]
    fireEvent.change(aggregationSelect, { target: { value: 'monthly' } })
    expect(defaultProps.onAggregationChange).toHaveBeenCalledWith('monthly')
  })

  it('shows current values', () => {
    render(<TrendFilters {...defaultProps} activityType="Run" distanceBucket="10K" aggregation="daily" />)
    const selects = screen.getAllByRole('combobox')
    expect((selects[0] as HTMLSelectElement).value).toBe('Run')
    expect((selects[1] as HTMLSelectElement).value).toBe('10K')
    expect((selects[2] as HTMLSelectElement).value).toBe('daily')
  })

  it('preset click emits BOTH dates via a single onDateRangeChange call', () => {
    render(<TrendFilters {...defaultProps} />)
    fireEvent.click(screen.getByRole('button', { name: 'Last 30 days' }))
    expect(defaultProps.onDateRangeChange).toHaveBeenCalledTimes(1)
    const [start, end] = defaultProps.onDateRangeChange.mock.calls[0]
    expect(start).not.toBe('')
    expect(end).not.toBe('')
    expect(new Date(start).getTime()).toBeLessThan(new Date(end).getTime())
  })

  it("'All time' emits empty start and end via onDateRangeChange", () => {
    render(<TrendFilters {...defaultProps} />)
    fireEvent.click(screen.getByRole('button', { name: 'All time' }))
    expect(defaultProps.onDateRangeChange).toHaveBeenCalledWith('', '')
    expect(defaultProps.onStartDateChange).not.toHaveBeenCalled()
    expect(defaultProps.onEndDateChange).not.toHaveBeenCalled()
  })
})
