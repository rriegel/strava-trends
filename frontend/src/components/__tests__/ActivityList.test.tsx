import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import ActivityList from '../ActivityList'
import type { ActivitySummary, Pagination } from '../../api/activities'

describe('ActivityList', () => {
  const mockActivities: ActivitySummary[] = [
    {
      id: 1, strava_id: null, name: 'Morning Run', type: 'Run', sport_type: 'Run',
      start_date: '2026-01-15T10:00:00Z', start_date_local: '2026-01-15T10:00:00Z',
      moving_time: 3600, distance: 10000, total_elevation_gain: 150, average_speed: 2.78,
      average_heartrate: 145, max_heartrate: null, average_cadence: null, average_watts: null,
      suffer_score: null, device_name: null, distance_bucket: null, effort_zone: null,
      terrain_type: null, route_id: null, has_streams: false,
    },
    {
      id: 2, strava_id: null, name: 'Evening Ride', type: 'Ride', sport_type: 'Ride',
      start_date: '2026-01-16T18:00:00Z', start_date_local: '2026-01-16T18:00:00Z',
      moving_time: 5400, distance: 30000, total_elevation_gain: 300, average_speed: 5.56,
      average_heartrate: null, max_heartrate: null, average_cadence: null, average_watts: null,
      suffer_score: null, device_name: null, distance_bucket: null, effort_zone: null,
      terrain_type: null, route_id: null, has_streams: false,
    },
  ]

  const mockPagination: Pagination = {
    page: 1, per_page: 20, total: 2, total_pages: 1,
  }

  it('renders loading state', () => {
    render(<ActivityList activities={[]} pagination={null} isLoading={true} />)
    const loadingElements = screen.getAllByText('', { exact: false })
    expect(loadingElements.length).toBeGreaterThan(0)
  })

  it('renders empty state when no activities', () => {
    render(<ActivityList activities={[]} pagination={null} isLoading={false} />)
    expect(screen.getByText('No activities')).toBeInTheDocument()
    expect(screen.getByText(/Get started by uploading/i)).toBeInTheDocument()
  })

  it('renders activity cards', () => {
    render(<ActivityList activities={mockActivities} pagination={mockPagination} isLoading={false} />)
    expect(screen.getByText('Morning Run')).toBeInTheDocument()
    expect(screen.getByText('Evening Ride')).toBeInTheDocument()
  })

  it('calls onActivityClick when activity is clicked', () => {
    const onActivityClick = vi.fn()
    render(<ActivityList activities={mockActivities} pagination={mockPagination} isLoading={false} onActivityClick={onActivityClick} />)
    fireEvent.click(screen.getByText('Morning Run'))
    expect(onActivityClick).toHaveBeenCalledWith(mockActivities[0])
  })

  it('shows confirm dialog when delete is clicked', () => {
    const onActivityDelete = vi.fn()
    render(<ActivityList activities={mockActivities} pagination={mockPagination} isLoading={false} onActivityDelete={onActivityDelete} />)
    const deleteButtons = screen.getAllByLabelText('Delete activity')
    fireEvent.click(deleteButtons[0])
    expect(screen.getByText('Delete Activity')).toBeInTheDocument()
    expect(onActivityDelete).not.toHaveBeenCalled()
  })

  it('calls onActivityDelete when confirm is clicked in dialog', () => {
    const onActivityDelete = vi.fn()
    render(<ActivityList activities={mockActivities} pagination={mockPagination} isLoading={false} onActivityDelete={onActivityDelete} />)
    const deleteButtons = screen.getAllByLabelText('Delete activity')
    fireEvent.click(deleteButtons[0])
    const confirmButton = screen.getByText('Delete')
    fireEvent.click(confirmButton)
    expect(onActivityDelete).toHaveBeenCalledWith(1)
  })

  it('renders pagination when multiple pages', () => {
    const pagination: Pagination = { page: 2, per_page: 20, total: 50, total_pages: 3 }
    render(<ActivityList activities={mockActivities} pagination={pagination} isLoading={false} />)
    expect(screen.getByText('Page 2 of 3')).toBeInTheDocument()
  })

  it('calls onPageChange when pagination button is clicked', () => {
    const onPageChange = vi.fn()
    const pagination: Pagination = { page: 2, per_page: 20, total: 50, total_pages: 3 }
    render(<ActivityList activities={mockActivities} pagination={pagination} isLoading={false} onPageChange={onPageChange} />)
    fireEvent.click(screen.getByText('Previous'))
    expect(onPageChange).toHaveBeenCalledWith(1)
    fireEvent.click(screen.getByText('Next'))
    expect(onPageChange).toHaveBeenCalledWith(3)
  })
})
