import { useState } from 'react'
import { getStravaConnectUrl, handleStravaCallback, syncStravaActivities } from '../api/strava'
import { useToast } from '../components/ToastProvider'

export function useStrava() {
  const [connecting, setConnecting] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const { addToast } = useToast()

  const connectToStrava = async () => {
    try {
      setConnecting(true)
      const { authorization_url } = await getStravaConnectUrl()
      // Redirect to Strava OAuth
      window.location.href = authorization_url
    } catch (error) {
      console.error('Failed to connect to Strava:', error)
      addToast('error', 'Failed to initiate Strava connection')
      setConnecting(false)
    }
  }

  const completeStravaAuth = async (code: string) => {
    try {
      const response = await handleStravaCallback(code)
      // Store the token
      localStorage.setItem('auth_token', response.access_token)
      addToast('success', 'Successfully connected to Strava')
      return response
    } catch (error) {
      console.error('Failed to complete Strava auth:', error)
      addToast('error', 'Failed to complete Strava authentication')
      throw error
    }
  }

  const syncActivities = async () => {
    try {
      setSyncing(true)
      const result = await syncStravaActivities()
      addToast('success', `Synced ${result.synced_count} activities`)
      return result
    } catch (error) {
      console.error('Failed to sync activities:', error)
      addToast('error', 'Failed to sync activities from Strava')
      throw error
    } finally {
      setSyncing(false)
    }
  }

  return {
    connecting,
    syncing,
    connectToStrava,
    completeStravaAuth,
    syncActivities
  }
}
