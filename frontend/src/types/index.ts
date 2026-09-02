export interface User {
  id: number
  strava_athlete_id: number
  firstname: string
  lastname: string
  username: string
  profile_url: string
  city: string
  state: string
  country: string
  default_distance_unit: string
  last_sync_at: string
  sync_status: string
}

export interface Activity {
  id: number
  strava_id: number
  name: string
  type: string
  sport_type: string
  start_date: string
  start_date_local: string
  moving_time: number
  elapsed_time: number
  distance: number
  total_elevation_gain: number
  average_speed: number
  max_speed: number
  average_heartrate: number
  max_heartrate: number
  has_heartrate: boolean
  average_watts: number
  average_cadence: number
  suffer_score: number
  device_name: string
  distance_bucket: string
  effort_zone: string
  terrain_type: string
  route_id: number | null
  has_streams: boolean
}

export interface ActivityStream {
  stream_type: string
  data: number[]
  series_type: string
  original_size: number
  resolution: string
}

export interface Route {
  id: number
  name: string
  distance: number
  elevation_gain: number
  activity_count: number
  cluster_id: number | null
  start_lat: number
  start_lng: number
  polyline: string
}

export interface TrendData {
  metric_type: string
  unit: string
  data_points: { date: string; value: number }[]
  aggregated_data: { period: string; value: number; min: number; max: number; count: number }[]
  trend: { slope: number; direction: string; r_squared: number }
}

export interface PercentileBand {
  date: string
  count: number
  p10: number
  p25?: number
  p50: number
  p75?: number
  p90: number
}

export interface PercentileData {
  metric_type: string
  bands: PercentileBand[]
}

export interface Pagination {
  page: number
  per_page: number
  total: number
  total_pages: number
}
