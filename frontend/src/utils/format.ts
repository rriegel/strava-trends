export function formatPace(speedMps: number): string {
  if (!speedMps || speedMps === 0) return '--:--'
  const paceSecondsPerKm = 1000 / speedMps
  const minutes = Math.floor(paceSecondsPerKm / 60)
  const seconds = Math.round(paceSecondsPerKm % 60)
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
