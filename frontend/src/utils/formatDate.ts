/**
 * Format ISO date string to readable format: "6:00pm 7/26/2026"
 */
export function formatDateTime(isoString: string): string {
  const date = new Date(isoString)
  
  // Format time: "6:00pm"
  const hours = date.getHours()
  const minutes = date.getMinutes()
  const ampm = hours >= 12 ? 'pm' : 'am'
  const displayHours = hours % 12 || 12
  const displayMinutes = minutes.toString().padStart(2, '0')
  const timeStr = `${displayHours}:${displayMinutes}${ampm}`
  
  // Format date: "7/26/2026"
  const month = date.getMonth() + 1
  const day = date.getDate()
  const year = date.getFullYear()
  const dateStr = `${month}/${day}/${year}`
  
  return `${timeStr} ${dateStr}`
}
