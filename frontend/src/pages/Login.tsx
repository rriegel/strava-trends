import { useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { login as apiLogin, register as apiRegister } from '../api/auth'
import { setTokens } from '../api/client'

/** FastAPI 422s carry a validation array; other errors carry a string detail. */
function extractErrorMessage(err: any, fallback: string): string {
  const detail = err?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0]
    const field = Array.isArray(first.loc) ? first.loc[first.loc.length - 1] : 'input'
    if (first.type === 'string_too_short') {
      return `Password must be at least 8 characters (you entered ${first.input?.length ?? 0}).`
    }
    return `${field}: ${first.msg}`.replace(/^body: /, '')
  }
  return fallback
}

export default function Login() {
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()

  const redirect = searchParams.get('redirect') || '/'

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    // Client-side validation mirrors the backend contract (backend enforces
    // again — this is for instant feedback, not security).
    if (mode === 'register' && password.length < 8) {
      setError(`Password must be at least 8 characters (you entered ${password.length}).`)
      return
    }

    setSubmitting(true)
    try {
      const response =
        mode === 'login'
          ? await apiLogin(email, password)
          : await apiRegister(email, password)
      setTokens(response.access_token, response.refresh_token)
      navigate(redirect, { replace: true })
    } catch (err: any) {
      const fallback =
        mode === 'register'
          ? 'Registration failed. Please try again.'
          : 'Invalid email or password.'
      setError(extractErrorMessage(err, fallback))
    } finally {
      setSubmitting(false)
    }
  }

  const toggleMode = () => {
    setMode(mode === 'login' ? 'register' : 'login')
    setError(null)
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="bg-white rounded-lg shadow-sm border p-8 max-w-md w-full">
        <h1 className="text-3xl font-bold text-strava-orange mb-2 text-center">Strava Trends</h1>
        <p className="text-gray-600 mb-8 text-center">
          Track your running performance over time
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
              Email
            </label>
            <input
              id="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              placeholder="you@example.com"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-strava-orange focus:border-transparent"
            />
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
              Password
            </label>
            <input
              id="password"
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete={mode === 'register' ? 'new-password' : 'current-password'}
              placeholder={mode === 'register' ? 'At least 8 characters' : 'Your password'}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-strava-orange focus:border-transparent"
            />
            {mode === 'register' && password.length > 0 && password.length < 8 && (
              <p className="mt-1 text-sm text-amber-600">
                {8 - password.length} more character{8 - password.length === 1 ? '' : 's'} needed
              </p>
            )}
          </div>

          {error && (
            <div className="text-red-600 text-sm bg-red-50 border border-red-200 rounded-md px-3 py-2">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={submitting}
            className="w-full px-4 py-2 bg-strava-orange text-white rounded-md hover:bg-orange-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {submitting ? 'Signing in...' : mode === 'login' ? 'Sign In' : 'Create Account'}
          </button>
        </form>

        <p className="mt-4 text-sm text-center text-gray-600">
          {mode === 'login' ? "Don't have an account? " : 'Already have an account? '}
          <button
            type="button"
            onClick={toggleMode}
            className="text-strava-orange hover:underline font-medium"
          >
            {mode === 'login' ? 'Create one' : 'Sign in'}
          </button>
        </p>
      </div>
    </div>
  )
}
