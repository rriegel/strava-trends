import { useStrava } from '../hooks/useStrava'
import { useAuth } from '../hooks/useAuth'

export default function SyncButton() {
  const { syncing, syncActivities } = useStrava()
  const { user } = useAuth()

  // Don't show sync button if not connected to Strava
  if (!user?.strava_athlete_id) {
    return null
  }

  const handleSync = async () => {
    try {
      await syncActivities()
      // Reload page to show new activities
      window.location.reload()
    } catch (error) {
      // Error already handled by hook
    }
  }

  return (
    <button
      onClick={handleSync}
      disabled={syncing}
      className="flex items-center gap-2 px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
    >
      <svg
        className={`w-5 h-5 ${syncing ? 'animate-spin' : ''}`}
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
        />
      </svg>
      <span>{syncing ? 'Syncing...' : 'Sync Activities'}</span>
    </button>
  )
}
