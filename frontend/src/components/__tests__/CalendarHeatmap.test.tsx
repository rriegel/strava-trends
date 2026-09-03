import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import CalendarHeatmap from '../CalendarHeatmap'
import type { CalendarResponse } from '../../api/activities'

// Mock the hook so no API client is involved
vi.mock('../../hooks/useCalendar', () => ({
  useCalendar: vi.fn(),
}))

import { useCalendar } from '../../hooks/useCalendar'
const mockedUseCalendar = vi.mocked(useCalendar)

function makeResponse(overrides: Partial<CalendarResponse> = {}): { data: CalendarResponse } {
  return {
    data: {
      metric: 'distance',
      start_date: '2024-01-01',
      end_date: '2024-12-31',
      summary: {
        total_activities: 10,
        total_distance: 50000,
        total_moving_time: 18000,
        longest_streak: 3,
        most_active_day: 'Saturday',
      },
      data: [
        { date: '2024-03-01', value: 5000, count: 1 },
        { date: '2024-03-02', value: 10000, count: 2 },
      ],
    },
    ...overrides,
  } as { data: CalendarResponse }
}

describe('CalendarHeatmap', () => {
  it('renders the title and metric toggle buttons', () => {
    mockedUseCalendar.mockReturnValue(makeResponse() as never)
    render(<CalendarHeatmap />)
    expect(screen.getByText('Activity Calendar')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Distance' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Activities' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Time' })).toBeInTheDocument()
  })

  it('refetches with the selected metric when toggled', async () => {
    const user = userEvent.setup()
    mockedUseCalendar.mockReturnValue(makeResponse() as never)
    render(<CalendarHeatmap />)

    await user.click(screen.getByRole('button', { name: 'Activities' }))
    expect(mockedUseCalendar).toHaveBeenLastCalledWith({ metric: 'count' })

    await user.click(screen.getByRole('button', { name: 'Time' }))
    expect(mockedUseCalendar).toHaveBeenLastCalledWith({ metric: 'moving_time' })
  })

  it('shows loading state', () => {
    mockedUseCalendar.mockReturnValue({ isLoading: true, error: null, data: undefined } as never)
    render(<CalendarHeatmap />)
    expect(screen.getByText('Activity Calendar')).toBeInTheDocument()
    expect(document.querySelector('.animate-spin')).not.toBeNull()
  })

  it('shows error state', () => {
    mockedUseCalendar.mockReturnValue({
      isLoading: false,
      error: new Error('boom'),
      data: undefined,
    } as never)
    render(<CalendarHeatmap />)
    expect(screen.getByText('Failed to load calendar data')).toBeInTheDocument()
  })

  it('renders a grid of day cells including active days', () => {
    mockedUseCalendar.mockReturnValue(makeResponse() as never)
    const { container } = render(<CalendarHeatmap />)
    // 365+ day cells render as small squares; verify a healthy grid exists
    const cells = container.querySelectorAll('.w-\\[12px\\]')
    expect(cells.length).toBeGreaterThan(300)
    // Month labels render
    expect(container.textContent).toMatch(/Jan|Feb|Mar/)
  })
})
