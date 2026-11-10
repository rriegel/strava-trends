/**
 * Query keys that must be invalidated whenever activity data changes
 * (upload, sync, delete). Any new activity-derived query family belongs in
 * this list — see useFileUpload.ts header comment for why (staleTime 5min
 * serves pre-change data otherwise).
 */
export const ACTIVITY_DATA_INVALIDATED_KEYS = [
  'activities',
  'routes',
  'route',
  'route-compare',
  'calendar',
  'multi-trend',
  'percentile-bands',
  'currentUser',
] as const
