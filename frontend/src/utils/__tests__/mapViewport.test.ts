import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import {
  loadViewport,
  saveViewport,
  saveViewportFromMap,
  createViewportSaver,
} from '../mapViewport'

describe('mapViewport', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('returns null when nothing saved', () => {
    expect(loadViewport('routes')).toBeNull()
  })

  it('saves and loads a viewport round-trip', () => {
    saveViewport('routes', { lng: -83.74, lat: 42.28, zoom: 12.5, bearing: 10, pitch: 30 })
    expect(loadViewport('routes')).toEqual({
      lng: -83.74,
      lat: 42.28,
      zoom: 12.5,
      bearing: 10,
      pitch: 30,
    })
  })

  it('rejects corrupt JSON and out-of-range values', () => {
    localStorage.setItem('strava-trends:map-viewport:routes', 'not json')
    expect(loadViewport('routes')).toBeNull()
    localStorage.setItem(
      'strava-trends:map-viewport:routes',
      JSON.stringify({ lng: 999, lat: 42, zoom: 10 })
    )
    expect(loadViewport('routes')).toBeNull()
    localStorage.setItem(
      'strava-trends:map-viewport:routes',
      JSON.stringify({ lng: -83, lat: 42 })
    )
    expect(loadViewport('routes')).toBeNull()
  })

  it('keys are isolated per page', () => {
    saveViewport('routes', { lng: 1, lat: 2, zoom: 3 })
    expect(loadViewport('route-compare')).toBeNull()
  })

  it('saveViewportFromMap reads center/zoom/bearing/pitch off the map', () => {
    saveViewportFromMap('routes', {
      getCenter: () => ({ lng: -83.7, lat: 42.3 }),
      getZoom: () => 11.2,
      getBearing: () => 5,
      getPitch: () => 0,
    })
    expect(loadViewport('routes')).toEqual({
      lng: -83.7,
      lat: 42.3,
      zoom: 11.2,
      bearing: 5,
      pitch: 0,
    })
  })

  describe('createViewportSaver', () => {
    it('saves on user moveend, skips marked programmatic moves', () => {
      const handlers: Record<string, () => void> = {}
      const fakeMap = {
        on: (event: string, handler: () => void) => {
          handlers[event] = handler
        },
        getCenter: () => ({ lng: -83.5, lat: 42.2 }),
        getZoom: () => 10,
        getBearing: () => 0,
        getPitch: () => 0,
      }
      const saver = createViewportSaver('routes', fakeMap as never)

      // User pan -> saved
      handlers['moveend']()
      expect(loadViewport('routes')?.lng).toBe(-83.5)

      // Programmatic fit -> skipped, flag consumed (next user move saves again)
      saver.markProgrammatic()
      handlers['moveend']()
      expect(loadViewport('routes')?.lng).toBe(-83.5) // unchanged
      handlers['moveend']()
      expect(loadViewport('routes')?.lng).toBe(-83.5) // still -83.5, flag consumed
    })

    it('storage failures are non-fatal', () => {
      vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
        throw new Error('quota')
      })
      const handlers: Record<string, () => void> = {}
      const fakeMap = {
        on: (event: string, handler: () => void) => {
          handlers[event] = handler
        },
        getCenter: () => ({ lng: 0, lat: 0 }),
        getZoom: () => 1,
        getBearing: () => 0,
        getPitch: () => 0,
      }
      createViewportSaver('routes', fakeMap as never)
      expect(() => handlers['moveend']()).not.toThrow()
    })
  })
})