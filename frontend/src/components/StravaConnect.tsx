import { useStrava } from '../hooks/useStrava'
import { useAuth } from '../hooks/useAuth'

export default function StravaConnect() {
  const { connectToStrava, connecting } = useStrava()
  const { user } = useAuth()

  // If user is already connected to Strava, show connected state
  if (user?.strava_athlete_id) {
    return (
      <div className="flex items-center gap-2 text-sm text-green-600">
        <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
          <path d="M15.387 17.944l-2.089-4.116h-3.065L15.387 24l5.15-10.172h-3.062m-7.008-5.599l2.836 5.598h4.172L10.463 0l-7 13.828h4.169"/>
        </svg>
        <span>Connected to Strava</span>
      </div>
    )
  }

  return (
    <button
      onClick={connectToStrava}
      disabled={connecting}
      className="flex items-center gap-2 px-4 py-2 bg-orange-500 hover:bg-orange-600 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
    >
      <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
        <path d="M15.387 17.944l-2.089-4.116h-3.065L15.387 24l5.15-10.172h-3.062m-7.008-5.599l2.836 5.598h4.172L10.463 0l-7 13.828h4.169"/>
      </svg>
      <span>{connecting ? 'Connecting...' : 'Connect to Strava'}</span>
    </button>
  )
}
