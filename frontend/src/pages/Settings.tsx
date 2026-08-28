import { useState, useEffect } from 'react'
import { usersApi } from '../api/users'
import { useToast } from '../components/ToastProvider'

export default function Settings() {
  const [maxHr, setMaxHr] = useState<string>('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const { addToast } = useToast()

  useEffect(() => {
    loadProfile()
  }, [])

  const loadProfile = async () => {
    try {
      const data = await usersApi.getProfile()
      setMaxHr(data.max_hr?.toString() || '')
    } catch (error) {
      console.error('Failed to load profile:', error)
      addToast('error', 'Failed to load profile')
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      const maxHrValue = maxHr ? parseInt(maxHr) : null
      
      if (maxHrValue !== null && (maxHrValue < 30 || maxHrValue > 250)) {
        addToast('error', 'Max HR must be between 30 and 250 bpm')
        setSaving(false)
        return
      }

      await usersApi.updatePreferences({ max_hr: maxHrValue })
      addToast('success', 'Settings saved successfully')
    } catch (error: any) {
      console.error('Failed to save settings:', error)
      const message = error.response?.data?.detail || 'Failed to save settings'
      addToast('error', message)
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading...</div>
      </div>
    )
  }

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">Settings</h1>

      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-4">Heart Rate Zones</h2>
        
        <div className="mb-4">
          <label htmlFor="max-hr" className="block text-sm font-medium text-gray-700 mb-2">
            Maximum Heart Rate (bpm)
          </label>
          <input
            id="max-hr"
            type="number"
            min="30"
            max="250"
            value={maxHr}
            onChange={(e) => setMaxHr(e.target.value)}
            placeholder="e.g., 190"
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-strava-orange focus:border-transparent"
          />
          <p className="mt-1 text-sm text-gray-500">
            Leave empty to use the maximum heart rate detected from your activities.
          </p>
        </div>

        <div className="mt-6">
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-4 py-2 bg-strava-orange text-white rounded-md hover:bg-orange-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {saving ? 'Saving...' : 'Save Settings'}
          </button>
        </div>
      </div>
    </div>
  )
}
