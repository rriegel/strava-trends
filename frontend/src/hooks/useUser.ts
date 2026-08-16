import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getCurrentUser, updateUser, syncActivities } from '../api/auth'
import type { User } from '../types'

export function useCurrentUser() {
  return useQuery<User>({
    queryKey: ['currentUser'],
    queryFn: getCurrentUser,
  })
}

export function useUpdateUser() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: updateUser,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['currentUser'] })
    },
  })
}

export function useSyncActivities() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: syncActivities,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['activities'] })
      queryClient.invalidateQueries({ queryKey: ['currentUser'] })
    },
  })
}
