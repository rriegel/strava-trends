import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, cleanup } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, useSearchParams } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Trends from '../Trends'
import { getMultiMetricTrend, getPercentileBands } from '../../api/trends'

vi.mock('../../api/trends', () => ({
  getMultiMetricTrend: vi.fn(),
  getPercentileBands: vi.fn(),
}))

// Trends looks up the route name for its filter chip via useRoute (singular).
// Mocked so tests don't need the API layer; clearAllMocks in beforeEach
// clears calls but keeps this implementation.
vi.mock('../../hooks/useRoutes', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../hooks/useRoutes')>()
  return {
    ...actual,
    useRoute: vi.fn(() => ({
      data: { id: 7, name: 'River Loop', distance: 5200, elevation_gain: 40, activity_count: 3, cluster_id: null, start_lat: 42.28, start_lng: -83.74, polyline: '' },
      isLoading: false,
      error: null,
    })),
  }
})

const mockGetMultiMetricTrend = vi.mocked(getMultiMetricTrend)
const mockGetPercentileBands = vi.mocked(getPercentileBands)

// Minimal trend payload so the chart + stat cards render
const emptyTrendData = {
  average_speed: {
    metric_type: 'average_speed',
    data_points: [],
    trend: { direction: 'stable', slope: 0, r_squared: 0, change_percent: 0 },
  },
}

function renderTrends(initialEntry = '/trends') {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialEntry]}>
        <Trends />
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('Trends page — quick date presets', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockGetMultiMetricTrend.mockResolvedValue(emptyTrendData as never)
    mockGetPercentileBands.mockResolvedValue({ bands: [] } as never)
  })

  afterEach(() => {
    cleanup()
  })

  describe('route filter', () => {
    // MemoryRouter doesn't write the real address bar, so URL state is read
    // from the router itself via a probe child on the same route.
    function RouteProbe() {
      const [params] = useSearchParams()
      return <div data-testid="route-probe">{params.toString()}</div>
    }

    function renderTrendsWithProbe(initialEntry: string) {
      const queryClient = new QueryClient({
        defaultOptions: { queries: { retry: false } },
      })
      return render(
        <QueryClientProvider client={queryClient}>
          <MemoryRouter initialEntries={[initialEntry]}>
            <Trends />
            <RouteProbe />
          </MemoryRouter>
        </QueryClientProvider>
      )
    }

    it('preserves route_id in the URL when arriving from the Routes page', async () => {
      // Regression: the mount-sync effect used to fire whenever none of its
      // six whitelisted keys were present, full-replacing the query string
      // with metrics=average_speed and silently dropping route_id — so
      // "View activity trends" landed on an unfiltered Trends page.
      renderTrendsWithProbe('/trends?route_id=7')

      // Chip renders with the route name
      expect(screen.getByText(/Route: River Loop/)).toBeInTheDocument()

      // route_id survived mount (not clobbered by the metrics default write)
      await vi.waitFor(() => {
        expect(screen.getByTestId('route-probe').textContent).toBe('route_id=7')
      })
    })

    it('sends route_id on trend and percentile API calls', async () => {
      renderTrendsWithProbe('/trends?route_id=7')

      await vi.waitFor(() => {
        expect(mockGetMultiMetricTrend).toHaveBeenCalledWith(
          expect.arrayContaining(['average_speed']),
          expect.objectContaining({ route_id: 7 })
        )
        expect(mockGetPercentileBands).toHaveBeenCalledWith(
          expect.objectContaining({ route_id: 7 })
        )
      })
    })

    it('writes default metrics param on a bare /trends link, but leaves existing params alone', async () => {
      // Bare link: mount-sync writes metrics=average_speed (shareability)
      const { unmount } = renderTrendsWithProbe('/trends')
      await vi.waitFor(() => {
        expect(screen.getByTestId('route-probe').textContent).toBe('metrics=average_speed')
      })
      unmount()

      // Non-bare link (e.g. ?type=Run): mount-sync must not fire
      renderTrendsWithProbe('/trends?type=Run')
      await vi.waitFor(() => {
        expect(screen.getByTestId('route-probe').textContent).toBe('type=Run')
      })
    })
  })

  it('populates BOTH start and end date fields when a preset is clicked', async () => {
    const user = userEvent.setup()
    renderTrends()

    await user.click(screen.getByRole('button', { name: 'Last 30 days' }))

    const startInput = screen.getByLabelText('Start Date') as HTMLInputElement
    const endInput = screen.getByLabelText('End Date') as HTMLInputElement

    // Regression: previously the end date call clobbered the start date call,
    // leaving start empty in both the input and the URL query.
    expect(startInput.value).not.toBe('')
    expect(endInput.value).not.toBe('')
    expect(new Date(startInput.value).getTime()).toBeLessThan(
      new Date(endInput.value).getTime()
    )
  })

  it('writes both start and end into the URL query params', async () => {
    const user = userEvent.setup()
    renderTrends()

    await user.click(screen.getByRole('button', { name: 'Last 3 months' }))

    // The date inputs are controlled components fed from filtersFromParams(),
    // which parses the URL query — so if both fields are populated, both
    // params made it into the router location (and therefore the URL bar).
    await vi.waitFor(() => {
      const params = new URLSearchParams({
        start: (screen.getByLabelText('Start Date') as HTMLInputElement).value,
        end: (screen.getByLabelText('End Date') as HTMLInputElement).value,
      })
      expect(params.get('start')).toBeTruthy()
      expect(params.get('end')).toBeTruthy()
    })
  })

  it("'All time' clears both date fields", async () => {
    const user = userEvent.setup()
    renderTrends('/trends?start=2026-01-01&end=2026-02-01')

    const startInput = screen.getByLabelText('Start Date') as HTMLInputElement
    const endInput = screen.getByLabelText('End Date') as HTMLInputElement
    expect(startInput.value).toBe('2026-01-01')
    expect(endInput.value).toBe('2026-02-01')

    await user.click(screen.getByRole('button', { name: 'All time' }))

    expect((screen.getByLabelText('Start Date') as HTMLInputElement).value).toBe('')
    expect((screen.getByLabelText('End Date') as HTMLInputElement).value).toBe('')
  })

  it('start date is 30 days before end date for the 30-day preset', async () => {
    const user = userEvent.setup()
    renderTrends()

    await user.click(screen.getByRole('button', { name: 'Last 30 days' }))

    const startInput = screen.getByLabelText('Start Date') as HTMLInputElement
    const endInput = screen.getByLabelText('End Date') as HTMLInputElement

    const expectedEnd = new Date()
    const expectedStart = new Date()
    expectedStart.setDate(expectedStart.getDate() - 30)
    const fmt = (d: Date) => d.toISOString().split('T')[0]

    expect(endInput.value).toBe(fmt(expectedEnd))
    expect(startInput.value).toBe(fmt(expectedStart))
  })
})
