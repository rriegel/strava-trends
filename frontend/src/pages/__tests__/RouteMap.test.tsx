import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, act } from '@testing-library/react'
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
    // three-arg (layer event) form → key by layer; two-arg (map event) →
    // plain key. Layer keying keeps 'click:routes-line' and the map-level
    // 'click' clear-handler from clobbering each other.
    if (handler) {
      this.handlers[`${event}:${_layerOrHandler}`] = handler
    } else {
      this.handlers[event] = _layerOrHandler as (e?: unknown) => void
    }
  }
  isStyleLoaded() {
    return this.styleLoaded
  }
  fitBounds() {}
  remove() {}
  getCanvas() {
    return { style: {} }
  }
  queryFeatures: unknown[] = []
  queryRenderedFeatures() {
    return this.queryFeatures
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
  useRenameRoute: vi.fn(() => ({ mutate: vi.fn() })),
}))

const { useRoutes, useRenameRoute } = await import('../../hooks/useRoutes')
const mockedUseRoutes = vi.mocked(useRoutes)
const mockedUseRenameRoute = vi.mocked(useRenameRoute)

const { default: RouteMap } = await import('../RouteMap')

function mockRoutes(routes: Route[]) {
  mockedUseRoutes.mockReturnValue({
    data: { routes, pagination: null },
    isLoading: false,
    error: null,
  } as never)
}

beforeEach(() => {
  // CI has no .env (gitignored); without a token the map never initializes
  // and map-state assertions would fail. Stubbed for all runs so behavior
  // is identical locally and in CI.
  vi.stubEnv('VITE_MAPBOX_TOKEN', 'test-token')
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

  it('navigates to route-filtered trends from popup button', async () => {
    const user = userEvent.setup()
    mockRoutes(ROUTES)
    render(<RouteMap />)

    await user.click(screen.getByText('River Loop'))
    await user.click(screen.getByText('View activity trends'))
    expect(navigateMock).toHaveBeenCalledWith('/trends?route_id=1')
  })

  it('starts inline rename from the pencil button and commits on Enter', async () => {
    const user = userEvent.setup()
    const mutateMock = vi.fn()
    mockedUseRenameRoute.mockReturnValue({ mutate: mutateMock } as never)
    mockRoutes(ROUTES)
    render(<RouteMap />)

    await user.click(screen.getByRole('button', { name: 'Rename River Loop' }))
    const input = screen.getByLabelText('Route name') as HTMLInputElement
    expect(input.value).toBe('River Loop')

    await user.clear(input)
    await user.type(input, 'Beecher Loop{Enter}')
    expect(mutateMock).toHaveBeenCalledTimes(1)
    expect(mutateMock).toHaveBeenCalledWith({ id: 1, name: 'Beecher Loop' })
  })

  it('cancels rename on Escape without calling the mutation', async () => {
    const user = userEvent.setup()
    const mutateMock = vi.fn()
    mockedUseRenameRoute.mockReturnValue({ mutate: mutateMock } as never)
    mockRoutes(ROUTES)
    render(<RouteMap />)

    await user.click(screen.getByRole('button', { name: 'Rename Hill Route' }))
    await user.type(screen.getByLabelText('Route name'), 'x{Escape}')
    expect(mutateMock).not.toHaveBeenCalled()
    // Original name still shown
    expect(screen.getByText('Hill Route')).toBeInTheDocument()
  })

  it('shows empty state when no routes', () => {
    mockRoutes([])
    render(<RouteMap />)
    expect(screen.getByText('No routes found')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Fit all routes' })).toBeDisabled()
  })

  describe('selection ghosting', () => {
    function getMap(): FakeMap {
      expect(mapInstances.length).toBeGreaterThan(0)
      return mapInstances[mapInstances.length - 1]
    }

    it('ghosts other routes on selection: gray dimmed base, selected on own layer, other dots hidden', async () => {
      const user = userEvent.setup()
      mockRoutes(ROUTES)
      render(<RouteMap />)

      await user.click(screen.getByText('River Loop'))
      const m = getMap()

      // Base layer now carries only the OTHER route, restyled as a ghost
      expect(m.filters['routes-line']).toEqual(['!=', ['get', 'id'], 1])
      expect(m.paintProps['routes-line']['line-color']).toBe('#9ca3af')
      expect(m.paintProps['routes-line']['line-opacity']).toBe(0.12)
      expect(m.paintProps['routes-line']['line-width']).toBe(3)

      // Selected route renders on its dedicated layer
      expect(m.filters['routes-line-selected']).toEqual(['==', ['get', 'id'], 1])
      expect(m.paintProps['routes-line-selected']['line-opacity']).toBe(1)

      // Start dots: selected route only
      expect(m.filters['routes-start-dots']).toEqual(['==', ['get', 'id'], 1])
    })

    it('hovering a ghost brightens only that route on the preview layer', async () => {
      const user = userEvent.setup()
      mockRoutes(ROUTES)
      render(<RouteMap />)

      await user.click(screen.getByText('River Loop'))
      const m = getMap()

      // Simulate mouseenter on the other route's ghost line (layer-keyed
      // handler). Synchronous map event → wrap in act() so the hover state
      // update flushes before asserting on the styling effect's output.
      const enter = m.handlers['mouseenter:routes-line'] as (e?: unknown) => void
      expect(enter).toBeDefined()
      act(() => {
        enter({ features: [{ properties: { id: 2 } }] })
      })

      // Hover layer shows route 2 in color at preview opacity; base ghost
      // filter excludes it so the two layers don't double-draw
      expect(m.filters['routes-line-hover']).toEqual(['==', ['get', 'id'], 2])
      expect(m.paintProps['routes-line-hover']['line-opacity']).toBe(0.6)
      expect(m.filters['routes-line']).toEqual([
        'all',
        ['!=', ['get', 'id'], 1],
        ['!=', ['get', 'id'], 2],
      ])

      // Leaving restores the plain ghost state
      const leave = m.handlers['mouseleave:routes-line'] as (e?: unknown) => void
      act(() => {
        leave()
      })
      expect(m.filters['routes-line-hover']).toEqual(['literal', false])
      expect(m.filters['routes-line']).toEqual(['!=', ['get', 'id'], 1])
    })

    it('clearing selection restores full-color zoom-aware baseline', async () => {
      const user = userEvent.setup()
      mockRoutes(ROUTES)
      render(<RouteMap />)

      await user.click(screen.getByText('River Loop'))
      await user.click(screen.getByRole('button', { name: /Close route details/ }))
      const m = getMap()

      expect(m.filters['routes-line']).toBeNull()
      // Colors come back from the data (zoom-aware ramp restored, not flat)
      expect(m.paintProps['routes-line']['line-color']).toEqual(['get', 'color'])
      expect(m.paintProps['routes-line']['line-opacity']).toEqual([
        'interpolate', ['linear'], ['zoom'], 8, 0.35, 12, 0.8,
      ])
      expect(m.filters['routes-line-selected']).toEqual(['literal', false])
      expect(m.filters['routes-start-dots']).toBeNull()
    })

    it('Esc clears the selection, but not while a rename is open', async () => {
      const user = userEvent.setup()
      mockRoutes(ROUTES)
      render(<RouteMap />)

      await user.click(screen.getByText('River Loop'))
      expect(screen.getByText('View activities')).toBeInTheDocument()

      // Esc during rename must NOT clear: start rename first
      await user.click(screen.getByRole('button', { name: 'Rename River Loop' }))
      const input = screen.getByLabelText('Route name')
      await user.type(input, '{Escape}')
      // Rename cancelled, selection still present
      expect(screen.getByText('View activities')).toBeInTheDocument()

      // Esc with no rename open clears the selection
      await user.keyboard('{Escape}')
      expect(screen.queryByText('View activities')).not.toBeInTheDocument()
    })
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
