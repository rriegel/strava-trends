import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useParams, useSearchParams, Link } from 'react-router-dom'
import mapboxgl from 'mapbox-gl'
import polyline from '@mapbox/polyline'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts'
import 'mapbox-gl/dist/mapbox-gl.css'
import { useRoute, useRouteCompare } from '../hooks/useRoutes'
import {
  loadViewport,
  createViewportSaver,
} from '../utils/mapViewport'
import { formatDistance as formatDistanceShared, distanceUnitLabel, type UnitSystem } from '../utils/format'
import { useUnits } from '../context/units'
import type { CompareActivity } from '../types'

/** Deterministic palette for activity colors — indexed by the activity's
 * position in the route's activity list, NOT by id (id-hashing collides:
 * ids 15 and 20 both hit slot 5%5). With selection capped at 5 and a
 * 10-color palette, two *selected* activities can only collide on a
 * route with 10+ activities — outside current scope. */
const ACTIVITY_COLORS = [
  '#ff6b35', // Strava orange
  '#3b82f6', // blue
  '#10b981', // green
  '#8b5cf6', // purple
  '#f59e0b', // amber
  '#ef4444', // red
  '#06b6d4', // cyan
  '#ec4899', // pink
  '#84cc16', // lime
  '#6366f1', // indigo
]

const MAX_SELECTABLE = 5

function formatDuration(seconds: number): string {
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = Math.round(seconds % 60)
  if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
  return `${m}:${String(s).padStart(2, '0')}`
}

function formatPace(sPerKm: number | null, unit: UnitSystem): string {
  if (sPerKm == null) return '—'
  // s/km -> s/mi is ×1.609344 (km per mile), NOT 1609.344 (meters/mile)
  const sPerUnit = unit === 'imperial' ? sPerKm * 1.609344 : sPerKm
  const m = Math.floor(sPerUnit / 60)
  const s = Math.round(sPerUnit % 60)
  return `${m}:${String(s).padStart(2, '0')} /${distanceUnitLabel(unit)}`
}

function formatDistance(meters: number | null, unit: UnitSystem): string {
  if (meters == null) return '—'
  return formatDistanceShared(meters, unit)
}

function formatElevationCompare(meters: number | null, unit: UnitSystem): string {
  if (meters == null) return '—'
  if (unit === 'imperial') {
    return `${(meters * 3.280839895013123).toFixed(0)} ft`
  }
  return `${meters.toFixed(0)} m`
}

/** Human label for a split segment length in the user's unit system.
 *  Splits are computed server-side at fixed meter intervals (1000/800/400);
 *  imperial renders the equivalent miles. */
function splitIntervalLabel(meters: number, unit: UnitSystem): string {
  if (unit === 'imperial') {
    const miles = meters * 3.280839895013123 / 5280
    return `${miles.toFixed(miles < 0.3 ? 2 : 2)} mi`
  }
  return meters >= 1000 ? `${meters / 1000} km` : `${meters} m`
}

export default function RouteCompare() {
  const { id } = useParams()
  const routeId = parseInt(id || '', 10)
  const mapContainer = useRef<HTMLDivElement>(null)
  const map = useRef<mapboxgl.Map | null>(null)
  const [searchParams, setSearchParams] = useSearchParams()
  const [mapError, setMapError] = useState(false)
  const [mapLoaded, setMapLoaded] = useState(false)

  // Selected activity ids from the URL (?activities=1,5,9) — shareable
  const selectedIds = useMemo(
    () =>
      (searchParams.get('activities') || '')
        .split(',')
        .map((s) => parseInt(s, 10))
        .filter((n) => Number.isFinite(n) && n > 0),
    [searchParams]
  )

  const { data: route } = useRoute(routeId)
  const { unit } = useUnits()
  // Route detail supplies the activity picker list (id/name/date per activity)
  const routeActivities = route?.activities ?? []

  // Split interval (meters) — URL-persisted like every other filter here
  const splitInterval = useMemo(() => {
    const raw = parseInt(searchParams.get('interval') || '', 10)
    return [1000, 800, 400].includes(raw) ? raw : 1000
  }, [searchParams])

  const setSplitInterval = (meters: number) => {
    setSearchParams(
      (prev) => {
        const nextParams = new URLSearchParams(prev)
        if (meters === 1000) {
          nextParams.delete('interval') // default: keep URLs clean
        } else {
          nextParams.set('interval', String(meters))
        }
        return nextParams
      },
      { replace: true }
    )
  }

  // Color lookup by activity id, keyed by position in the route's list
  // (stable across selection changes; see ACTIVITY_COLORS note on why not
  // id-hashing). Falls back to id-hash for activities outside the list.
  const activityColor = useCallback(
    (activityId: number): string => {
      const idx = routeActivities.findIndex((ra) => ra.id === activityId)
      if (idx >= 0) return ACTIVITY_COLORS[idx % ACTIVITY_COLORS.length]
      return ACTIVITY_COLORS[activityId % ACTIVITY_COLORS.length]
    },
    [routeActivities]
  )

  const {
    data: compare,
    isLoading,
    isFetching,
    error,
  } = useRouteCompare(routeId, selectedIds, splitInterval)

  // Selection <-> URL (one writer, callback form so stacked updates compose)
  const toggleActivity = (activityId: number) => {
    setSearchParams(
      (prev) => {
        const current = (prev.get('activities') || '')
          .split(',')
          .filter(Boolean)
          .map(Number)
        const next = current.includes(activityId)
          ? current.filter((n) => n !== activityId)
          : [...current, activityId].slice(0, MAX_SELECTABLE)
        const nextParams = new URLSearchParams(prev)
        if (next.length > 0) {
          nextParams.set('activities', next.join(','))
        } else {
          nextParams.delete('activities')
        }
        return nextParams
      },
      { replace: true }
    )
  }

  // Initialize map
  useEffect(() => {
    if (!mapContainer.current) return
    mapboxgl.accessToken = import.meta.env.VITE_MAPBOX_TOKEN || ''
    if (!mapboxgl.accessToken) {
      setMapError(true)
      return
    }
    const saved = loadViewport('route-compare')
    map.current = new mapboxgl.Map({
      container: mapContainer.current,
      style: 'mapbox://styles/mapbox/outdoors-v12',
      // Restore the last camera instantly; first-ever visit defaults near
      // the app's routes (the data-driven fit below takes over precisely)
      center: saved ? [saved.lng, saved.lat] : [-83.74, 42.28],
      zoom: saved ? saved.zoom : 11,
      bearing: saved?.bearing ?? 0,
      pitch: saved?.pitch ?? 0,
    })
    map.current.addControl(new mapboxgl.NavigationControl(), 'top-right')
    map.current.on('load', () => setMapLoaded(true))
    // Persist the camera; data-driven fits mark themselves programmatic so
    // they don't overwrite the user's own saved camera
    createViewportSaver('route-compare', map.current)
    return () => {
      map.current?.remove()
      map.current = null
    }
  }, [])

  // Draw the route's canonical line + each selected activity's own track.
  // Keyed on mapLoaded so drawing waits for the map's real load event —
  // isStyleLoaded() can report false forever if polled at the wrong moment.
  useEffect(() => {
    const mbMap = map.current
    if (!mbMap || !compare) return

    const draw = () => {
      if (!map.current) return
      const m = map.current

      // Reset sources/layers on each payload (idempotent redraw)
      for (const layerId of ['compare-acts', 'compare-route']) {
        if (m.getLayer(layerId)) m.removeLayer(layerId)
      }
      if (m.getSource('compare-route')) m.removeSource('compare-route')
      if (m.getSource('compare-acts')) m.removeSource('compare-acts')

      const features = compare.activities
        .filter((a) => a.track.length >= 2 && !a.direction_reversed)
        .map((a) => ({
          type: 'Feature' as const,
          properties: { id: a.id, color: activityColor(a.id) },
          geometry: { type: 'LineString' as const, coordinates: a.track.map(([lat, lng]) => [lng, lat]) },
        }))

      // Canonical route line: faint gray spine under the tracks
      if (route?.polyline) {
        try {
          const coords = polyline.decode(route.polyline).map(([lat, lng]: [number, number]) => [lng, lat])
          m.addSource('compare-route', {
            type: 'geojson',
            data: { type: 'Feature', properties: {}, geometry: { type: 'LineString', coordinates: coords } },
          })
          m.addLayer({
            id: 'compare-route',
            type: 'line',
            source: 'compare-route',
            layout: { 'line-join': 'round', 'line-cap': 'round' },
            paint: { 'line-color': '#9ca3af', 'line-width': 2, 'line-opacity': 0.3 },
          })
        } catch {
          // polyline decode unavailable — spine is optional context
        }
      }

      if (features.length) {
        m.addSource('compare-acts', {
          type: 'geojson',
          data: { type: 'FeatureCollection', features },
        })
        m.addLayer({
          id: 'compare-acts',
          type: 'line',
          source: 'compare-acts',
          layout: { 'line-join': 'round', 'line-cap': 'round' },
          paint: { 'line-color': ['get', 'color'], 'line-width': 4, 'line-opacity': 0.9 },
        })
      }

      // Fit to all drawn geometry — a data-driven reframe on selection
      // change: instant (no sweep), and marked programmatic so the
      // user's saved camera isn't overwritten by it
      const allCoords = [
        ...features.flatMap((f) => (f.geometry.coordinates as [number, number][])),
      ]
      if (allCoords.length) {
        const lats = allCoords.map((c) => c[1])
        const lngs = allCoords.map((c) => c[0])
        const saver = (
          m as unknown as { _saver?: { markProgrammatic: () => void } }
        )._saver
        saver?.markProgrammatic()
        m.fitBounds(
          [
            [Math.min(...lngs), Math.min(...lats)],
            [Math.max(...lngs), Math.max(...lats)],
          ],
          { padding: 60, maxZoom: 16, animate: false }
        )
      }
    }

    if (mapLoaded && mbMap.isStyleLoaded()) draw()
    else mbMap.once('load', draw)
  }, [compare, route?.polyline, mapLoaded])

  const compareActivities = compare?.activities ?? []
  const plottable = compareActivities.filter(
    (a) => a.race_plot && !a.direction_reversed
  )

  // Race plot data: resample every activity onto a SHARED distance grid.
  // Joining on exact stream distances doesn't work — each activity's GPS
  // points land at different distances, so most rows would hold a value
  // for one activity and null for the rest, rendering as disconnected
  // tick marks. Linear interpolation onto a common 50 m grid gives every
  // activity a value at (almost) every x, like a real race plot.
  const raceData = useMemo(() => {
    if (plottable.length < 1) return []

    // Collapse standing points (keep first arrival) per activity so the
    // distance axis is strictly increasing and interpolation is total
    const curves = plottable.map((a) => {
      const d: number[] = []
      const t: number[] = []
      a.race_plot!.distances.forEach((dist, i) => {
        if (d.length === 0 || dist > d[d.length - 1]) {
          d.push(dist)
          t.push(a.race_plot!.elapsed_seconds[i])
        }
      })
      return { id: a.id, d, t, final: d[d.length - 1] }
    })

    const interp = (c: (typeof curves)[0], x: number): number | null => {
      if (x < c.d[0] || x > c.final) return null
      let lo = 0
      let hi = c.d.length - 1
      while (hi - lo > 1) {
        const mid = (lo + hi) >> 1
        if (c.d[mid] <= x) lo = mid
        else hi = mid
      }
      if (c.d[hi] === c.d[lo]) return c.t[hi]
      return c.t[lo] + (c.t[hi] - c.t[lo]) * ((x - c.d[lo]) / (c.d[hi] - c.d[lo]))
    }

    const maxFinal = Math.max(...curves.map((c) => c.final))
    const STEP = 50
    const rows: Record<string, number | null>[] = []
    for (let x = 0; x <= maxFinal + STEP / 2; x += STEP) {
      const row: Record<string, number | null> = { dist: x }
      for (const c of curves) {
        row[`${c.id}`] = interp(c, x)
      }
      rows.push(row)
    }
    return rows
  }, [plottable])

  // Split table: same checkpoints across activities (400m intervals)
  const splitRows = useMemo(() => {
    if (plottable.length < 1) return []
    const maxLen = Math.max(...plottable.map((a) => a.splits?.length ?? 0))
    const rows: {
      segment: string
      cells: { activityId: number; seconds: number; pace: number | null; isBest: boolean }[]
    }[] = []
    for (let i = 0; i < maxLen; i++) {
      const cells = plottable
        .filter((a) => a.splits && a.splits[i])
        .map((a) => ({
          activityId: a.id,
          seconds: a.splits![i].seconds,
          pace: a.splits![i].pace_s_per_km,
        }))
      if (cells.length < 1) continue
      const best = Math.min(...cells.map((c) => c.seconds))
      // Segment label comes from an activity that HAS this split — counts
      // differ between activities (slightly different GPS distances), and
      // indexing plottable[0].splits[i] crashes when activity 0 is the
      // shorter one. All same-index splits cover ~the same segment anyway
      // (same checkpoints from a shared start); prefer the longest
      // activity's value so labels stay stable across renders.
      const labelSource =
        plottable.find((a) => a.splits && a.splits[i] && a.splits.length === maxLen) ??
        plottable.find((a) => a.splits && a.splits[i])
      rows.push({
        segment: `${(labelSource!.splits![i].start_m / 1000).toFixed(1)}–${(labelSource!.splits![i].end_m / 1000).toFixed(1)} km`,
        cells: cells.map((c) => ({ ...c, isBest: c.seconds === best })),
      })
    }
    return rows
  }, [plottable])

  if (!routeId || Number.isNaN(routeId)) {
    return <div className="p-8 text-gray-500">Invalid route id.</div>
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            Compare — {route?.name ?? `Route ${routeId}`}
          </h1>
          <p className="text-gray-600 mt-1">
            Same route, different days: GPS overlay, cumulative time, and splits
          </p>
        </div>
        <Link
          to="/routes"
          className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg bg-white text-gray-700 hover:bg-gray-50"
        >
          ← Routes
        </Link>
      </div>

      {/* Activity picker */}
      <div className="bg-white rounded-lg shadow-sm border p-4">
        <div className="flex items-center justify-between mb-2">
          <h2 className="font-semibold text-gray-900">Activities on this route</h2>
          <span className="text-xs text-gray-500">select 2–{MAX_SELECTABLE}</span>
        </div>
        {!route && <div className="text-sm text-gray-500">Loading activities…</div>}
        <div className="flex flex-wrap gap-2">
          {routeActivities.map((ra) => {
            const checked = selectedIds.includes(ra.id)
            return (
              <button
                key={ra.id}
                type="button"
                onClick={() => toggleActivity(ra.id)}
                className={`px-3 py-1.5 text-sm rounded-full border transition-colors ${
                  checked
                    ? 'text-white border-transparent'
                    : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
                }`}
                style={checked ? { backgroundColor: activityColor(ra.id) } : undefined}
              >
                {new Date(ra.start_date).toLocaleDateString()} ·{' '}
                {formatDistance(ra.distance, unit)}
              </button>
            )
          })}
        </div>
        {selectedIds.length < 2 && (
          <p className="text-xs text-amber-600 mt-2">
            Select at least 2 activities to compare.
          </p>
        )}
      </div>

      {/* Loading/error blocks removed from the document flow — the map
          card keeps its size and carries status overlays instead, so no
          layout shift when compare data arrives. */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800">Failed to load comparison. Try different activities.</p>
        </div>
      )}

      {/* Map card: always mounted so the map initializes on page load
          (initializing after compare data arrives was too late — the init
          effect ran once on mount, found no container, and never retried,
          leaving a blank card). Status overlays (hint / loading / updating)
          render inside the fixed-size card instead of shifting layout. */}
      <div className="bg-white rounded-lg shadow-sm border overflow-hidden">
        <div className="relative h-96 w-full">
          {mapError ? (
            <div className="h-96 flex items-center justify-center text-gray-500 bg-gray-50">
              Mapbox token not configured — GPS overlay unavailable
            </div>
          ) : (
            <>
              <div ref={mapContainer} className="h-96 w-full" />
              {!compare && !error && (
                <div className="absolute inset-0 flex items-center justify-center bg-white/70 text-sm text-gray-500">
                  {isLoading ? (
                    <div className="flex flex-col items-center gap-3">
                      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
                      <span>Loading comparison…</span>
                    </div>
                  ) : (
                    `Select 2–${MAX_SELECTABLE} activities below to overlay their GPS tracks`
                  )}
                </div>
              )}
              {compare && isFetching && (
                <div className="absolute top-3 right-3 bg-white/90 border border-gray-200 rounded-md px-2.5 py-1 text-xs text-gray-500 flex items-center gap-2">
                  <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-blue-600" />
                  Updating…
                </div>
              )}
            </>
          )}
        </div>
        {compare && (
          <div className="p-3 flex flex-wrap gap-4 border-t">
            {compareActivities.map((a) => (
              <div key={a.id} className="flex items-center gap-1.5 text-sm">
                <span
                  className="w-3 h-3 rounded-full inline-block"
                  style={{ backgroundColor: activityColor(a.id) }}
                />
                <span className="text-gray-700">
                  {new Date(a.summary.start_date).toLocaleDateString()}
                    {a.direction_reversed && ' (ran reverse — no time compare)'}
                  </span>
                </div>
              ))}
            </div>
        )}
      </div>

        {compare && (
          <>
          {/* Race plot */}
          {plottable.length >= 1 && raceData.length > 1 && (
            <div className="bg-white rounded-lg shadow-sm border p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-1">
                Cumulative time vs distance
              </h3>
              <p className="text-xs text-gray-500 mb-4">
                Lower is faster. Vertical jumps = pauses (clock kept running).
              </p>
              <ResponsiveContainer width="100%" height={360}>
                <LineChart data={raceData} margin={{ top: 5, right: 20, bottom: 25, left: 10 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis
                    dataKey="dist"
                    stroke="#9ca3af"
                    fontSize={12}
                    tick={{ fill: '#6b7280' }}
                    tickFormatter={(v) => (unit === 'imperial' ? (((v as number) / 1609.344).toFixed(1)) : (((v as number) / 1000).toFixed(1)))}
                    label={{
                      value: `Distance (${distanceUnitLabel(unit)})`,
                      position: 'insideBottom',
                      offset: -15,
                      style: { fill: '#6b7280', fontSize: 12 },
                    }}
                  />
                  <YAxis
                    stroke="#9ca3af"
                    fontSize={12}
                    tick={{ fill: '#6b7280' }}
                    tickFormatter={(v) => formatDuration(v as number)}
                    width={70}
                    domain={['dataMin', 'dataMax']}
                    tickCount={6}
                  />
                  <Tooltip
                    content={({ active, payload, label }: any) => {
                      if (!active || !payload || payload.length === 0) return null
                      return (
                        <div className="bg-white border border-gray-200 rounded-lg shadow-lg p-3">
                          <p className="text-sm font-medium text-gray-900 mb-2">
                            {unit === 'imperial'
                              ? `${((label as number) / 1609.344).toFixed(2)} mi`
                              : `${((label as number) / 1000).toFixed(2)} km`}
                          </p>
                          {payload.map((entry: any) => {
                            const act = compareActivities.find((a) => String(a.id) === entry.dataKey)
                            return (
                              <div key={entry.dataKey} className="flex items-center gap-2 text-sm">
                                <div
                                  className="w-3 h-3 rounded-full"
                                  style={{ backgroundColor: entry.color ?? entry.stroke }}
                                />
                                <span className="text-gray-600">
                                  {act
                                    ? new Date(act.summary.start_date).toLocaleDateString()
                                    : entry.dataKey}
                                  :
                                </span>
                                <span className="font-medium text-gray-900">
                                  {formatDuration(entry.value as number)}
                                </span>
                              </div>
                            )
                          })}
                        </div>
                      )
                    }}
                  />
                  <Legend
                    content={() => (
                      <div className="flex flex-wrap gap-4 mt-4 justify-center">
                        {plottable.map((a) => (
                          <div key={a.id} className="flex items-center gap-2 text-sm">
                            <div
                              className="w-3 h-3 rounded-full"
                              style={{ backgroundColor: activityColor(a.id) }}
                            />
                            <span className="text-gray-600">
                              {new Date(a.summary.start_date).toLocaleDateString()}
                            </span>
                          </div>
                        ))}
                      </div>
                    )}
                  />
                  {plottable.map((a) => (
                    <Line
                      key={a.id}
                      type="monotone"
                      dataKey={`${a.id}`}
                      stroke={activityColor(a.id)}
                      strokeWidth={2}
                      dot={{ fill: activityColor(a.id), r: 2 }}
                      activeDot={{ r: 4 }}
                      connectNulls={false}
                      isAnimationActive={false}
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Split table */}
          {plottable.length >= 1 && splitRows.length > 0 && (
            <div className="bg-white rounded-lg shadow-sm border p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900">
                  Splits ({splitIntervalLabel(splitInterval, unit)})
                </h3>
                <div className="flex items-center gap-1" role="group" aria-label="Split length">
                  {[1000, 800, 400].map((m) => (
                    <button
                      key={m}
                      type="button"
                      onClick={() => setSplitInterval(m)}
                      className={`px-2.5 py-1 text-xs font-medium rounded-md border transition-colors ${
                        splitInterval === m
                          ? 'bg-blue-600 text-white border-blue-600'
                          : 'bg-white text-gray-600 border-gray-300 hover:bg-gray-50'
                      }`}
                    >
                      {splitIntervalLabel(m, unit)}
                    </button>
                  ))}
                </div>
              </div>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead>
                    <tr>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                        Segment
                      </th>
                      {plottable.map((a) => (
                        <th
                          key={a.id}
                          className="px-4 py-2 text-right text-xs font-medium uppercase"
                          style={{ color: activityColor(a.id) }}
                        >
                          {new Date(a.summary.start_date).toLocaleDateString()}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {splitRows.map((row, i) => (
                      <tr key={i}>
                        <td className="px-4 py-2 text-sm text-gray-700">{row.segment}</td>
                        {row.cells.map((cell) => (
                          <td key={cell.activityId} className="px-4 py-2 text-sm text-right">
                            {cell.isBest ? (
                              <span className="inline-block px-2 py-0.5 rounded-full bg-green-100 text-green-800 font-semibold">
                                {formatDuration(cell.seconds)}
                                <span className="text-green-600 text-xs ml-2">
                                  {formatPace(cell.pace, unit)}
                                </span>
                              </span>
                            ) : (
                              <span className="text-gray-600">
                                {formatDuration(cell.seconds)}
                                <span className="text-gray-400 text-xs ml-2">
                                  {formatPace(cell.pace, unit)}
                                </span>
                              </span>
                            )}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Summary comparison */}
          <div className="bg-white rounded-lg shadow-sm border p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Summary</h3>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead>
                  <tr>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Metric</th>
                    {compareActivities.map((a) => (
                      <th
                        key={a.id}
                        className="px-4 py-2 text-right text-xs font-medium uppercase"
                        style={{ color: activityColor(a.id) }}
                      >
                        {new Date(a.summary.start_date).toLocaleDateString()}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {[
                    {
                      label: 'Moving time',
                      get: (a: CompareActivity) => formatDuration(a.summary.moving_time ?? 0),
                    },
                    {
                      label: 'Distance',
                      get: (a: CompareActivity) => formatDistance(a.summary.distance, unit),
                    },
                    {
                      label: 'Avg HR',
                      get: (a: CompareActivity) => a.summary.average_heartrate?.toFixed(0) ?? '—',
                    },
                    {
                      label: 'Elevation gain',
                      get: (a: CompareActivity) => formatElevationCompare(a.summary.total_elevation_gain, unit),
                    },
                  ].map((metric) => (
                    <tr key={metric.label}>
                      <td className="px-4 py-2 text-sm text-gray-700">{metric.label}</td>
                      {compareActivities.map((a) => (
                        <td key={a.id} className="px-4 py-2 text-sm text-right text-gray-600">
                          {metric.get(a)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
          </>
        )}
    </div>
  )
}