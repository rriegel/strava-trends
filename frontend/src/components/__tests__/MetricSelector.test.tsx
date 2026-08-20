import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import MetricSelector from '../MetricSelector'

const metrics = [
  { value: 'average_speed', label: 'Average Speed' },
  { value: 'average_heartrate', label: 'Heart Rate' },
  { value: 'hr_pace_ratio', label: 'HR/Pace Ratio' },
]

describe('MetricSelector', () => {
  it('renders metric options', () => {
    render(<MetricSelector metrics={metrics} value="average_speed" onChange={() => {}} />)
    expect(screen.getByText('Average Speed')).toBeInTheDocument()
    expect(screen.getByText('Heart Rate')).toBeInTheDocument()
  })

  it('calls onChange when a different metric is selected', () => {
    const onChange = vi.fn()
    render(<MetricSelector metrics={metrics} value="average_speed" onChange={onChange} />)
    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'average_heartrate' } })
    expect(onChange).toHaveBeenCalledWith('average_heartrate')
  })

  it('shows current selection', () => {
    render(<MetricSelector metrics={metrics} value="hr_pace_ratio" onChange={() => {}} />)
    const select = screen.getByRole('combobox') as HTMLSelectElement
    expect(select.value).toBe('hr_pace_ratio')
  })

  it('renders label when provided', () => {
    render(
      <MetricSelector 
        metrics={metrics} 
        value="average_speed" 
        onChange={() => {}} 
        label="Select Metric" 
      />
    )
    expect(screen.getByText('Select Metric')).toBeInTheDocument()
  })
})
