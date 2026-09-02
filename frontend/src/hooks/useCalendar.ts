import { useQuery } from '@tanstack/react-query'
import { activitiesApi } from '../api/activities'

export function useCalendar(params: {
  start_date?: string
  end_date?: string
  metric?: 'distance' | 'count' | 'moving_time'
} = {}) {
  return useQuery({
    queryKey: ['calendar', params],
    queryFn: () => activitiesApi.getCalendar(params),
  })
}
