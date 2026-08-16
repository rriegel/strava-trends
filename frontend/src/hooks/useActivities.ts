import { useQuery } from '@tanstack/react-query'
import { getActivities, getActivity, getActivityStreams } from '../api/activities'
import type { ActivitiesResponse } from '../api/activities'
import type { Activity, ActivityStream } from '../types'

export function useActivities(params: {
  page?: number
  per_page?: number
  type?: string
  distance_bucket?: string
  effort_zone?: string
  terrain_type?: string
  start_date?: string
  end_date?: string
}) {
  return useQuery<ActivitiesResponse>({
    queryKey: ['activities', params],
    queryFn: () => getActivities(params),
  })
}

export function useActivity(id: number) {
  return useQuery<Activity>({
    queryKey: ['activity', id],
    queryFn: () => getActivity(id),
    enabled: !!id,
  })
}

export function useActivityStreams(id: number) {
  return useQuery<ActivityStream[]>({
    queryKey: ['activity-streams', id],
    queryFn: () => getActivityStreams(id),
    enabled: !!id,
  })
}
