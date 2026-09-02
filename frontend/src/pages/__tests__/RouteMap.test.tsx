import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { Route } from '../../types'

/**
 * RouteMap pulls in mapbox-gl, which needs WebGL. Mock the whole module with
 * a fake Map implementation that records calls; the component logic under
 * test (colors, sidebar, popup, navigation) doesn't depend on actual tiles.
 */
const mapInstances: FakeMap[] = []

class FakeMap {
  styleLoaded = true
  handlers: Record<string, (e?: unknown) => void> = {}
  sources = new Map<string, unknown>()
  layers: unknown[] = []
  paintProps: Record<string, Record<string, unknown>> = {}
  filters: Record<string, unknown> = {}

  addControl() {}
  addSource(_id: string, data: unknown) {
    this.sources.set(data as string, data)
  }
  getSource() {
    return null
  }
  addLayer(layer: unknown) {
    this.layers.push(layer)
  }
  setFilter(_layer: string, filter: unknown) {
    this.filters[_layer] = filter
  }
  setPaintProperty(layer: string, prop: string, value: unknown) {
    if (!this.paintProps[layer]) this.paintProps[layer] = {}
    this.paintProps[layer][prop] = value
  }
  on(event: string, _layerOrHandler: unknown, handler?: (e: unknown) => void) {
    // two-arg (map event) or three-arg (layer event) forms
    this.handlers[event] = handler || (_layerOrHandler as (e?: unknown) => void)
  }
  isStyleLoaded() {
    return this.styleLoaded
  }
  fitBounds() {}
  remove() {}
  getCanvas() {
    return { style: {} }
  }
}

// Polyline fixtures: two short routes
const ROUTES: Route[] = [
  {
    id: 1,
    name: 'River Loop',
    distance: 5200,
    elevation_gain: 40,
    activity_count: 12,
    cluster_id: null,
    start_lat: 42.28,
    start_lng: -83.74,
    polyline: 'wc~uF|pjpO?oC?kC', // trivial encoded line
  },
  {
    id: 2,
    name: 'Hill Route',
    distance: 10300,
    elevation_gain: 180,
    activity_count: 4,
    cluster_id: null,
    start_lat: 42.29,
    start_lng: -83.75,
    polyline: 'aa~uF|pjpO?cB?wD',
  },
]

vi.mock('mapbox-gl', () => {
  return {
    default: {
      Map: class {
        constructor() {
          const instance = new FakeMap()
          mapInstances.push(instance)
          return instance
        }
      },
      accessToken: '',
      NavigationControl: class {},
    },
  }
})

vi.mock('../../hooks/useRoutes', () => ({
  useRoutes: vi.fn(),
}))

const { useRoutes } = await import('../../hooks/useRoutes')
const mockedUseRoutes = vi.mocked(useRoutes)

const { default: RouteMap } = await import('../RouteMap')

function mockRoutes(routes: Route[]) {
  mockedUseRoutes.mockReturnValue({
    data: { routes, pagination: null },
    isLoading: false,
    error: null,
  } as never)
}

beforeEach(() => {
  mapInstances.length = 0
  vi.clearAllMocks()
})

describe('RouteMap', () => {
  it('renders sidebar with route list and deterministic colors', async () => {
    mockRoutes(ROUTES)
    const { container } = render(<RouteMap />)

    expect(screen.getByText('Routes')).toBeInTheDocument()
    expect(screen.getByText('2 routes discovered')).toBeInTheDocument()
    expect(screen.getByText('River Loop')).toBeInTheDocument()
    expect(screen.getByText('Hill Route')).toBeInTheDocument()
    // Fit-all button exists
    expect(screen.getByRole('button', { name: 'Fit all routes' })).toBeInTheDocument()
    // Color dots render with deterministic per-id colors (not list order)
    const dots = container.querySelectorAll('.w-3.h-3.rounded-full')
    expect(dots.length).toBe(2)
  })

  it('shows truncation warning when exactly 100 routes returned', async () => {
    const many: Route[] = Array.from({ length: 100 }, (_, i) => ({
      ...ROUTES[0],
      id: i + 1,
      name: `Route ${i + 1}`,
    }))
    mockRoutes(many)
    render(<RouteMap />)
    expect(screen.getByText(/Showing first 100 routes/)).toBeInTheDocument()
  })

  it('opens detail popup on route click and closes it', async () => {
    const user = userEvent.setup()
    mockRoutes(ROUTES)
    render(<RouteMap />)

    await user.click(screen.getByText('River Loop'))
    expect(screen.getByText('View activities')).toBeInTheDocument()
    // Distance appears in both the sidebar row and the popup
    expect(screen.getAllByText('5.2 km').length).toBeGreaterThanOrEqual(2)
    expect(screen.getAllByText('40 m').length).toBeGreaterThanOrEqual(2)

    // Close
    await user.click(screen.getByRole('button', { name: /Close route details/ }))
    expect(screen.queryByText('View activities')).not.toBeInTheDocument()
  })

  it('navigates to filtered activities from popup button', async () => {
    const user = userEvent.setup()
    mockRoutes(ROUTES)
    render(<RouteMap />)

    await user.click(screen.getByText('River Loop'))
    await user.click(screen.getByText('View activities'))
    // useNavigate from the mocked router
    expect(navigateMock).toHaveBeenCalledWith('/activities?route_id=1')
  })

  it('shows empty state when no routes', () => {
    mockRoutes([])
    render(<RouteMap />)
    expect(screen.getByText('No routes found')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Fit all routes' })).toBeDisabled()
  })
})

// Shared navigate mock wired through the router mock below
const navigateMock = vi.fn()

vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>()
  return {
    ...actual,
    useNavigate: () => navigateMock,
  }
})
