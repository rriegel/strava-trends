import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import mapboxgl from 'mapbox-gl'
import polyline from '@mapbox/polyline'
import 'mapbox-gl/dist/mapbox-gl.css'
import { useRoutes } from '../hooks/useRoutes'

/**
 * Deterministic color per route id, so colors don't shuffle when the sort
 * order or page of routes changes. Cycles after 8 ids.
 */
function routeColor(routeId: number): string {
  const ROUTE_COLORS = [
    '#ff6b35', // Strava orange
    '#3b82f6', // blue
    '#10b981', // green
    '#8b5cf6', // purple
    '#f59e0b', // amber
    '#ef4444', // red
    '#06b6d4', // cyan
    '#ec4899', // pink
  ]
  // Hash to spread similar ids apart while staying deterministic
  const idx = (routeId * 7) % ROUTE_COLORS.length
  return ROUTE_COLORS[idx]
}

export default function RouteMap() {
  const mapContainer = useRef<HTMLDivElement>(null)
  const map = useRef<mapboxgl.Map | null>(null)
  const [selectedRouteId, setSelectedRouteId] = useState<number | null>(null)
  const [hoveredRouteId, setHoveredRouteId] = useState<number | null>(null)
  const [routesTruncated, setRoutesTruncated] = useState(false)
  const navigate = useNavigate()

  const { data, isLoading, error } = useRoutes({ per_page: 100 })
  const routes = useMemo(() => data?.routes || [], [data])
  const selectedRoute = useMemo(
    () => routes.find((r) => r.id === selectedRouteId) || null,
    [routes, selectedRouteId]
  )

  // Initialize map
  useEffect(() => {
    if (!mapContainer.current) return

    mapboxgl.accessToken = import.meta.env.VITE_MAPBOX_TOKEN || ''
    
    if (!mapboxgl.accessToken) {
      console.error('Mapbox token not configured')
      return
    }

    map.current = new mapboxgl.Map({
      container: mapContainer.current,
      style: 'mapbox://styles/mapbox/outdoors-v12',
      center: [-74.5, 40], // Default center
      zoom: 9
    })

    map.current.addControl(new mapboxgl.NavigationControl(), 'top-right')

    return () => {
      if (map.current) {
        map.current.remove()
      }
    }
  }, [])

  // Add routes to map when data loads
  useEffect(() => {
    if (!map.current || !routes.length) return

    const loadRoutes = () => {
      if (!map.current) return

      // Decode all polylines and build GeoJSON
      const features = routes.map((route) => {
        const decoded = polyline.decode(route.polyline)
        const coordinates = decoded.map(([lat, lng]) => [lng, lat])
        const color = routeColor(route.id)

        return {
          type: 'Feature' as const,
          properties: {
            id: route.id,
            name: route.name || `Route ${route.id}`,
            distance: route.distance,
            elevation_gain: route.elevation_gain,
            activity_count: route.activity_count,
            color,
          },
          geometry: {
            type: 'LineString' as const,
            coordinates,
          },
        }
      })

      // Add source and layer for routes
      if (map.current.getSource('routes')) {
        ;(map.current.getSource('routes') as mapboxgl.GeoJSONSource).setData({
          type: 'FeatureCollection',
          features,
        })
      } else {
        map.current.addSource('routes', {
          type: 'geojson',
          data: {
            type: 'FeatureCollection',
            features,
          },
        })

        map.current.addLayer({
          id: 'routes-line',
          type: 'line',
          source: 'routes',
          layout: {
            'line-join': 'round',
            'line-cap': 'round',
          },
          paint: {
            'line-color': ['get', 'color'],
            'line-width': 4,
            'line-opacity': 0.8,
          },
        })

        // Add hover effect
        map.current.on('mouseenter', 'routes-line', (e) => {
          if (!map.current || !e.features || !e.features.length) return
          map.current.getCanvas().style.cursor = 'pointer'
          const feature = e.features[0]
          setHoveredRouteId(feature.properties?.id)
        })

        map.current.on('mouseleave', 'routes-line', () => {
          if (!map.current) return
          map.current.getCanvas().style.cursor = ''
          setHoveredRouteId(null)
        })

        // Add click handler
        map.current.on('click', 'routes-line', (e) => {
          if (!e.features || !e.features.length) return
          const feature = e.features[0]
          const routeId = feature.properties?.id
          setSelectedRouteId(routeId)

          // Zoom to route
          const coordinates = (feature.geometry as any).coordinates
          const bounds = coordinates.reduce(
            (acc: [[number, number], [number, number]], coord: [number, number]) => {
              return [
                [Math.min(acc[0][0], coord[0]), Math.min(acc[0][1], coord[1])],
                [Math.max(acc[1][0], coord[0]), Math.max(acc[1][1], coord[1])],
              ]
            },
            [
              [coordinates[0][0], coordinates[0][1]],
              [coordinates[0][0], coordinates[0][1]],
            ]
          )
          map.current!.fitBounds(bounds, { padding: 100, maxZoom: 15 })
        })
      }

      // Fit bounds to show all routes
      if (features.length > 0) {
        const allCoords = features.flatMap((f) => f.geometry.coordinates)
        const lats = allCoords.map((c) => c[1])
        const lngs = allCoords.map((c) => c[0])
        const bounds: mapboxgl.LngLatBoundsLike = [
          [Math.min(...lngs), Math.min(...lats)],
          [Math.max(...lngs), Math.max(...lats)],
        ]
        map.current.fitBounds(bounds, { padding: 50 })
      }
    }

    if (map.current.isStyleLoaded()) {
      loadRoutes()
    } else {
      map.current.on('load', loadRoutes)
    }
  }, [routes])

  // If the API returned exactly the page size, there may be more routes.
  // Sidebar concern — must fire even when the map never initialized
  // (no Mapbox token in CI), so it can't live in the map-drawing effect.
  useEffect(() => {
    setRoutesTruncated(routes.length >= 100)
  }, [routes])

  // Zoom to fit all visible routes (used on initial load and "Fit all" button)
  const fitAllRoutes = () => {
    if (!map.current || routes.length === 0) return
    const allCoords = routes.flatMap((route) =>
      polyline.decode(route.polyline).map(([lat, lng]) => [lng, lat] as [number, number])
    )
    if (allCoords.length === 0) return
    const lats = allCoords.map((c) => c[1])
    const lngs = allCoords.map((c) => c[0])
    const bounds: mapboxgl.LngLatBoundsLike = [
      [Math.min(...lngs), Math.min(...lats)],
      [Math.max(...lngs), Math.max(...lats)],
    ]
    map.current.fitBounds(bounds, { padding: 50 })
  }

  // Highlight selected route
  useEffect(() => {
    if (!map.current || !map.current.isStyleLoaded()) return

    if (selectedRouteId) {
      map.current.setFilter('routes-line', ['==', ['get', 'id'], selectedRouteId])
      map.current.setPaintProperty('routes-line', 'line-width', 6)
      map.current.setPaintProperty('routes-line', 'line-opacity', 1)
    } else {
      map.current.setFilter('routes-line', null)
      map.current.setPaintProperty('routes-line', 'line-width', 4)
      map.current.setPaintProperty('routes-line', 'line-opacity', 0.8)
    }
  }, [selectedRouteId])

  const formatDistance = (meters: number) => {
    if (meters >= 1000) {
      return `${(meters / 1000).toFixed(1)} km`
    }
    return `${meters.toFixed(0)} m`
  }

  const formatElevation = (meters: number) => {
    return `${meters.toFixed(0)} m`
  }

  return (
    <div className="flex h-[calc(100vh-8rem)]">
      {/* Sidebar */}
      <div className="w-96 bg-white border-r overflow-y-auto">
        <div className="p-4 border-b">
          <div className="flex items-center justify-between">
            <h1 className="text-2xl font-bold text-gray-900">Routes</h1>
            <button
              type="button"
              onClick={fitAllRoutes}
              disabled={routes.length === 0}
              className="px-3 py-1 text-sm border border-gray-300 rounded-lg bg-white text-gray-700 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              Fit all routes
            </button>
          </div>
          <p className="text-sm text-gray-600 mt-1">
            {routes.length} route{routes.length !== 1 ? 's' : ''} discovered
          </p>
          {routesTruncated && (
            <p className="text-xs text-amber-600 mt-1">
              Showing first 100 routes — refine with more activities or filters
            </p>
          )}
        </div>

        {isLoading && (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
          </div>
        )}

        {error && (
          <div className="p-4 bg-red-50 border-b border-red-200">
            <p className="text-red-800 text-sm">Failed to load routes</p>
          </div>
        )}

        <div className="divide-y">
          {routes.map((route) => {
            const color = routeColor(route.id)
            const isSelected = selectedRouteId === route.id
            const isHovered = hoveredRouteId === route.id

            return (
              <div
                key={route.id}
                className={`p-4 cursor-pointer transition-colors ${
                  isSelected
                    ? 'bg-blue-50 border-l-4 border-l-blue-600'
                    : isHovered
                    ? 'bg-gray-50'
                    : 'hover:bg-gray-50'
                }`}
                onClick={() => setSelectedRouteId(route.id)}
                onMouseEnter={() => setHoveredRouteId(route.id)}
                onMouseLeave={() => setHoveredRouteId(null)}
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <div
                      className="w-3 h-3 rounded-full"
                      style={{ backgroundColor: color }}
                    />
                    <h3 className="font-semibold text-gray-900">
                      {route.name || `Route ${route.id}`}
                    </h3>
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-2 text-sm">
                  <div>
                    <div className="text-gray-500 text-xs">Distance</div>
                    <div className="font-medium text-gray-900">
                      {formatDistance(route.distance)}
                    </div>
                  </div>
                  <div>
                    <div className="text-gray-500 text-xs">Elevation</div>
                    <div className="font-medium text-gray-900">
                      {formatElevation(route.elevation_gain)}
                    </div>
                  </div>
                  <div>
                    <div className="text-gray-500 text-xs">Activities</div>
                    <div className="font-medium text-gray-900">
                      {route.activity_count}
                    </div>
                  </div>
                </div>
              </div>
            )
          })}
        </div>

        {!isLoading && routes.length === 0 && (
          <div className="p-8 text-center text-gray-500">
            <p className="mb-2">No routes found</p>
            <p className="text-sm">Upload activities with GPS data to discover routes</p>
          </div>
        )}
      </div>

      {/* Map */}
      <div className="flex-1 relative">
        {isLoading && (
          <div className="absolute inset-0 bg-gray-100 flex items-center justify-center z-10">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
          </div>
        )}
        <div ref={mapContainer} className="w-full h-full" />

        {/* Route detail popup */}
        {selectedRoute && (
          <div className="absolute bottom-4 left-4 right-4 md:right-auto md:w-96 bg-white rounded-lg shadow-lg border p-4 z-20">
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center gap-2">
                <div
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: routeColor(selectedRoute.id) }}
                />
                <h3 className="font-semibold text-gray-900">
                  {selectedRoute.name || `Route ${selectedRoute.id}`}
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setSelectedRouteId(null)}
                className="text-gray-400 hover:text-gray-600 text-lg leading-none"
                aria-label="Close route details"
              >
                ×
              </button>
            </div>

            <div className="grid grid-cols-3 gap-3 text-sm mb-4">
              <div>
                <div className="text-gray-500 text-xs">Distance</div>
                <div className="font-medium text-gray-900">
                  {formatDistance(selectedRoute.distance)}
                </div>
              </div>
              <div>
                <div className="text-gray-500 text-xs">Elevation</div>
                <div className="font-medium text-gray-900">
                  {formatElevation(selectedRoute.elevation_gain)}
                </div>
              </div>
              <div>
                <div className="text-gray-500 text-xs">Activities</div>
                <div className="font-medium text-gray-900">
                  {selectedRoute.activity_count}
                </div>
              </div>
            </div>

            <button
              type="button"
              onClick={() => navigate(`/activities?route_id=${selectedRoute.id}`)}
              className="w-full px-3 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700"
            >
              View activities
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
