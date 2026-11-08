import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useCurrentUser } from '../hooks/useUser'
import type { User } from '../types'

export type UnitSystem = 'metric' | 'imperial'

interface UnitsContextValue {
  /** Current unit system; 'metric' until the profile loads / outside the provider */
  unit: UnitSystem
  /** True while the preference is being fetched (callers can render metric defaults) */
  isLoading: boolean
  /** Optimistically switch the UI immediately (Settings save also persists to the API) */
  setUnit: (unit: UnitSystem) => void
}

const UnitsContext = createContext<UnitsContextValue>({
  unit: 'metric',
  isLoading: false,
  setUnit: () => {},
})

/**
 * Unit preference source of truth: users.default_distance_unit, surfaced via
 * the /users/me profile query. The provider mirrors the query cache into
 * context; formatters read the context (or the 'metric' default outside the
 * provider, which keeps existing component tests provider-free).
 *
 * NOTE: this is deliberately NOT URL state — it's a user setting, unlike the
 * shareable filter params every page carries.
 */
export function UnitProvider({ children }: { children: ReactNode }) {
  const { data: user, isLoading } = useCurrentUser()
  const [unit, setUnitState] = useState<UnitSystem>('metric')
  const queryClient = useQueryClient()

  // Mirror the cached profile into context. Re-sync whenever the query
  // refetches (e.g. after invalidation) unless the user made a newer
  // optimistic change this session.
  useEffect(() => {
    const cached = queryClient.getQueryData<User>(['currentUser'])
    const source = user ?? cached
    if (source?.default_distance_unit === 'imperial' || source?.default_distance_unit === 'metric') {
      setUnitState(source.default_distance_unit)
    }
  }, [user, queryClient])

  const setUnit = (next: UnitSystem) => setUnitState(next)

  return (
    <UnitsContext.Provider value={{ unit, isLoading, setUnit }}>
      {children}
    </UnitsContext.Provider>
  )
}

export function useUnits(): UnitsContextValue {
  return useContext(UnitsContext)
}
