import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import ActivityCard from '../ActivityCard'
import type { ActivitySummary } from '../../api/activities'

describe('ActivityCard', () => {
  const mockActivity: ActivitySummary = {
    id: 1,
    strava_id: 12345,
    name: 'Morning Run',
    type: 'Run',
    sport_type: 'Run',
    start_date: '2026-01-15T10:00:00Z',
    start_date_local: '2026-01-15T10:00:00Z',
    moving_time: 3600,
    distance: 10000,
    total_elevation_gain: 150,
    average_speed: 2.78,
    average_heartrate: 145,
    max_heartrate: 175,
    average_cadence: 85,
    average_watts: null,
    suffer_score: 75,
    device_name: 'Garmin Forerunner 945',
    distance_bucket: '10K',
    effort_zone: 'hard',
    terrain_type: 'road',
    route_id: null,
    has_streams: false,
  }

  it('renders activity name', () => {
    render(<ActivityCard activity={mockActivity} />)
    expect(screen.getByText('Morning Run')).toBeInTheDocument()
  })

  it('renders activity type with bullet separator', () => {
    render(<ActivityCard activity={mockActivity} />)
    const elements = screen.getAllByText(/Run/)
    expect(elements.length).toBeGreaterThan(0)
  })

  it('renders activity date', () => {
    render(<ActivityCard activity={mockActivity} />)
    const date = new Date(mockActivity.start_date_local).toLocaleDateString()
    expect(screen.getByText(date)).toBeInTheDocument()
  })

  it('renders distance', () => {
    render(<ActivityCard activity={mockActivity} />)
    expect(screen.getByText('Distance')).toBeInTheDocument()
    expect(screen.getByText('10.00 km')).toBeInTheDocument()
  })

  it('renders moving time', () => {
    render(<ActivityCard activity={mockActivity} />)
    expect(screen.getByText('Time')).toBeInTheDocument()
    expect(screen.getByText(/1h/)).toBeInTheDocument()
  })

  it('renders pace', () => {
    render(<ActivityCard activity={mockActivity} />)
    expect(screen.getByText('Pace')).toBeInTheDocument()
    expect(screen.getByText(/\/km/)).toBeInTheDocument()
  })

  it('renders elevation gain', () => {
    render(<ActivityCard activity={mockActivity} />)
    expect(screen.getByText('Elevation')).toBeInTheDocument()
    expect(screen.getByText('150 m')).toBeInTheDocument()
  })

  it('renders heart rate', () => {
    render(<ActivityCard activity={mockActivity} />)
    expect(screen.getByText('Avg HR')).toBeInTheDocument()
    expect(screen.getByText('145 bpm')).toBeInTheDocument()
  })

  it('renders suffer score', () => {
    render(<ActivityCard activity={mockActivity} />)
    expect(screen.getByText('Suffer Score')).toBeInTheDocument()
    expect(screen.getByText('75')).toBeInTheDocument()
  })

  it('renders device name', () => {
    render(<ActivityCard activity={mockActivity} />)
    expect(screen.getByText('Garmin Forerunner 945')).toBeInTheDocument()
  })

  it('renders distance bucket and effort zone', () => {
    render(<ActivityCard activity={mockActivity} />)
    expect(screen.getByText('10K')).toBeInTheDocument()
    expect(screen.getByText('hard')).toBeInTheDocument()
  })

  it('calls onClick when activity name is clicked', () => {
    const onClick = vi.fn()
    render(<ActivityCard activity={mockActivity} onClick={onClick} />)
    fireEvent.click(screen.getByText('Morning Run'))
    expect(onClick).toHaveBeenCalledWith(mockActivity)
  })

  it('shows confirm dialog when delete button is clicked', () => {
    const onDelete = vi.fn()
    render(<ActivityCard activity={mockActivity} onDelete={onDelete} />)
    const deleteButton = screen.getByLabelText('Delete activity')
    fireEvent.click(deleteButton)
    expect(screen.getByText('Delete Activity')).toBeInTheDocument()
    expect(screen.getByText(/Are you sure you want to delete/)).toBeInTheDocument()
    expect(onDelete).not.toHaveBeenCalled()
  })

  it('calls onDelete when confirm is clicked in dialog', () => {
    const onDelete = vi.fn()
    render(<ActivityCard activity={mockActivity} onDelete={onDelete} />)
    const deleteButton = screen.getByLabelText('Delete activity')
    fireEvent.click(deleteButton)
    const confirmButton = screen.getByText('Delete')
    fireEvent.click(confirmButton)
    expect(onDelete).toHaveBeenCalledWith(1)
  })

  it('closes dialog when cancel is clicked', () => {
    const onDelete = vi.fn()
    render(<ActivityCard activity={mockActivity} onDelete={onDelete} />)
    const deleteButton = screen.getByLabelText('Delete activity')
    fireEvent.click(deleteButton)
    const cancelButton = screen.getByText('Cancel')
    fireEvent.click(cancelButton)
    expect(screen.queryByText('Delete Activity')).not.toBeInTheDocument()
    expect(onDelete).not.toHaveBeenCalled()
  })

  it('does not render delete button if onDelete is not provided', () => {
    render(<ActivityCard activity={mockActivity} />)
    expect(screen.queryByLabelText('Delete activity')).not.toBeInTheDocument()
  })

  it('renders activity type icon', () => {
    render(<ActivityCard activity={mockActivity} />)
    expect(screen.getByText('🏃')).toBeInTheDocument()
  })

  it('renders different icon for different activity types', () => {
    const bikeActivity = { ...mockActivity, type: 'Ride' }
    render(<ActivityCard activity={bikeActivity} />)
    expect(screen.getByText('🚴')).toBeInTheDocument()
  })
})
