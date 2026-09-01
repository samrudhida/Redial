import { useCallback, useEffect, useState } from 'react'

export interface AppSettings {
  tablePageSize: number
  /**
   * Seconds between automatic refetches, applied app-wide as the QueryClient's
   * default refetchInterval (see App.tsx) — every page/chart/table polls at
   * this interval unless a hook explicitly overrides it. 0 disables polling.
   */
  dashboardRefreshIntervalSeconds: number
}

const STORAGE_KEY = 'redial-settings'

const DEFAULT_SETTINGS: AppSettings = {
  tablePageSize: 25,
  // Live operations app — auto-refresh by default so retry/collection
  // activity from the background scheduler shows up without a manual reload.
  dashboardRefreshIntervalSeconds: 30,
}

export function readStoredSettings(): AppSettings {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return DEFAULT_SETTINGS
    const parsed = JSON.parse(raw) as Partial<AppSettings>
    return { ...DEFAULT_SETTINGS, ...parsed }
  } catch {
    return DEFAULT_SETTINGS
  }
}

/**
 * Frontend-only workspace preferences, persisted to localStorage. These are
 * NOT backend settings — there is no settings endpoint, so nothing here is
 * ever sent to or read from the API.
 */
export function useSettings() {
  const [settings, setSettings] = useState<AppSettings>(readStoredSettings)

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(settings))
    } catch {
      // Storage can be unavailable (private browsing, quota) — settings just won't persist.
    }
  }, [settings])

  const updateSettings = useCallback((patch: Partial<AppSettings>) => {
    setSettings(previous => ({ ...previous, ...patch }))
  }, [])

  return { settings, updateSettings }
}

export { DEFAULT_SETTINGS }
