import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, cleanup } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Trends from '../Trends'
import { getMultiMetricTrend, getPercentileBands } from '../../api/trends'

vi.mock('../../api/trends', () => ({
  getMultiMetricTrend: vi.fn(),
  getPercentileBands: vi.fn(),
}))

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
