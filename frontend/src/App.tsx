import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useEffect } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { Toaster } from 'sonner'
import { ThemeProvider } from './context/ThemeContext'
import { UserProvider } from './context/UserContext'
import { readStoredSettings, useSettings } from './hooks/useSettings'
import { AppShell } from './layout/AppShell'
import { AiDecisionsPage } from './pages/AiDecisionsPage'
import { AnalyticsPage } from './pages/AnalyticsPage'
import { CommunicationsPage } from './pages/CommunicationsPage'
import { DashboardPage } from './pages/DashboardPage'
import { EscalationsPage } from './pages/EscalationsPage'
import { LandingPage } from './pages/LandingPage'
import { LoginPage } from './pages/LoginPage'
import { MandatesPage } from './pages/MandatesPage'
import { ObservabilityPage } from './pages/ObservabilityPage'
import { PaymentsPage } from './pages/PaymentsPage'
import { RetryQueuePage } from './pages/RetryQueuePage'
import { SettingsPage } from './pages/SettingsPage'
import { SignupPage } from './pages/SignupPage'

// App-wide live-data default: every page's queries poll at the user's
// configured interval (Settings > Live data refresh) unless a hook
// explicitly overrides it — this is what makes every table/chart/KPI across
// the whole app (not just the Dashboard) reflect the background scheduler's
// activity without a manual reload.
const initialRefreshSeconds = readStoredSettings().dashboardRefreshIntervalSeconds
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchInterval: initialRefreshSeconds > 0 ? initialRefreshSeconds * 1000 : false,
    },
  },
})

/**
 * Keeps the QueryClient's global refetchInterval in sync with the Settings
 * page's "Live data refresh" control — without this, changing the interval
 * would only take effect on pages after a full reload, since QueryClient
 * defaultOptions are otherwise fixed at construction time.
 */
function QueryDefaultsSync() {
  const { settings } = useSettings()

  useEffect(() => {
    queryClient.setDefaultOptions({
      queries: {
        ...queryClient.getDefaultOptions().queries,
        refetchInterval: settings.dashboardRefreshIntervalSeconds > 0 ? settings.dashboardRefreshIntervalSeconds * 1000 : false,
      },
    })
  }, [settings.dashboardRefreshIntervalSeconds])

  return null
}

/** Everything that lives inside the existing dashboard chrome — unchanged from before this task. */
function DashboardApp() {
  return <AppShell>
    <Routes>
      <Route path="dashboard" element={<DashboardPage />} />
      <Route path="mandates" element={<MandatesPage />} />
      <Route path="retry-queue" element={<RetryQueuePage />} />
      <Route path="ai-decisions" element={<AiDecisionsPage />} />
      <Route path="communications" element={<CommunicationsPage />} />
      <Route path="escalations" element={<EscalationsPage />} />
      <Route path="analytics" element={<AnalyticsPage />} />
      <Route path="observability" element={<ObservabilityPage />} />
      <Route path="settings" element={<SettingsPage />} />
      <Route path="payments" element={<PaymentsPage />} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  </AppShell>
}

function App() {
  return <QueryClientProvider client={queryClient}>
    <QueryDefaultsSync />
    <UserProvider>
      <ThemeProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/signup" element={<SignupPage />} />
            <Route path="/*" element={<DashboardApp />} />
          </Routes>
        </BrowserRouter>
        <Toaster position="bottom-right" richColors />
      </ThemeProvider>
    </UserProvider>
  </QueryClientProvider>
}

export default App
