export default function Login() {
  const handleStravaLogin = () => {
    // Redirect to Strava OAuth
    const clientId = import.meta.env.VITE_STRAVA_CLIENT_ID
    const redirectUri = import.meta.env.VITE_STRAVA_REDIRECT_URI
    const scope = 'read,activity:read_all,profile:read_all'
    
    window.location.href = `https://www.strava.com/oauth/authorize?client_id=${clientId}&response_type=code&redirect_uri=${redirectUri}&scope=${scope}`
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="bg-white rounded-lg shadow-sm border p-8 max-w-md w-full text-center">
        <h1 className="text-3xl font-bold text-strava-orange mb-2">Strava Trends</h1>
        <p className="text-gray-600 mb-8">Track your running performance over time</p>
        <button
          onClick={handleStravaLogin}
          className="bg-strava-orange text-white px-6 py-3 rounded-lg font-medium hover:bg-orange-600 transition-colors"
        >
          Connect with Strava
        </button>
      </div>
    </div>
  )
}
