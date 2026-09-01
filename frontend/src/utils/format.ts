/**
 * Check if a metric type needs speed-to-pace conversion (stored as m/s, displayed as min/km)
 * Note: grade_adjusted_pace is already stored as min/km, so it doesn't need conversion
 */
export function isPaceMetric(metricType: string): boolean {
  return metricType === 'average_speed'
}

/**
 * Check if a metric is displayed as pace (for formatting purposes)
 * This includes both metrics that need conversion and those already in pace format
 */
export function isPaceDisplay(metricType: string): boolean {
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

/**
 * Calculate linear regression trend for data points
 * @param dataPoints Array of {date: string, value: number}
 * @returns Trend object with slope, direction, r_squared
 */
export function calculateTrend(dataPoints: { date: string; value: number }[]): {
  slope: number
  direction: 'increasing' | 'decreasing' | 'stable'
  r_squared: number
} {
  if (dataPoints.length < 2) {
    return { slope: 0, direction: 'stable', r_squared: 0 }
  }

  // Convert dates to numeric (days since first date)
  const startDate = new Date(dataPoints[0].date)
  const x = dataPoints.map((d) => {
    const date = new Date(d.date)
    return (date.getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24)
  })
  const y = dataPoints.map((d) => d.value)

  const n = x.length
  const sumX = x.reduce((a, b) => a + b, 0)
  const sumY = y.reduce((a, b) => a + b, 0)
  const sumXY = x.reduce((acc, xi, i) => acc + xi * y[i], 0)
  const sumX2 = x.reduce((acc, xi) => acc + xi * xi, 0)
  const sumY2 = y.reduce((acc, yi) => acc + yi * yi, 0)

  // Calculate slope and intercept
  const denominator = n * sumX2 - sumX * sumX
  if (denominator === 0) {
    return { slope: 0, direction: 'stable', r_squared: 0 }
  }

  const slope = (n * sumXY - sumX * sumY) / denominator
  const intercept = (sumY - slope * sumX) / n

  // Calculate R-squared
  const yMean = sumY / n
  const ssTotal = sumY2 - n * yMean * yMean
  const ssResidual = y.reduce((acc, yi, i) => {
    const predicted = slope * x[i] + intercept
    return acc + (yi - predicted) ** 2
  }, 0)

  const r_squared = ssTotal === 0 ? 0 : 1 - ssResidual / ssTotal

  // Determine direction
  let direction: 'increasing' | 'decreasing' | 'stable'
  if (slope > 0.01) {
    direction = 'increasing'
  } else if (slope < -0.01) {
    direction = 'decreasing'
  } else {
    direction = 'stable'
  }

  return { slope, direction, r_squared }
}
