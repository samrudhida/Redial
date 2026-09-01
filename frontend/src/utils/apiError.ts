import { isAxiosError } from 'axios'

interface PydanticValidationIssue {
  msg?: string
}

/**
 * Extracts a human-readable message from an API error, matching the two
 * error envelope shapes the backend actually returns (see
 * backend/app/api/exception_handlers.py):
 *   - {"error": "...", "detail": "some string"}
 *   - {"error": "validation_error", "detail": [{msg: "...", ...}, ...]}
 */
export function extractErrorMessage(error: unknown, fallback = 'Something went wrong.'): string {
  if (isAxiosError(error)) {
    const detail = (error.response?.data as { detail?: unknown } | undefined)?.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0] as PydanticValidationIssue
      if (typeof first.msg === 'string') return first.msg
    }
    return error.message || fallback
  }
  return error instanceof Error ? error.message : fallback
}
