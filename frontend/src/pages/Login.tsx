import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { devLogin } from '../api/auth'

export default function Login() {
  const [error, setError] = useState<string | null>(null)
  const navigate = useNavigate()

  useEffect(() => {
    // Auto-login with dev credentials
    const login = async () => {
      try {
        const response = await devLogin()
        localStorage.setItem('auth_token', response.access_token)
        navigate('/')
      } catch (err) {
        console.error('Login failed:', err)
        setError('Failed to log in. Please try again.')
      }
    }
    login()
  }, [navigate])

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="bg-white rounded-lg shadow-sm border p-8 max-w-md w-full text-center">
        <h1 className="text-3xl font-bold text-strava-orange mb-2">Strava Trends</h1>
        <p className="text-gray-600 mb-8">Track your running performance over time</p>
        {error ? (
          <div className="text-red-600">{error}</div>
        ) : (
          <div className="text-gray-500">Logging in...</div>
        )}
      </div>
    </div>
  )
}
