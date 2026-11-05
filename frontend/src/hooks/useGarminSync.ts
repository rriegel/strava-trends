import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { garminSyncApi, type GarminSyncReport, type GarminSyncStatus } from '../api/garminSync'

/**
 * Query families derived from synced activities — mirrors
 * UPLOAD_INVALIDATED_KEYS in useFileUpload.ts. A sync inserts activities
 * (with streams/routes), so every aggregate over activities must refetch.
 */
const SYNC_INVALIDATED_KEYS = [
  'activities',
  'routes',
  'route',
  'route-compare',
  'calendar',
  'multi-trend',
  'percentile-bands',
  'currentUser',
] as const

export function useGarminSyncStatus() {
  return useQuery<GarminSyncStatus>({
    queryKey: ['garminSyncStatus'],
    queryFn: garminSyncApi.status,
    staleTime: 60_000,
  })
}

export interface UseGarminSyncResult {
  sync: (backfill?: boolean, limit?: number) => Promise<GarminSyncReport>
  isSyncing: boolean
  error: string | null
  report: GarminSyncReport | null
  clearReport: () => void
}

export function useGarminSync(): UseGarminSyncResult {
  const queryClient = useQueryClient()

  const mutation = useMutation<GarminSyncReport, Error, { backfill: boolean; limit?: number }>({
    mutationFn: ({ backfill, limit }) => garminSyncApi.sync(backfill, limit),
    onSuccess: (report) => {
      if (report.synced > 0) {
        // Only invalidate when something actually imported — a skipped-only
        // sync changed no data (duplicates are data-preserving by design).
        for (const key of SYNC_INVALIDATED_KEYS) {
          queryClient.invalidateQueries({ queryKey: [key] })
        }
      }
      // Always refresh the status badge (last_sync_at moved even on no-op syncs)
      queryClient.invalidateQueries({ queryKey: ['garminSyncStatus'] })
    },
  })

  const sync = (backfill = false, limit?: number) =>
    mutation.mutateAsync({ backfill, limit })

  return {
    sync,
    isSyncing: mutation.isPending,
    error: mutation.error ? mutation.error.message : null,
    report: mutation.data ?? null,
    clearReport: () => mutation.reset(),
  }
}
