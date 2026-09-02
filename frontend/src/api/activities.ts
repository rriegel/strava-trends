import apiClient from './client'

export interface ActivitySummary {
  id: number
  strava_id: number | null
  name: string
  type: string
  sport_type: string | null
  start_date: string
  start_date_local: string
  moving_time: number | null
  distance: number | null
  total_elevation_gain: number | null
  average_speed: number | null
  average_heartrate: number | null
  max_heartrate: number | null
  average_cadence: number | null
  average_watts: number | null
  suffer_score: number | null
  device_name: string | null
  distance_bucket: string | null
  effort_zone: string | null
  terrain_type: string | null
  route_id: number | null
  has_streams: boolean
}

export interface ActivityDetail extends ActivitySummary {
  elapsed_time: number | null
  max_speed: number | null
  has_heartrate: boolean
  weighted_average_watts: number | null
  max_watts: number | null
  kilojoules: number | null
  gear_id: string | null
  computed_metrics: Array<{
    metric_type: string
    value: number
    computed_at: string
  }>
  effort_groups: Array<{
    group_type: string
    group_label: string
    group_value: string
    time_in_zone: number | null
  }>
  created_at: string
  updated_at: string | null
}

export interface Pagination {
  page: number
  per_page: number
  total: number
  total_pages: number
}

export interface ActivitiesResponse {
  activities: ActivitySummary[]
  pagination: Pagination
}

export interface ActivityFilters {
  type?: string
  start_date?: string
  end_date?: string
  distance_bucket?: string
  effort_zone?: string
  terrain_type?: string
  route_id?: number
  sort_by?: string
  sort_order?: 'asc' | 'desc'
  page?: number
  per_page?: number
}

export interface EffortZoneBreakdown {
  zone: string
  label: string
  time_seconds: number
  percentage: number
}

export interface EffortData {
  activity_id: number
  max_hr: number
  dominant_zone: string
  total_time: number
  zone_breakdown: EffortZoneBreakdown[]
}

export interface CalendarDay {
  date: string
  value: number
  count: number
}

export interface CalendarSummary {
  total_activities: number
  total_distance: number
  total_moving_time: number
  longest_streak: number
  most_active_day: string
}

export interface CalendarResponse {
  metric: string
  data: CalendarDay[]
  start_date: string
  end_date: string
  summary: CalendarSummary
}

export const activitiesApi = {
  async list(filters: ActivityFilters = {}): Promise<ActivitiesResponse> {
    const params = new URLSearchParams()
    
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        params.set(key, String(value))
      }
    })
    
    const response = await apiClient.get<ActivitiesResponse>(
      `/activities/?${params.toString()}`
    )
    return response.data
  },

  async getCalendar(params: {
    start_date?: string
    end_date?: string
    metric?: 'distance' | 'count' | 'moving_time'
  } = {}): Promise<CalendarResponse> {
    const searchParams = new URLSearchParams()
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        searchParams.set(key, String(value))
      }
    })
    const response = await apiClient.get<CalendarResponse>(
      `/activities/calendar?${searchParams.toString()}`
    )
    return response.data
  },

  async getDetail(activityId: number): Promise<ActivityDetail> {
    const response = await apiClient.get<ActivityDetail>(
      `/activities/${activityId}`
    )
    return response.data
  },

  async delete(activityId: number): Promise<void> {
    await apiClient.delete(`/activities/${activityId}`)
  },

  async getEffort(activityId: number): Promise<EffortData> {
    const response = await apiClient.get<EffortData>(
      `/activities/${activityId}/effort`
    )
    return response.data
  },
}
