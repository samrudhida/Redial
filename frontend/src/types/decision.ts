/** Mirrors DecisionLogResponse in backend/app/api/routes/decisions.py. */
export interface DecisionLog {
  id: string
  mandate_id: string
  decision_type: string
  explanation: string
  /** Decimal in range [0, 1], serialized as a string (e.g. "0.9200"). */
  confidence_score: string
  created_at: string
}
