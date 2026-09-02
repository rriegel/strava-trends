import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import type { CalendarResponse } from '../../api/activities'

vi.mock('../../hooks/useCalendar', () => ({
  useCalendar: vi.fn(),
}))

import Dashboard from '../Dashboard'
import { useCalendar } from '../../hooks/useCalendar'
const mockedUseCalendar = vi.mocked(useCalendar)

function mockCalendar(summary: Partial<CalendarResponse['summary']> = {}) {
  mockedUseCalendar.mockReturnValue({
    isLoading: false,
    error: null,
    data: {
      metric: 'distance',
      start_date: '2025-09-01',
      end_date: '2026-09-01',
      summary: {
        total_activities: 142,
        total_distance: 1250000,
        total_moving_time: 450000,
        longest_streak: 12,
        most_active_day: 'Saturday',
        ...summary,
      },
      data: [],
    },
  } as never)
}

describe('Dashboard', () => {
  it('renders summary stat cards from calendar data', () => {
    mockCalendar()
    render(<Dashboard />)
    expect(screen.getByText('Total Activities')).toBeInTheDocument()
    expect(screen.getByText('142')).toBeInTheDocument()
    expect(screen.getByText('1250.00 km')).toBeInTheDocument()
    expect(screen.getByText('12 days')).toBeInTheDocument()
    expect(screen.getByText('Saturday')).toBeInTheDocument()
  })

  it('formats streak as singular for 1 day', () => {
    mockCalendar({ longest_streak: 1 })
    render(<Dashboard />)
    expect(screen.getByText('1 day')).toBeInTheDocument()
  })

  it('shows placeholder when most_active_day is empty', () => {
    mockCalendar({ most_active_day: '' })
    render(<Dashboard />)
    expect(screen.getByText('--')).toBeInTheDocument()
  })

  it('shows loading spinner while fetching', () => {
    mockedUseCalendar.mockReturnValue({ isLoading: true, error: null, data: undefined } as never)
    render(<Dashboard />)
    expect(document.querySelector('.animate-spin')).not.toBeNull()
    // Stat cards are hidden while loading
    expect(screen.queryByText('Total Activities')).not.toBeInTheDocument()
  })

  it('shows error state instead of stats', () => {
    mockedUseCalendar.mockReturnValue({
      isLoading: false,
      error: new Error('boom'),
      data: undefined,
    } as never)
    render(<Dashboard />)
    expect(screen.getByText('Failed to load dashboard stats')).toBeInTheDocument()
  })
})
