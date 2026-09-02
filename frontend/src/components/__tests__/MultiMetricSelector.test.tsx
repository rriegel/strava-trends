import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import MultiMetricSelector, { AVAILABLE_METRICS } from '../MultiMetricSelector'

describe('MultiMetricSelector', () => {
  it('renders all available metrics', () => {
    render(
      <MultiMetricSelector
        metrics={AVAILABLE_METRICS}
        selected={['average_speed']}
        onChange={() => {}}
      />
    )
    AVAILABLE_METRICS.forEach((metric) => {
      expect(screen.getByRole('button', { name: new RegExp(metric.label) })).toBeInTheDocument()
    })
  })

  it('shows selection count', () => {
    render(
      <MultiMetricSelector
        metrics={AVAILABLE_METRICS}
        selected={['average_speed', 'average_heartrate']}
        onChange={() => {}}
        maxSelections={3}
      />
    )
    expect(screen.getByText('2/3 selected')).toBeInTheDocument()
  })

  it('allows selecting a metric', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()
    render(
      <MultiMetricSelector
        metrics={AVAILABLE_METRICS}
        selected={['average_speed']}
        onChange={onChange}
        maxSelections={3}
      />
    )
    await user.click(screen.getByRole('button', { name: /Avg Heart Rate/ }))
    expect(onChange).toHaveBeenCalledWith(['average_speed', 'average_heartrate'])
  })

  it('allows deselecting a metric', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()
    render(
      <MultiMetricSelector
        metrics={AVAILABLE_METRICS}
        selected={['average_speed', 'average_heartrate']}
        onChange={onChange}
      />
    )
    await user.click(screen.getByRole('button', { name: /Avg Heart Rate/ }))
    expect(onChange).toHaveBeenCalledWith(['average_speed'])
  })

  it('does not deselect the last remaining metric', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()
    render(
      <MultiMetricSelector
        metrics={AVAILABLE_METRICS}
        selected={['average_speed']}
        onChange={onChange}
      />
    )
    await user.click(screen.getByRole('button', { name: /Avg Pace/ }))
    expect(onChange).not.toHaveBeenCalled()
  })

  it('does not exceed maxSelections', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()
    render(
      <MultiMetricSelector
        metrics={AVAILABLE_METRICS}
        selected={['average_speed', 'average_heartrate', 'average_cadence']}
        onChange={onChange}
        maxSelections={3}
      />
    )
    await user.click(screen.getByRole('button', { name: /Elevation Gain/ }))
    expect(onChange).not.toHaveBeenCalled()
    // The unselectable button is disabled
    expect(screen.getByRole('button', { name: /Elevation Gain/ })).toBeDisabled()
  })
})
