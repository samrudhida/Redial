# Frontend UX polish + client-side System Health dashboard

Status: approved for planning
Scope: `frontend/` only — no backend files are touched, no API contracts change.

## 1. Context and corrected premises

The originating brief described the app as having low-contrast tables, a
plain AI Decisions table, and an Observability page that "only says no
backend endpoint exists." Direct inspection of the repo shows the app is
further along than that description:

- The app already has a consistent design system (`SectionCard`, `DataTable`,
  `StatusBadge`, `FilterBar`, `Pagination`, `EmptyState`, `.confidence` bars)
  used uniformly across all list pages.
- The Observability page (`src/pages/ObservabilityPage.tsx`) is already
  wired to five real backend endpoints (`/observability/overview`,
  `/workflows`, `/workflows/{id}`, `/provider`, `/errors`, `/metrics`) and
  renders real charts, tables, and a node-timeline modal. There is no stub
  text anywhere in the codebase (verified by grep for "No backend endpoint",
  "coming soon", "not implemented", etc. — the only near-matches are
  legitimate, already-honest `EmptyState` messages such as "Time-series data
  not yet available").
- Backend inspection (`backend/app/observability/`, `backend/app/workflow/`,
  `WorkflowExecutionService`) found two fields that *are* real-looking
  numbers in the API response but are actually dead placeholders:
  `average_ai_latency_ms` (in `/observability/overview`) and `ai_latency_ms`
  (in `/observability/metrics`) are hardcoded to `0.0` in
  `workflow_execution_service.py`, with the backend's own comment stating AI
  trace latency is never attached to `WorkflowState`. `ProviderHealth.average_latency_ms`
  and `.failures` are likewise hardcoded (`0.0` / `0`). The backend does
  collect AI call latency (`app/observability/metrics.py: record_latency`,
  called from `app/llm/ai_service.py`) and per-call traces
  (`app/observability/ai_trace.py: AITraceRecorder`), but neither is ever
  read back out or exposed through any endpoint — this is a genuine backend
  gap, out of scope to fix (frontend-only constraint), but the frontend must
  not present the resulting `0.0` as a real measurement.
- `GET /health` exists, mounted at the app root (not under `/api/v1`), and
  is not currently called by the frontend anywhere.
- `/communications` and `/decisions` are plain offset/limit lists with no
  total-count field or header anywhere in the response — there is no way to
  learn a true total without fetching every page.

These findings replace the original "Part 5/6" framing. The revised plan:
keep the existing real backend-observability sections untouched, add a new,
clearly-separate client-side "System Health" panel for the metrics that
genuinely only exist client-side, and fix the two places where the
existing page currently presents dead backend placeholders as if they were
real measurements.

## 2. Goals

1. Fix contrast/readability across tables, badges, borders, hovers,
   disabled states, placeholders, pagination, and filters, in **both**
   light and dark themes. Pure token-level CSS changes; no layout changes.
2. Polish AI Decisions, Communications, and Escalations pages: confidence
   tiers with color coding, decision-type badges, channel icons, wrapping
   reasoning/message text with hover tooltips for truncated content,
   friendlier timestamps.
3. Add a "System Health" tab to the Observability page covering the metrics
   that have no backend equivalent (request timing, React Query cache
   state, session activity feed, dev info) plus a "Workflow Overview" panel
   built from data the app already fetches.
4. Correct the two dead-placeholder fields (`average_ai_latency_ms==0`,
   `ai_latency_ms==0`, `ProviderHealth.average_latency_ms==0`,
   `ProviderHealth.failures==0`) so the UI shows an honest "Not tracked"
   state instead of a fabricated-looking zero.
5. Ship with a clean `npm run build`, `npx tsc -b --noEmit`, and
   `npx eslint src`.

## 3. Non-goals

- No backend changes, no new/changed API endpoints or contracts.
- No new routes/pages — "System Health" is a second tab on the existing
  `/observability` route.
- No redesign of layout, spacing rhythm, or navigation.
- No fabricated data anywhere: every number traces to either a real backend
  field or a real client-observed measurement (HTTP timing, React Query
  cache state, `window`/`navigator`/`import.meta.env`).
- No attempt to compute true totals for communications or decisions (no
  backend support — see §1).

## 4. Part 1/3/4 — Contrast and per-page polish

Pure CSS token pass over `frontend/src/styles/global.css`, both `:root` and
`[data-theme='dark']` blocks. No new class names for existing elements;
same markup, stronger color values. Concretely: `.cell-muted` / `td small`,
placeholder colors, `.pagination-range`, badge tone backgrounds/foregrounds,
border colors (`#e3eaf3` / `#26364d` family), row-hover backgrounds
(dark-mode hover is currently a near-invisible `#16233690`), and new
disabled-state rules for buttons/inputs/selects (none exist today).

Page-level additions, all reusing existing primitives:

- **AI Decisions** (`AiDecisionsPage.tsx`, `statusPresentation.ts`): add
  `confidenceTone(score)` → success/info/warning/danger at the 95/80/60
  thresholds, applied as a modifier on the existing `.confidence` bar. Add
  `decisionTypePresentation(type)` and render decision type as a
  `StatusBadge` instead of plain `<strong>`. Reasoning cell wraps
  (`white-space: normal`, clamped) instead of hard-truncating, with a
  `title` attribute carrying the full text for hover.
- **Communications** (`CommunicationsPage.tsx`): channel icons
  (`Mail`/`MessageSquare`/`Phone`/`Bell` from `lucide-react`, already a
  dependency) next to the channel label. Message cell wraps with a `title`
  tooltip. Delivery-status badge colors already exist via
  `deliveryStatusPresentation` — just benefits from the Part 1 contrast
  pass.
- **Escalations** (`EscalationsPage.tsx`): level and resolved/open badges
  already exist (`escalationLevelPresentation`); apply the Part 1 contrast
  pass and tighten row spacing to match the other data tables.
- Every truncated ID cell across all tables gets a `title` attribute (native
  tooltip) if it doesn't already carry the full value some other way.

## 5. Part 5 — System Health tab

### 5.1 Data provenance (what's reused vs. newly computed)

| Metric | Source | New request? |
|---|---|---|
| Backend reachable | `GET /health` (real endpoint, not currently called) | Yes — 1 new lightweight polling query, through the shared `api` instance |
| API latency (avg/fastest/slowest, success/fail counts, success rate) | Client-observed HTTP timing via an axios interceptor on the shared `api` instance | No — piggybacks on every request the app already makes |
| Per-API-group status (Dashboard/Mandates/Payments/Retry/Communications/Decisions/Escalations) | React Query's own cache (`queryCache.subscribe`), grouped by existing query-key prefixes | No |
| React Query cache stats (cached/active/stale/fetching/last refresh) | React Query's own cache | No |
| Total mandates, pending retries, payment attempts, open escalations | `useDashboardSummary()` — already the Dashboard page's data source | No new *shape*, but this hook is invoked on this page if not already cached — justified since it's the authoritative aggregate source, not a duplicate |
| AI decisions (total) | `total_ai_calls` from `useObservabilityOverview()` — already called by tab 1 of this same page | No |
| Communications | Opportunistic read from whatever's already in the React Query cache for the communications list query (if the user has visited Communications this session); otherwise shown as unavailable | No — never fetched solely for this |
| Live activity feed | Derived from the same request-timing interceptor stream (every completed request becomes a feed entry), capped at 30, newest first | No |
| Performance cards | Same request-timing stream, aggregated | No |
| Dev section (APP_ENV, API base URL, React version, Vite mode, browser, window size) | `import.meta.env`, `React.version`, `navigator.userAgent`, `window.innerWidth/Height` — rendered only when `import.meta.env.DEV` | No |
| Manual refresh | `queryClient.refetchQueries()` | Re-runs existing queries; not a new query type |

### 5.2 New files

- `src/observability/requestMetrics.ts` — module-level ring buffer (cap
  200) + subscribe/notify, populated by request/response interceptors added
  to the existing shared `api` instance (`src/services/api.ts`). Each entry:
  `{ id, apiGroup, method, path, status: 'success' | 'error', durationMs, timestamp }`.
  `apiGroup` derived from the URL path prefix, mapped to the seven named
  groups. This is the single place HTTP timing is measured — every existing
  hook/page gets it for free, no per-hook changes.
- `src/hooks/useRequestMetrics.ts` — `useSyncExternalStore` over the ring
  buffer; exposes the raw feed (newest-first, capped 30) and derived
  aggregates (avg/min/max latency, success count, fail count, success
  rate). Powers both the Performance Cards and the Activity Feed.
- `src/hooks/useQueryHealth.ts` — `useSyncExternalStore` over
  `queryClient.getQueryCache().subscribe`; computes cache-wide counts
  (cached/active/stale/fetching) and per-group health
  (Healthy/Error/Loading) from each group's queries' `status`/`fetchStatus`.
- `src/hooks/useHealthCheck.ts` — thin `useQuery` wrapping a new
  `fetchHealth()` in `src/services/healthApi.ts`, which calls the real
  `GET /health` (root-mounted — computed via `api.defaults.baseURL` with the
  `/api/v1` suffix stripped, through the same `api` instance so it's still
  timed by the interceptor).
- `src/pages/observability/SystemHealthPanel.tsx` — the tab's root
  component, composed of small subcomponents in the same directory:
  `ApiStatusGrid.tsx`, `ActivityFeed.tsx`, `WorkflowOverview.tsx`,
  `DevInfoPanel.tsx`. Each is a focused, independently readable unit
  consuming one or two of the hooks above — no component calls axios
  directly.

### 5.3 Modified files

- `src/services/api.ts` — add the request/response interceptor pair
  (delegates to `requestMetrics.ts`).
- `src/pages/ObservabilityPage.tsx` — add a tab switcher ("Workflow
  Insights" / "System Health"); existing five sections move under the first
  tab unchanged; `SystemHealthPanel` renders under the second.
- `src/utils/statusPresentation.ts` — add `confidenceTone`,
  `decisionTypePresentation`; no changes to existing exports.
- `src/styles/global.css` — Part 1 contrast tokens, plus new rules for the
  tab switcher, activity feed list, dev-info grid, and API-status grid
  (visually consistent with existing `.provider-grid` / `.metric-grid`
  patterns — no new visual language).

### 5.4 Honest-zero fix (Part 6)

In `ObservabilityPage.tsx`'s existing "Overview" tile grid, latency bar
chart, and provider cards: where the value being rendered is
`average_ai_latency_ms`, `ai_latency_ms`, `ProviderHealth.average_latency_ms`,
or `ProviderHealth.failures`, render a "Not tracked" badge with an
explanatory tooltip ("the backend does not currently attach AI-call latency
to workflow executions") instead of the numeric `0`/`0.0`/`0 ms`. This is
the only change to the existing five sections — everything else in them
(workflow tracing, node timings, status, confidence, requests-today) is real
and stays as-is.

## 6. Assumptions

- `GET /health` is reachable at `${baseURL without /api/v1}/health` in every
  environment this runs in (matches `main.py`/`router.py` mounting, which
  has no prefix on the health router).
- "Backend reachable" is defined as: the `/health` request succeeds
  (2xx) within its request timeout. A failed or timed-out request means
  "No."
  <!-- ambiguity resolved: pick this over "any successful request in the
       last N seconds," since it's the most direct, doesn't depend on other
       traffic, and doesn't require assuming a poll interval the user never
       specified -->
- Communications' "session-loaded count" in Workflow Overview is explicitly
  labeled as such (not "total") to avoid implying it's an aggregate.
- Per-API-group "Healthy/Error/Loading" reflects the *most recent* query in
  that group; a group with no queries yet (nothing fetched this session) is
  shown as a distinct neutral "Not yet queried" state, not lumped in with
  either Healthy or Error.
- The request-metrics ring buffer and activity feed are in-memory only
  (reset on page reload) — no persistence requirement was stated.
- Dev section visibility uses `import.meta.env.DEV`, Vite's standard flag,
  which is `true` for `vite dev` and `false` for `vite build` — matching
  "only visible in development" without needing a new env var.
- No polling interval was specified for the health check or the API-status
  grid; both are computed from whatever's already in the React Query cache
  (i.e., react to existing fetches) except the dedicated health check, which
  polls on a short interval (30s) purely to keep "Backend reachable"
  current while the tab is open — this is the one deliberately-recurring
  request in the whole feature, and it's cheap (no body).

## 7. Verification plan

After implementation, run and report actual output (not assumed success):

```
npm run build
npx tsc -b --noEmit
npx eslint src
```

Then use the `run` skill to start the dev server and manually exercise:
Part 1 contrast in both themes, AI Decisions confidence/badge rendering,
Communications channel icons, Escalations badges, the System Health tab's
seven sections including a manual refresh, and the two honest-zero fixes on
the Workflow Insights tab. Report actual findings, not assumed success.

## 8. Deliverables to report back

1. Files created
2. Files modified
3. Features added
4. Performance-relevant notes (interceptor overhead, ring-buffer cap)
5. Screens/pages improved
6. Assumptions (§6 above, restated for visibility)
