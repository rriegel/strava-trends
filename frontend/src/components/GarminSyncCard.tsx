import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useGarminSync, useGarminSyncStatus } from '../hooks/useGarminSync'
import { activitiesApi } from '../api/activities'
import { garminSyncApi, type GarminDuplicateEntry } from '../api/garminSync'

/**
 * Garmin sync controls for the Activities page:
 * - "Sync now" button (incremental) with last-synced + key-expiry chips
 * - Collapsible backfill control (initial history pull)
 * - Inline report after a sync run
 * - Duplicate Review section (rendered only when the last report has
 *   cross-source duplicates) — keep-existing default, replace-with-garmin
 *   deletes the manual twin then re-syncs that garmin id.
 */
export default function GarminSyncCard() {
  const { data: status } = useGarminSyncStatus()
  const { sync, isSyncing, error, report, clearReport } = useGarminSync()
  const queryClient = useQueryClient()
  const [showBackfill, setShowBackfill] = useState(false)
  const [backfillLimit, setBackfillLimit] = useState('')
  const [replacingIds, setReplacingIds] = useState<Set<string>>(new Set())
  const [replaceErrors, setReplaceErrors] = useState<Record<string, string>>({})
  // Duplicate review session: seeded from the first report carrying
  // duplicates, then PERSISTS across per-row actions (mutation data is
  // replaced by every sync call, so it can't hold the working list).
  const [reviewQueue, setReviewQueue] = useState<GarminDuplicateEntry[] | null>(null)

  const handleSync = async (backfill: boolean) => {
    const limit = backfill && backfillLimit ? parseInt(backfillLimit, 10) : undefined
    try {
      const result = await sync(backfill, Number.isNaN(limit ?? NaN) ? undefined : limit)
      // Seed the review session only on a fresh duplicates-bearing report —
      // never clobber an in-progress review with a partial report.
      if (result.duplicates.length > 0) {
        setReviewQueue(result.duplicates)
      }
    } catch {
      // error surfaced via hook state
    }
  }

  const handleReplace = async (dup: GarminDuplicateEntry) => {
    setReplacingIds((prev) => new Set(prev).add(dup.garmin_activity_id))
    setReplaceErrors((prev) => {
      const next = { ...prev }
      delete next[dup.garmin_activity_id]
      return next
    })
    try {
      await replaceOne(dup)
      // Row resolved: remove it from the review queue in place. The rest
      // of the queue is untouched — the user keeps working through it.
      setReviewQueue((prev) =>
        prev ? prev.filter((d) => d.garmin_activity_id !== dup.garmin_activity_id) : prev
      )
    } catch (err) {
      setReplaceErrors((prev) => ({
        ...prev,
        [dup.garmin_activity_id]:
          err instanceof Error ? err.message : 'Replace failed',
      }))
    } finally {
      setReplacingIds((prev) => {
        const next = new Set(prev)
        next.delete(dup.garmin_activity_id)
        return next
      })
    }
  }

  const replaceOne = async (dup: GarminDuplicateEntry) => {
    // 1. Delete the manual twin via the standard activities API.
    await activitiesApi.delete(dup.existing_activity_id)
    // 2. Import exactly that garmin id (single-activity endpoint —
    //    deliberately skips the cross-source duplicate check).
    await garminSyncApi.importSingle(dup.garmin_activity_id)
    // 3. Refresh derived queries (the hook's mutation didn't run, so its
    //    invalidation didn't either) + the status badge.
    for (const key of ['activities', 'routes', 'route', 'route-compare', 'calendar', 'multi-trend', 'percentile-bands', 'currentUser']) {
      queryClient.invalidateQueries({ queryKey: [key] })
    }
    queryClient.invalidateQueries({ queryKey: ['garminSyncStatus'] })
  }

  const handleKeep = (dup: GarminDuplicateEntry) => {
    // Deliberate "keep existing" — removes the row from the review queue
    // without touching any data. The manual upload stays; the garmin copy
    // remains skipped (its id is still absent, so a later backfill would
    // re-surface it, which is the correct conservative behavior).
    setReviewQueue((prev) =>
      prev ? prev.filter((d) => d.garmin_activity_id !== dup.garmin_activity_id) : prev
    )
  }

  const [replaceAllBusy, setReplaceAllBusy] = useState(false)
  const [replaceAllError, setReplaceAllError] = useState<string | null>(null)

  const handleReplaceAll = async () => {
    if (!reviewQueue) return
    setReplaceAllBusy(true)
    setReplaceAllError(null)
    const queue = [...reviewQueue]
    const failed: { id: string; error: string }[] = []
    // Sequential (not parallel): each step deletes an activity + imports its
    // replacement; parallel calls would race on the shared DB session cache
    // and hammer Garmin. N is small (dozens at most), so sequential is fine.
    for (const dup of queue) {
      setReplacingIds((prev) => new Set(prev).add(dup.garmin_activity_id))
      try {
        await replaceOne(dup)
        setReviewQueue((prev) =>
          prev ? prev.filter((d) => d.garmin_activity_id !== dup.garmin_activity_id) : prev
        )
      } catch (err) {
        failed.push({
          id: dup.garmin_activity_id,
          error: err instanceof Error ? err.message : 'Replace failed',
        })
        // Stop on first failure: remaining rows keep their twins intact and
        // the user can retry them individually (states stay consistent).
        break
      } finally {
        setReplacingIds((prev) => {
          const next = new Set(prev)
          next.delete(dup.garmin_activity_id)
          return next
        })
      }
    }
    if (failed.length > 0) {
      setReplaceAllError(
        `Stopped at ${failed[0].id}: ${failed[0].error} — remaining duplicates left for individual review.`
      )
    }
    setReplaceAllBusy(false)
  }

  const duplicates: GarminDuplicateEntry[] = reviewQueue ?? []
  const hasDuplicates = duplicates.length > 0

  return (
    <div className="bg-white rounded-lg shadow-sm border p-4 mb-6" data-testid="garmin-sync-card">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-3 flex-wrap">
          <button
            type="button"
            onClick={() => handleSync(false)}
            disabled={isSyncing}
            className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            data-testid="garmin-sync-button"
          >
            {isSyncing ? 'Syncing…' : 'Sync Garmin'}
          </button>
          <button
            type="button"
            onClick={() => setShowBackfill((v) => !v)}
            className="text-sm text-blue-600 hover:text-blue-800 font-medium"
          >
            {showBackfill ? 'Hide backfill' : 'Backfill…'}
          </button>
          {status?.last_sync_at && (
            <span className="text-sm text-gray-500" data-testid="garmin-last-sync">
              Last synced {formatWhen(status.last_sync_at)}
            </span>
          )}
          {status?.key_expired && (
            <span
              className="text-sm font-medium text-red-700 bg-red-100 px-2 py-0.5 rounded"
              data-testid="garmin-key-expired"
            >
              API key expired
            </span>
          )}
          {!status?.key_expired && status?.key_warning && (
            <span
              className="text-sm font-medium text-amber-700 bg-amber-100 px-2 py-0.5 rounded"
              data-testid="garmin-key-warning"
            >
              API key expires in {status.key_days_left} day{status.key_days_left === 1 ? '' : 's'}
            </span>
          )}
          {!status?.key_configured && (
            <span className="text-sm text-gray-500">Garmin API key not configured (.env)</span>
          )}
        </div>
      </div>

      {showBackfill && (
        <div className="mt-3 flex items-center gap-3 flex-wrap border-t pt-3">
          <label className="text-sm text-gray-700" htmlFor="garmin-backfill-limit">
            Limit (optional, for the initial pull):
          </label>
          <input
            id="garmin-backfill-limit"
            type="number"
            min={1}
            value={backfillLimit}
            onChange={(e) => setBackfillLimit(e.target.value)}
            placeholder="all"
            className="border rounded px-2 py-1 text-sm w-24"
          />
          <button
            type="button"
            onClick={() => handleSync(true)}
            disabled={isSyncing}
            className="bg-gray-800 text-white px-3 py-1.5 rounded-lg hover:bg-gray-900 transition-colors text-sm disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSyncing ? 'Backfilling…' : 'Run backfill'}
          </button>
          <p className="text-xs text-gray-500 w-full">
            Full-history pull downloads every original FIT — can take many minutes. Existing
            manual uploads of the same activities are reported as duplicates, never deleted.
          </p>
        </div>
      )}

      {error && (
        <p className="mt-3 text-sm text-red-700 bg-red-50 border border-red-200 rounded px-3 py-2" data-testid="garmin-sync-error">
          {error}
        </p>
      )}

      {report && (
        <div className="mt-3 border-t pt-3" data-testid="garmin-sync-report">
          <div className="flex items-center justify-between">
            <p className="text-sm text-gray-700">
              <span className="font-medium">{report.synced}</span> synced ·{' '}
              <span className="font-medium">{report.skipped}</span> skipped ·{' '}
              <span className="font-medium">{report.failed}</span> failed
              {report.duplicates.length > 0 && (
                <> · <span className="font-medium text-amber-700">{report.duplicates.length}</span> duplicate{report.duplicates.length === 1 ? '' : 's'}</>
              )}
            </p>
            <button
              type="button"
              onClick={clearReport}
              className="text-xs text-gray-400 hover:text-gray-600"
            >
              dismiss
            </button>
          </div>
          {report.failures.length > 0 && (
            <ul className="mt-2 text-xs text-red-700 space-y-1">
              {report.failures.map((f, i) => (
                <li key={i}>
                  {f.garmin_activity_id ?? 'unknown'}: {f.error}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {hasDuplicates && (
        <div className="mt-3 border-t pt-3" data-testid="garmin-duplicate-review">
          <div className="flex items-center justify-between mb-2 flex-wrap gap-2">
            <h3 className="text-sm font-semibold text-gray-900">
              Duplicate review ({duplicates.length} remaining)
            </h3>
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={handleReplaceAll}
                disabled={replaceAllBusy || isSyncing}
                className="text-xs bg-amber-600 text-white px-3 py-1.5 rounded hover:bg-amber-700 disabled:opacity-50 disabled:cursor-not-allowed"
                data-testid="garmin-replace-all"
              >
                {replaceAllBusy ? 'Replacing all…' : `Replace all (${duplicates.length})`}
              </button>
              <button
                type="button"
                onClick={() => setReviewQueue(null)}
                className="text-xs text-gray-400 hover:text-gray-600"
              >
                dismiss review
              </button>
            </div>
          </div>
          {replaceAllError && (
            <p className="mb-2 text-xs text-red-700 bg-red-50 border border-red-200 rounded px-3 py-2">
              {replaceAllError}
            </p>
          )}
          <p className="text-xs text-gray-500 mb-2">
            These Garmin activities look like ones you already uploaded manually. Keep existing
            (default) or replace the manual copy with the Garmin original. Resolving one row
            keeps the rest of the list intact.
          </p>
          <ul className="space-y-2">
            {duplicates.map((dup) => (
              <li
                key={dup.garmin_activity_id}
                className="flex items-center justify-between gap-3 bg-amber-50 border border-amber-200 rounded px-3 py-2 text-sm flex-wrap"
              >
                <div>
                  <span className="font-medium text-gray-900">
                    {dup.garmin_name ?? `Garmin activity ${dup.garmin_activity_id}`}
                  </span>
                  <span className="text-gray-500">
                    {' '}· {formatWhen(dup.garmin_start)}
                    {dup.garmin_distance != null && ` · ${(dup.garmin_distance / 1000).toFixed(2)} km`}
                  </span>
                  <div className="text-xs text-gray-500">
                    matches existing: {dup.existing_name ?? `#${dup.existing_activity_id}`} ({dup.existing_source})
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {replaceErrors[dup.garmin_activity_id] && (
                    <span className="text-xs text-red-700">{replaceErrors[dup.garmin_activity_id]}</span>
                  )}
                  <button
                    type="button"
                    onClick={() => handleKeep(dup)}
                    disabled={replaceAllBusy}
                    className="text-xs text-gray-700 border border-gray-300 px-2.5 py-1 rounded hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
                    data-testid="garmin-keep-existing"
                  >
                    Keep existing
                  </button>
                  <button
                    type="button"
                    onClick={() => handleReplace(dup)}
                    disabled={replacingIds.has(dup.garmin_activity_id) || replaceAllBusy || isSyncing}
                    className="text-xs bg-amber-600 text-white px-2.5 py-1 rounded hover:bg-amber-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {replacingIds.has(dup.garmin_activity_id) ? 'Replacing…' : 'Replace with Garmin'}
                  </button>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

function formatWhen(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  const diffMs = Date.now() - d.getTime()
  const minutes = Math.floor(diffMs / 60_000)
  if (minutes < 1) return 'just now'
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  if (days < 7) return `${days}d ago`
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
}
