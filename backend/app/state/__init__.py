"""
app/state/
──────────
LangGraph state schemas.
Each agent graph has a typed State dataclass / TypedDict that defines
what information flows between nodes in the graph.

Example:
  state/retry_state.py  — MandateRetryState with fields like
                           mandate_id, attempt_count, last_error, etc.
"""
