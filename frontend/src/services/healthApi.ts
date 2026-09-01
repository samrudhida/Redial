import axios from 'axios'

/** Mirrors the response of GET /health (see backend/app/api/routes/health.py) — note: no /api/v1 prefix. */
export interface HealthStatus {
  status: string
  version: string
  environment: string
  razorpay_configured: boolean
  /** The public half of the Razorpay key pair — safe to use client-side to initialise Checkout.js. */
  razorpay_key_id: string | null
}

/**
 * GET /health — mounted at the API root, not under /api/v1 like every other
 * route, so this uses its own axios call rather than the shared `api` client.
 */
export async function fetchHealth(): Promise<HealthStatus> {
  const baseURL = (import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1').replace(/\/api\/v1\/?$/, '')
  const { data } = await axios.get<HealthStatus>(`${baseURL}/health`)
  return data
}
