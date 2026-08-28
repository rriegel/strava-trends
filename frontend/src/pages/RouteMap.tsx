import { useEffect, useRef, useState } from 'react'
import mapboxgl from 'mapbox-gl'
import polyline from '@mapbox/polyline'
import 'mapbox-gl/dist/mapbox-gl.css'
import { useRoutes } from '../hooks/useRoutes'

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

export default function RouteMap() {
  const mapContainer = useRef<HTMLDivElement>(null)
  const map = useRef<mapboxgl.Map | null>(null)
  const [selectedRouteId, setSelectedRouteId] = useState<number | null>(null)
  const [hoveredRouteId, setHoveredRouteId] = useState<number | null>(null)

  const { data, isLoading, error } = useRoutes({ per_page: 100 })
  const routes = data?.routes || []

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
      const features = routes.map((route, index) => {
        const decoded = polyline.decode(route.polyline)
        const coordinates = decoded.map(([lat, lng]) => [lng, lat])
        const color = ROUTE_COLORS[index % ROUTE_COLORS.length]

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
          <h1 className="text-2xl font-bold text-gray-900">Routes</h1>
          <p className="text-sm text-gray-600 mt-1">
            {routes.length} route{routes.length !== 1 ? 's' : ''} discovered
          </p>
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
          {routes.map((route, index) => {
            const color = ROUTE_COLORS[index % ROUTE_COLORS.length]
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
      </div>
    </div>
  )
}
