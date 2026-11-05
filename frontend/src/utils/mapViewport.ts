/**
 * Map viewport persistence — the pattern Google Maps / Strava use to avoid
 * the "sweeping pan" on every page load: remember where the user left the
 * camera, restore it instantly on init, and only animate camera moves the
 * user deliberately caused (Fit-all button, selection focus). Data-driven
 * reframes (routes loaded, tracks drawn) never animate.
 *
 * Viewports are keyed per page so different views don't fight over one
 * camera. localStorage failures (privacy mode, quota) are non-fatal.
 */

export interface MapViewport {
  lng: number
  lat: number
  zoom: number
  bearing?: number
  pitch?: number
}

const PREFIX = 'strava-trends:map-viewport:'

export function loadViewport(key: string): MapViewport | null {
  try {
    const raw = localStorage.getItem(PREFIX + key)
    if (!raw) return null
    const parsed = JSON.parse(raw)
    if (
      typeof parsed?.lng !== 'number' ||
      typeof parsed?.lat !== 'number' ||
      typeof parsed?.zoom !== 'number' ||
      Math.abs(parsed.lat) > 90 ||
      Math.abs(parsed.lng) > 180 ||
      parsed.zoom < 0 ||
      parsed.zoom > 22
    ) {
      return null
    }
    return parsed as MapViewport
  } catch {
    return null
  }
}

export function saveViewport(key: string, viewport: MapViewport): void {
  try {
    localStorage.setItem(PREFIX + key, JSON.stringify(viewport))
  } catch {
    // storage unavailable — persistence is best-effort
  }
}

/** Convenience: save straight from a Mapbox GL map instance. */
export function saveViewportFromMap(
  key: string,
  map: { getCenter: () => { lng: number; lat: number }; getZoom: () => number; getBearing: () => number; getPitch: () => number }
): void {
  const c = map.getCenter()
  saveViewport(key, {
    lng: c.lng,
    lat: c.lat,
    zoom: map.getZoom(),
    bearing: map.getBearing(),
    pitch: map.getPitch(),
  })
}

/**
 * Wire moveend-saving with a programmatic-move guard: set the returned
 * flag true BEFORE any programmatic fitBounds so the resulting moveend
 * doesn't overwrite the user's saved camera; user-initiated pan/zooms
 * (no flag) save normally.
 */
export function createViewportSaver(
  key: string,
  map: {
    on: (event: string, handler: () => void) => void
    getCenter: () => { lng: number; lat: number }
    getZoom: () => number
    getBearing: () => number
    getPitch: () => number
  }
): { markProgrammatic: () => void } {
  let programmatic = false
  map.on('moveend', () => {
    if (programmatic) {
      programmatic = false
      return
    }
    saveViewportFromMap(key, map)
  })
  return {
    markProgrammatic: () => {
      programmatic = true
    },
  }
}
