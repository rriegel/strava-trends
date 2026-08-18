import apiClient from './client'

export interface StravaConnectResponse {
  authorization_url: string
}

export interface SyncResponse {
  status: string
  synced_count: number
}

export async function getStravaConnectUrl(): Promise<StravaConnectResponse> {
  const response = await apiClient.get('/auth/strava/connect')
  return response.data
}

export async function handleStravaCallback(code: string): Promise<any> {
  const response = await apiClient.post('/auth/strava/callback', null, {
    params: { code }
  })
  return response.data
}

export async function syncStravaActivities(): Promise<SyncResponse> {
  const response = await apiClient.post('/activities/sync')
  return response.data
}
