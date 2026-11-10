import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'

// Settings drives the unit preference through the real UnitProvider (the same
// wrapping the app mounts it under), so mock the profile query the provider
// reads and the users API Settings calls directly.
vi.mock('../../hooks/useUser', () => ({
  useCurrentUser: vi.fn().mockReturnValue({
    data: { default_distance_unit: 'metric', max_hr: 190 },
    isLoading: false,
  }),
}))

vi.mock('../../api/users', () => ({
  usersApi: {
    getProfile: vi.fn().mockResolvedValue({
      max_hr: 190,
      default_distance_unit: 'metric',
    }),
    updatePreferences: vi.fn().mockResolvedValue({
      message: 'Preferences updated',
      max_hr: 190,
      default_distance_unit: 'imperial',
    }),
  },
}))

vi.mock('../../components/ToastProvider', () => ({
  useToast: () => ({ addToast: vi.fn() }),
}))

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Settings from '../Settings'
import { UnitProvider } from '../../context/units'
import { usersApi } from '../../api/users'

function renderSettings() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <UnitProvider>
        <Settings />
      </UnitProvider>
    </QueryClientProvider>
  )
}

function clickUnitOption(labelText: string) {
  // The radio input is sr-only; clicking the visible label text toggles it
  const label = screen.getByText(labelText).closest('label')
  if (!label) throw new Error(`No label found for ${labelText}`)
  fireEvent.click(label)
}

describe('Settings unit preference', () => {
  it('renders both unit options with hints', async () => {
    renderSettings()
    // Profile load resolves async — wait for the settings body to appear
    await screen.findByText('Units')
    expect(screen.getByText('Metric')).toBeInTheDocument()
    expect(screen.getByText('Imperial')).toBeInTheDocument()
    expect(screen.getByText('km, min/km, m')).toBeInTheDocument()
    expect(screen.getByText('mi, min/mi, ft')).toBeInTheDocument()
  })

  it('selecting imperial sends default_distance_unit=imperial in the PATCH', async () => {
    renderSettings()
    await screen.findByText('Units')

    clickUnitOption('Imperial')
    fireEvent.click(screen.getByText('Save Settings'))

    await vi.waitFor(() => {
      expect(usersApi.updatePreferences).toHaveBeenCalledWith(
        expect.objectContaining({ default_distance_unit: 'imperial' })
      )
    })
  })

  it('metric selection persists as metric', async () => {
    renderSettings()
    await screen.findByText('Units')

    clickUnitOption('Metric')
    fireEvent.click(screen.getByText('Save Settings'))

    await vi.waitFor(() => {
      expect(usersApi.updatePreferences).toHaveBeenCalledWith(
        expect.objectContaining({ default_distance_unit: 'metric' })
      )
    })
  })
})
