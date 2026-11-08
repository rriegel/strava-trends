import { useState, useEffect } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { usersApi } from '../api/users'
import { useToast } from '../components/ToastProvider'
import { useUnits, type UnitSystem } from '../context/units'

/**
 * Query families whose responses carry unit-bearing display values. A unit
 * flip changes how every distance/pace/elevation renders, so all of these
 * must refetch after saving — same discipline as UPLOAD_INVALIDATED_KEYS in
 * useFileUpload.ts (5-min staleTime would otherwise serve stale-unit data).
 */
const UNIT_INVALIDATED_KEYS = [
  'activities',
  'routes',
  'route',
  'route-compare',
  'calendar',
  'multi-trend',
  'percentile-bands',
] as const

export default function Settings() {
  const [maxHr, setMaxHr] = useState<string>('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const { addToast } = useToast()
  const { unit, setUnit } = useUnits()
  const queryClient = useQueryClient()

  useEffect(() => {
    loadProfile()
  }, [])

  const loadProfile = async () => {
    try {
      const data = await usersApi.getProfile()
      setMaxHr(data.max_hr?.toString() || '')
      if (data.default_distance_unit === 'imperial' || data.default_distance_unit === 'metric') {
        setUnit(data.default_distance_unit)
      }
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

      await usersApi.updatePreferences({ max_hr: maxHrValue, default_distance_unit: unit })
      // Optimistic UI switch already happened via the toggle; persisting the
      // same value keeps provider <-> DB in sync on next profile load.
      // Invalidate every unit-bearing query family so no page shows stale
      // units from the 5-min cache window.
      for (const key of UNIT_INVALIDATED_KEYS) {
        queryClient.invalidateQueries({ queryKey: [key] })
      }
      queryClient.invalidateQueries({ queryKey: ['currentUser'] })
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

  const unitOptions: { value: UnitSystem; label: string; hint: string }[] = [
    { value: 'metric', label: 'Metric', hint: 'km, min/km, m' },
    { value: 'imperial', label: 'Imperial', hint: 'mi, min/mi, ft' },
  ]

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">Settings</h1>

      <div className="bg-white rounded-lg shadow p-6 space-y-6">
        <div>
          <h2 className="text-lg font-semibold mb-4">Units</h2>
          <div className="grid grid-cols-2 gap-3 max-w-md">
            {unitOptions.map((option) => (
              <label
                key={option.value}
                className={`flex flex-col items-start p-3 border rounded-lg cursor-pointer transition-colors ${
                  unit === option.value
                    ? 'border-strava-orange ring-1 ring-strava-orange bg-orange-50'
                    : 'border-gray-300 hover:border-gray-400'
                }`}
              >
                <input
                  type="radio"
                  name="distance-unit"
                  value={option.value}
                  checked={unit === option.value}
                  onChange={() => setUnit(option.value)}
                  className="sr-only"
                />
                <span className="font-medium text-gray-900">{option.label}</span>
                <span className="text-sm text-gray-500">{option.hint}</span>
              </label>
            ))}
          </div>
          <p className="mt-2 text-sm text-gray-500">
            Applies everywhere after you save: distances, pace, and elevation across all pages.
          </p>
        </div>

        <div className="border-t pt-6">
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
        </div>

        <div>
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
