import { api } from './api'

export interface SeedSummary {
  mandates_created: number
  payment_attempts_created: number
  retry_schedules_created: number
  decisions_created: number
  communications_created: number
  escalations_created: number
}

export interface SeedDeleteSummary {
  mandates_deleted: number
}

/**
 * POST /api/v1/dev/seed — development-only endpoint (see
 * backend/app/api/routes/dev_seed.py). Only mounted when the backend's
 * APP_ENV is "development"; returns 404 in any other environment.
 */
export async function seedDemoData(count = 150): Promise<SeedSummary> {
  const { data } = await api.post<SeedSummary>('/dev/seed', { count })
  return data
}

/** DELETE /api/v1/dev/seed — removes only the demo data this tool created. */
export async function deleteDemoData(): Promise<SeedDeleteSummary> {
  const { data } = await api.delete<SeedDeleteSummary>('/dev/seed')
  return data
}
