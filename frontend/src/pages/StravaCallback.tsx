import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useStrava } from '../hooks/useStrava'

export default function StravaCallback() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const { completeStravaAuth } = useStrava()
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const code = searchParams.get('code')
    const errorParam = searchParams.get('error')

    if (errorParam) {
      setError('Authorization denied')
      setTimeout(() => navigate('/'), 3000)
      return
    }

    if (!code) {
      setError('No authorization code received')
      setTimeout(() => navigate('/'), 3000)
      return
    }

    completeStravaAuth(code)
      .then(() => {
        setTimeout(() => navigate('/'), 2000)
      })
      .catch(() => {
        setError('Failed to complete authentication')
        setTimeout(() => navigate('/'), 3000)
      })
  }, [searchParams, navigate, completeStravaAuth])

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="text-red-600 text-xl mb-2">❌ {error}</div>
          <p className="text-gray-600">Redirecting...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-500 mx-auto mb-4"></div>
        <p className="text-gray-600">Connecting to Strava...</p>
      </div>
    </div>
  )
}
