import apiClient from './client'

export interface UserProfile {
  id: number
  strava_athlete_id: number
  firstname: string
  lastname: string
  username: string | null
  profile_url: string | null
  city: string | null
  state: string | null
  country: string | null
  default_distance_unit: string
  preferred_hr_zones: Record<string, { min: number; max: number }> | null
  max_hr: number | null
  last_sync_at: string | null
  sync_status: string
  created_at: string | null
}

export interface UserPreferencesUpdate {
  max_hr?: number | null
  default_distance_unit?: string
}

export interface PreferencesUpdateResponse {
  message: string
  max_hr: number | null
  default_distance_unit: string
}

export const usersApi = {
  async getProfile(): Promise<UserProfile> {
    const response = await apiClient.get<UserProfile>('/users/me')
    return response.data
  },

  async updatePreferences(preferences: UserPreferencesUpdate): Promise<PreferencesUpdateResponse> {
    const response = await apiClient.patch<PreferencesUpdateResponse>('/users/me', preferences)
    return response.data
  },
}
