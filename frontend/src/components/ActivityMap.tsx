import { useEffect, useRef, useState } from 'react'
import mapboxgl from 'mapbox-gl'
import 'mapbox-gl/dist/mapbox-gl.css'

interface ActivityMapProps {
  activityId: number
  hasStreams: boolean
}

interface StreamData {
  data: [number, number][] // [lat, lng] pairs
  series_type: string
  original_size: number
}

export default function ActivityMap({ activityId, hasStreams }: ActivityMapProps) {
  const mapContainer = useRef<HTMLDivElement>(null)
  const map = useRef<mapboxgl.Map | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!hasStreams || !mapContainer.current) {
      setLoading(false)
      return
    }

    // Initialize map
    mapboxgl.accessToken = import.meta.env.VITE_MAPBOX_TOKEN || ''
    
    if (!mapboxgl.accessToken) {
      setError('Mapbox token not configured')
      setLoading(false)
      return
    }

    map.current = new mapboxgl.Map({
      container: mapContainer.current,
      style: 'mapbox://styles/mapbox/outdoors-v12',
      center: [0, 0],
      zoom: 1
    })

    // Fetch streams and add route
    const loadRoute = async () => {
      try {
        const response = await fetch(`/api/activities/${activityId}/streams?stream_types=latlng`)
        if (!response.ok) throw new Error('Failed to load route data')
        
        const data = await response.json()
        const latlngStream: StreamData | undefined = data.streams?.latlng
        
        if (!latlngStream || !latlngStream.data || latlngStream.data.length === 0) {
          setError('No route data available')
          setLoading(false)
          return
        }

        // Convert [lat, lng] to [lng, lat] for Mapbox
        const coordinates = latlngStream.data.map(([lat, lng]) => [lng, lat])
        
        // Wait for map to load
        map.current!.on('load', () => {
          // Add route as a line layer
          map.current!.addSource('route', {
            type: 'geojson',
            data: {
              type: 'Feature',
              properties: {},
              geometry: {
                type: 'LineString',
                coordinates
              }
            }
          })

          map.current!.addLayer({
            id: 'route-line',
            type: 'line',
            source: 'route',
            layout: {
              'line-join': 'round',
              'line-cap': 'round'
            },
            paint: {
              'line-color': '#ff6b35', // Strava orange
              'line-width': 4,
              'line-opacity': 0.8
            }
          })

          // Add start marker
          map.current!.addLayer({
            id: 'route-start',
            type: 'circle',
            source: 'route',
            paint: {
              'circle-radius': 8,
              'circle-color': '#22c55e', // green
              'circle-stroke-width': 2,
              'circle-stroke-color': '#fff'
            },
            filter: ['==', '$type', 'Point']
          })

          // Add start/end points
          map.current!.addSource('start-end', {
            type: 'geojson',
            data: {
              type: 'FeatureCollection',
              features: [
                {
                  type: 'Feature',
                  properties: { type: 'start' },
                  geometry: {
                    type: 'Point',
                    coordinates: coordinates[0]
                  }
                },
                {
                  type: 'Feature',
                  properties: { type: 'end' },
                  geometry: {
                    type: 'Point',
                    coordinates: coordinates[coordinates.length - 1]
                  }
                }
              ]
            }
          })

          map.current!.addLayer({
            id: 'start-end-points',
            type: 'circle',
            source: 'start-end',
            paint: {
              'circle-radius': 8,
              'circle-color': ['case',
                ['==', ['get', 'type'], 'start'],
                '#22c55e', // green for start
                '#ef4444'  // red for end
              ],
              'circle-stroke-width': 2,
              'circle-stroke-color': '#fff'
            }
          })

          // Fit bounds to route
          const bounds = new mapboxgl.LngLatBounds(coordinates[0], coordinates[0])
          coordinates.forEach(coord => bounds.extend(coord))
          map.current!.fitBounds(bounds, { padding: 50 })

          setLoading(false)
        })
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load route')
        setLoading(false)
      }
    }

    loadRoute()

    return () => {
      if (map.current) {
        map.current.remove()
      }
    }
  }, [activityId, hasStreams])

  if (!hasStreams) {
    return (
      <div className="bg-gray-100 rounded-lg p-8 text-center text-gray-500">
        <svg className="w-12 h-12 mx-auto mb-2 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
        </svg>
        <p>No route data available for this activity</p>
      </div>
    )
  }

  return (
    <div className="relative">
      {loading && (
        <div className="absolute inset-0 bg-gray-100 rounded-lg flex items-center justify-center z-10">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-strava-orange"></div>
        </div>
      )}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700 text-sm">
          {error}
        </div>
      )}
      <div ref={mapContainer} className="w-full h-96 rounded-lg" />
    </div>
  )
}
