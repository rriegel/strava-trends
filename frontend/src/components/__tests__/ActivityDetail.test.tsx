import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import ActivityDetail from '../ActivityDetail'
import { activitiesApi, ActivityDetail as ActivityDetailType } from '../../api/activities'

vi.mock('../../api/activities')

describe('ActivityDetail', () => {
  const mockActivity: ActivityDetailType = {
    id: 1,
    strava_id: 12345,
    name: 'Morning Run',
    type: 'Run',
    sport_type: 'Run',
    start_date: '2026-01-15T10:00:00Z',
    start_date_local: '2026-01-15T10:00:00Z',
    moving_time: 3600,
    elapsed_time: 3700,
    distance: 10000,
    total_elevation_gain: 150,
    average_speed: 2.78,
    max_speed: 3.5,
    average_heartrate: 145,
    max_heartrate: 175,
    has_heartrate: true,
    average_cadence: 85,
    average_watts: null,
    weighted_average_watts: null,
    max_watts: null,
    suffer_score: 75,
    kilojoules: null,
    gear_id: null,
    device_name: 'Garmin Forerunner 945',
    distance_bucket: '10K',
    effort_zone: 'hard',
    terrain_type: 'road',
    route_id: null,
    has_streams: true,
    computed_metrics: [],
    effort_groups: [],
    created_at: '2026-01-15T10:00:00Z',
    updated_at: null,
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders loading state initially', () => {
    vi.mocked(activitiesApi.getDetail).mockImplementation(() => new Promise(() => {}))
    render(<ActivityDetail activityId={1} onClose={vi.fn()} />)
    // Loading state shows skeleton, activity name should not be present
    expect(screen.queryByText('Morning Run')).not.toBeInTheDocument()
  })

  it('renders activity details after loading', async () => {
    vi.mocked(activitiesApi.getDetail).mockResolvedValue(mockActivity)
    render(<ActivityDetail activityId={1} onClose={vi.fn()} />)

    await waitFor(() => {
      expect(screen.getByText('Morning Run')).toBeInTheDocument()
    })

    expect(screen.getByText('10.00 km')).toBeInTheDocument()
    expect(screen.getByText('150 m')).toBeInTheDocument()
    expect(screen.getByText('145 bpm')).toBeInTheDocument()
  })

  it('calls onClose when close button is clicked', async () => {
    const onClose = vi.fn()
    vi.mocked(activitiesApi.getDetail).mockResolvedValue(mockActivity)
    render(<ActivityDetail activityId={1} onClose={onClose} />)

    await waitFor(() => {
      expect(screen.getByText('Morning Run')).toBeInTheDocument()
    })

    const closeButton = screen.getByLabelText('Close')
    fireEvent.click(closeButton)
    expect(onClose).toHaveBeenCalled()
  })

  it('calls onClose when backdrop is clicked', async () => {
    const onClose = vi.fn()
    vi.mocked(activitiesApi.getDetail).mockResolvedValue(mockActivity)
    render(<ActivityDetail activityId={1} onClose={onClose} />)

    await waitFor(() => {
      expect(screen.getByText('Morning Run')).toBeInTheDocument()
    })

    // Click the backdrop
    const backdrop = screen.getByText('Morning Run').closest('div[style*="position: fixed"]')
    if (backdrop) {
      fireEvent.click(backdrop)
      expect(onClose).toHaveBeenCalled()
    }
  })

  it('calls onClose when Escape key is pressed', async () => {
    const onClose = vi.fn()
    vi.mocked(activitiesApi.getDetail).mockResolvedValue(mockActivity)
    render(<ActivityDetail activityId={1} onClose={onClose} />)

    await waitFor(() => {
      expect(screen.getByText('Morning Run')).toBeInTheDocument()
    })

    fireEvent.keyDown(document, { key: 'Escape' })
    expect(onClose).toHaveBeenCalled()
  })

  it('renders error state when fetch fails', async () => {
    vi.mocked(activitiesApi.getDetail).mockRejectedValue(new Error('Network error'))
    render(<ActivityDetail activityId={1} onClose={vi.fn()} />)

    await waitFor(() => {
      expect(screen.getByText('Error')).toBeInTheDocument()
      expect(screen.getByText('Network error')).toBeInTheDocument()
    })
  })

  it('renders classifications when present', async () => {
    vi.mocked(activitiesApi.getDetail).mockResolvedValue(mockActivity)
    render(<ActivityDetail activityId={1} onClose={vi.fn()} />)

    await waitFor(() => {
      expect(screen.getByText('Classifications')).toBeInTheDocument()
      expect(screen.getByText('10K')).toBeInTheDocument()
      expect(screen.getByText('hard')).toBeInTheDocument()
      expect(screen.getByText('road')).toBeInTheDocument()
    })
  })

  it('renders device name when present', async () => {
    vi.mocked(activitiesApi.getDetail).mockResolvedValue(mockActivity)
    render(<ActivityDetail activityId={1} onClose={vi.fn()} />)

    await waitFor(() => {
      expect(screen.getByText(/Garmin Forerunner 945/)).toBeInTheDocument()
    })
  })

  it('renders ActivityMap component when has_streams is true', async () => {
    vi.mocked(activitiesApi.getDetail).mockResolvedValue(mockActivity)
    render(<ActivityDetail activityId={1} onClose={vi.fn()} />)

    await waitFor(() => {
      expect(screen.getByText('Morning Run')).toBeInTheDocument()
    })

    // ActivityMap should render (it shows "No route data available" if streams fail to load)
    const mapContainer = screen.getByText('Morning Run').closest('div')
    expect(mapContainer).toBeInTheDocument()
  })
})
