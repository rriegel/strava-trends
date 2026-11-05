import apiClient from './client'

export interface GarminDuplicateEntry {
  garmin_activity_id: string
  garmin_start: string
  garmin_distance: number | null
  garmin_name: string | null
  existing_activity_id: number
  existing_source: string
  existing_name: string | null
}

export interface GarminSyncReport {
  status: 'success' | 'error'
  synced: number
  skipped: number
  failed: number
  duplicates: GarminDuplicateEntry[]
  failures: { garmin_activity_id: string | null; error: string }[]
  cursor_before: string | null
  cursor_after: string | null
}

export interface GarminSyncStatus {
  key_configured: boolean
  key_expires_at: string | null
  key_days_left: number | null
  key_expired: boolean
  key_warning: boolean
  last_sync_at: string | null
  cursor: string | null
}

export const garminSyncApi = {
  async sync(backfill: boolean = false, limit?: number): Promise<GarminSyncReport> {
    const params: Record<string, string | number> = {}
    if (backfill) params.backfill = 'true'
    if (limit !== undefined) params.limit = limit
    const response = await apiClient.post<GarminSyncReport>('/sync/garmin', null, { params })
    return response.data
  },

  async importSingle(garminActivityId: string): Promise<GarminSyncReport> {
    const response = await apiClient.post<GarminSyncReport>(
      `/sync/garmin/${garminActivityId}`
    )
    return response.data
  },

  async status(): Promise<GarminSyncStatus> {
    const response = await apiClient.get<GarminSyncStatus>('/sync/garmin/status')
    return response.data
  },
}
