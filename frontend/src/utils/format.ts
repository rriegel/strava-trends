/**
 * Display formatting with unit-system support.
 *
 * Raw values are always SI (meters, m/s); conversion happens at the edge:
 *   - Distance/elevation: converted HERE (client-side) per the user's
 *     users.default_distance_unit preference — see context/units.tsx
 *   - Pace: the Trends API already returns converted values (min/km or min/mi
 *     depending on the user's preference), so formatPaceDecimal only formats;
 *     formatPace converts raw m/s input (activity cards, detail views).
 */

export type UnitSystem = 'metric' | 'imperial'

const M_PER_MI = 1609.344 // meters per mile — for meter-quantity conversions (distance)
// NOTE pace: min/mi = (M_PER_MI meters) / (speed m/s) / 60 — meters cancel to
// seconds-per-mile, so the 1609.344 factor IS correct there. Do not "fix" it
// to 1.609344 (that's the km-per-mile factor for converting min/km values).
const FT_PER_M = 3.280839895013123 // exact: 1 ft = 0.3048 m

/**
 * Check if a metric is displayed as pace (min/km or min/mi).
 *
 *   - average_speed: stored m/s in DB, arrives as pace from the trends API
 *   - grade_adjusted_pace: stored and arrives as pace
 */
export function isPaceDisplay(metricType: string): boolean {
  return metricType === 'average_speed' || metricType === 'grade_adjusted_pace'
}

/**
 * Distance-unit suffix for the current unit system (for pace labels:
 * "/km" vs "/mi", "min/km per day", "Distance (km)" etc.)
 */
export function distanceUnitLabel(unit: UnitSystem = 'metric'): string {
  return unit === 'imperial' ? 'mi' : 'km'
}

/**
 * Elevation unit suffix for the current unit system ("m" vs "ft")
 */
export function elevationUnitLabel(unit: UnitSystem = 'metric'): string {
  return unit === 'imperial' ? 'ft' : 'm'
}

/**
 * Format speed (m/s) as pace string (M:SS), converting to the unit system.
 * @param speedMps Speed in meters per second
 * @param unit Unit system; imperial gives min/mi
 * @returns Formatted pace string (e.g., "5:00")
 */
export function formatPace(speedMps: number, unit: UnitSystem = 'metric'): string {
  if (!speedMps || speedMps === 0) return '--:--'
  const secondsPerUnit = (unit === 'imperial' ? M_PER_MI : 1000) / speedMps
  const minutes = Math.floor(secondsPerUnit / 60)
  const seconds = Math.round(secondsPerUnit % 60)
  return `${minutes}:${seconds.toString().padStart(2, '0')}`
}

/**
 * Format a decimal pace value (decimal minutes per unit) as M:SS string.
 * No conversion: the trends API already returns values in the user's unit
 * system; this only renders.
 * @param paceDecimal Pace in decimal minutes (e.g., 5.5 = 5:30)
 * @returns Formatted pace string (e.g., "5:30")
 */
export function formatPaceDecimal(paceDecimal: number): string {
  if (!paceDecimal || paceDecimal <= 0) return '--:--'
  const totalSeconds = Math.round(paceDecimal * 60)
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `${minutes}:${seconds.toString().padStart(2, '0')}`
}

export function formatDistance(meters: number, unit: UnitSystem = 'metric'): string {
  if (unit === 'imperial') {
    const miles = meters / M_PER_MI
    return `${miles.toFixed(2)} mi`
  }
  const km = meters / 1000
  return `${km.toFixed(2)} km`
}

export function formatDuration(seconds: number): string {
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = seconds % 60
  if (h > 0) return `${h}h ${m}m ${s}s`
  if (m > 0) return `${m}m ${s}s`
  return `${s}s`
}

export function formatElevation(meters: number, unit: UnitSystem = 'metric'): string {
  if (unit === 'imperial') {
    const feet = meters * FT_PER_M
    return `${Math.round(feet)} ft`
  }
  return `${Math.round(meters)} m`
}

export function formatHeartrate(bpm: number): string {
  return `${Math.round(bpm)} bpm`
}
