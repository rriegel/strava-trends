import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, cleanup } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Routes, Route, useSearchParams } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import RouteCompare from '../RouteCompare'
import { getRoute, compareRouteActivities } from '../../api/routes'
import type { CompareResponse } from '../../types'

vi.mock('../../api/routes', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../api/routes')>()
  return {
    ...actual,
    getRoute: vi.fn(),
    compareRouteActivities: vi.fn(),
  }
})

// Mapbox needs WebGL — fake map like RouteMap's tests
vi.mock('mapbox-gl', () => ({
  default: {
    Map: class {
      addControl() {}
      on() {}
      once() {}
      isStyleLoaded() {
        return false
      }
      remove() {}
    },
    accessToken: '',
    NavigationControl: class {},
  },
}))

const mockedGetRoute = vi.mocked(getRoute)
const mockedCompare = vi.mocked(compareRouteActivities)

const ROUTE_DETAIL = {
  id: 5,
  name: 'Bandemer Loop',
  distance: 5583,
  elevation_gain: 40,
  activity_count: 3,
  cluster_id: null,
  start_lat: 42.3,
  start_lng: -83.75,
  polyline: 'wc~uF|pjpO?oC?kC',
  activities: [
    { id: 11, start_date: '2026-09-01T08:00:00', moving_time: 1528, distance: 5583.0, average_speed: 3.65, average_heartrate: 150, distance_bucket: '5k', effort_zone: 'tempo' },
    { id: 22, start_date: '2026-09-15T08:00:00', moving_time: 1490, distance: 5590.0, average_speed: 3.75, average_heartrate: 148, distance_bucket: '5k', effort_zone: 'tempo' },
    { id: 33, start_date: '2026-10-01T08:00:00', moving_time: 1455, distance: 5575.0, average_speed: 3.83, average_heartrate: 146, distance_bucket: '5k', effort_zone: 'threshold' },
  ],
}

const COMPARE_PAYLOAD: CompareResponse = {
  route: { id: 5, name: 'Bandemer Loop', distance: 5583, elevation_gain: 40, activity_count: 3 },
  activities: [
    {
      id: 11,
      summary: { id: 11, name: 'Run Sep 1', start_date: '2026-09-01T08:00:00', moving_time: 1528, elapsed_time: 1600, distance: 5583, average_speed: 3.65, average_heartrate: 150, total_elevation_gain: 40 },
      track: [[42.3, -83.75], [42.31, -83.75], [42.32, -83.75]],
      race_plot: { distances: [0, 2000, 4000, 5583], elapsed_seconds: [0, 600, 1200, 1600] },
      splits: [
        { start_m: 0, end_m: 400, seconds: 120, pace_s_per_km: 300 },
        { start_m: 400, end_m: 5583, seconds: 1480, pace_s_per_km: 288 },
      ],
      direction_reversed: false,
    },
    {
      id: 22,
      summary: { id: 22, name: 'Run Sep 15', start_date: '2026-09-15T08:00:00', moving_time: 1490, elapsed_time: 1550, distance: 5590, average_speed: 3.75, average_heartrate: 148, total_elevation_gain: 38 },
      track: [[42.3, -83.75], [42.31, -83.74], [42.32, -83.75]],
      race_plot: { distances: [0, 2000, 4000, 5590], elapsed_seconds: [0, 580, 1160, 1550] },
      splits: [
        { start_m: 0, end_m: 400, seconds: 115, pace_s_per_km: 288 },
        { start_m: 400, end_m: 5590, seconds: 1435, pace_s_per_km: 277 },
      ],
      direction_reversed: false,
    },
  ],
}

function renderCompare(initialEntry: string) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialEntry]}>
        <Routes>
          <Route path="/routes/:id/compare" element={<RouteCompare />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('RouteCompare', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockedGetRoute.mockResolvedValue(ROUTE_DETAIL as never)
    mockedCompare.mockResolvedValue(COMPARE_PAYLOAD as never)
  })

  afterEach(() => {
    cleanup()
  })

  function URLProbe() {
    const [params] = useSearchParams()
    return <div data-testid="url-probe">{params.toString()}</div>
  }

  it('fetches compare for the ids in the URL and renders chart + splits', async () => {
    render(
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <MemoryRouter initialEntries={['/routes/5/compare?activities=11,22']}>
          <Routes>
            <Route path="/routes/:id/compare" element={<RouteCompare />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    )
    await vi.waitFor(() => {
      expect(mockedCompare).toHaveBeenCalledWith(5, [11, 22])
    })
    // Split table shows segments with per-activity times; best segment highlighted
    await vi.waitFor(() => {
      expect(screen.getByText('Splits (400 m checkpoints)')).toBeInTheDocument()
    })
    expect(screen.getByText('Cumulative time vs distance')).toBeInTheDocument()
    expect(screen.getByText('Summary')).toBeInTheDocument()
  })

  it('toggles picker chips into the URL; compare only fires at 2+', async () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    mockedCompare.mockClear()
    const { } = render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/routes/5/compare']}>
          <Routes>
            <Route path="/routes/:id/compare" element={<RouteCompare />} />
          </Routes>
          <URLProbe />
        </MemoryRouter>
      </QueryClientProvider>
    )

    // Not enough selected: no compare call
    await vi.waitFor(() => expect(mockedGetRoute).toHaveBeenCalled())
    expect(mockedCompare).not.toHaveBeenCalled()

    const user = userEvent.setup()
    // Two date chips (from ROUTE_DETAIL.activities) — click both. The first
    // click persists a single id in the URL (selection state); the compare
    // query only fires once a second id lands (hook gated at >= 2).
    await user.click(await screen.findByRole('button', { name: /9\/1\/2026/ }))
    await vi.waitFor(() => {
      expect(screen.getByTestId('url-probe').textContent).toBe('activities=11')
    })
    expect(mockedCompare).not.toHaveBeenCalled()
    await user.click(await screen.findByRole('button', { name: /9\/15\/2026/ }))
    await vi.waitFor(() => {
      // URLSearchParams.toString() percent-encodes the comma
      expect(screen.getByTestId('url-probe').textContent).toBe('activities=11%2C22')
    })
    // Hook disabled until 2+ — but once both are in the URL it fires
    await vi.waitFor(() => {
      expect(mockedCompare).toHaveBeenCalledWith(5, [11, 22])
    })
  })

  it('shows reverse-run notice and still renders', async () => {
    mockedCompare.mockResolvedValue({
      ...COMPARE_PAYLOAD,
      activities: COMPARE_PAYLOAD.activities.map((a, i) =>
        i === 1 ? { ...a, direction_reversed: true, race_plot: null, splits: null } : a
      ),
    } as never)

    renderCompare('/routes/5/compare?activities=11,22')

    await vi.waitFor(() => {
      expect(screen.getByText(/ran reverse — no time compare/)).toBeInTheDocument()
    })
    // Chart still renders with the single forward activity's curve, but the
    // split table also stays (both come only from plottable activities)
    await vi.waitFor(() => {
      expect(screen.getByText('Cumulative time vs distance')).toBeInTheDocument()
    })
  })

  it('shows an error state when the compare call fails', async () => {
    mockedCompare.mockRejectedValue(new Error('boom'))
    renderCompare('/routes/5/compare?activities=11,22')
    await vi.waitFor(() => {
      expect(screen.getByText(/Failed to load comparison/)).toBeInTheDocument()
    })
  })
})