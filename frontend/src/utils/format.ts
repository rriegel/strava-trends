/**
 * Check if a metric type is a pace metric (stored as speed in m/s, displayed as pace in min/km)
 */
export function isPaceMetric(metricType: string): boolean {
  return metricType === 'average_speed' || metricType === 'grade_adjusted_pace'
}

/**
 * Convert speed (m/s) to pace (min/km) as a decimal number
 * @param speedMps Speed in meters per second
 * @returns Pace in minutes per km (e.g., 5.5 = 5:30 min/km)
 */
export function convertSpeedToPace(speedMps: number): number {
  if (!speedMps || speedMps === 0) return 0
  return 1000 / speedMps / 60
}

/**
 * Format speed (m/s) as pace string (M:SS min/km)
 * @param speedMps Speed in meters per second
 * @returns Formatted pace string (e.g., "5:00")
 */
export function formatPace(speedMps: number): string {
  if (!speedMps || speedMps === 0) return '--:--'
  const paceSecondsPerKm = 1000 / speedMps
  const minutes = Math.floor(paceSecondsPerKm / 60)
  const seconds = Math.round(paceSecondsPerKm % 60)
  return `${minutes}:${seconds.toString().padStart(2, '0')}`
}

/**
 * Format a decimal pace value (min/km) as M:SS string
 * @param paceDecimal Pace in decimal minutes (e.g., 5.5 = 5:30)
 * @returns Formatted pace string (e.g., "5:30")
 */
export function formatPaceDecimal(paceDecimal: number): string {
  if (!paceDecimal || paceDecimal === 0) return '--:--'
  const minutes = Math.floor(paceDecimal)
  const seconds = Math.round((paceDecimal - minutes) * 60)
  return `${minutes}:${seconds.toString().padStart(2, '0')}`
}

export function formatDistance(meters: number, unit: string = 'metric'): string {
  if (unit === 'imperial') {
    const miles = meters / 1609.344
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

export function formatElevation(meters: number): string {
  return `${Math.round(meters)} m`
}

export function formatHeartrate(bpm: number): string {
  return `${Math.round(bpm)} bpm`
}
