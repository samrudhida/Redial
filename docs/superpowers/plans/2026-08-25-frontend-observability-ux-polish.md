# Frontend UX Polish + System Health Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Polish contrast/readability across the app, add AI-audit-console styling to AI Decisions/Communications/Escalations, and add a client-side "System Health" tab to the Observability page that reuses real backend data wherever it exists and is honest ("Not tracked") about the two fields the backend only fakes.

**Architecture:** Pure CSS token pass for contrast (no markup changes). Small presentation helpers added to the existing `statusPresentation.ts`/`format.ts` pattern. A single axios interceptor pair on the existing shared `api` instance feeds a module-level ring buffer that every page gets timing/activity data from for free. React Query's own `QueryClient`/`QueryCache` is read directly (via `useSyncExternalStore`) for cache and per-API health — no parallel state is invented for data React Query already tracks.

**Tech Stack:** React 19, TypeScript (strict, `verbatimModuleSyntax`), `@tanstack/react-query` v5, `axios`, `lucide-react`, existing hand-rolled CSS (no CSS-in-JS, no component library).

**Spec:** `docs/superpowers/specs/2026-08-25-frontend-observability-ux-polish-design.md`

## Global Constraints

- **Frontend only.** Never edit anything under `backend/`. No API contract changes.
- **No test framework exists in this project** (no vitest/jest, no `test` script in `package.json`). Do not add one — out of scope. Each task's verification step is `npx tsc -b --noEmit` + `npx eslint src` (both must be clean) instead of a test run; Task 13 runs the full build and a manual browser pass.
- **No unnecessary requests.** Never add a `useQuery`/axios call whose data is already available from a hook already used on the same page, or from the React Query cache directly. The only genuinely new recurring request in this whole plan is the `/health` poll (Task 9) — everything else observes state the app already produces.
- **Never fabricate data.** A value only renders as a number if it traces to a real backend field or a real client-observed measurement (HTTP timing, React Query cache state, `window`/`navigator`/`import.meta.env`). Where the backend hardcodes a placeholder (`average_ai_latency_ms`, `ai_latency_ms`, `ProviderHealth.average_latency_ms`, `ProviderHealth.failures` — all `0`/`0.0` by construction in `workflow_execution_service.py`, not measurement), render "Not tracked" with an explanatory `title` tooltip instead.
- **Keep both themes working.** Every color change touches both `:root` and `[data-theme='dark']` — never fix one theme and leave the other as it was.
- **System Health is a second tab on the existing `/observability` route** — no new route, no sidebar changes.
- **The seven tracked API groups, in this exact order:** Dashboard, Mandates, Payments, Retry, Communications, Decisions, Escalations. Their query-key first segments are `'dashboard'`, `'mandates'`, `'payments'`, `'retry-schedules'`, `'communications'`, `'decisions'`, `'escalations'`; their URL prefixes are `/dashboard`, `/mandates`, `/payments`, `/retry-schedules`, `/communications`, `/decisions`, `/escalations`.
- **No component calls axios directly.** All new HTTP access goes through `src/services/*.ts`, consumed via a hook in `src/hooks/*.ts`, exactly like every existing feature.

---

### Task 1: Global contrast/readability CSS pass

**Files:**
- Modify: `frontend/src/styles/global.css`

**Interfaces:**
- Produces: no new classes for existing markup; all later tasks that add new markup (Tasks 3–5, 10–12) may assume the token-level colors below are already fixed and can reuse existing classes (`.cell-muted`, `.status-badge.tone-*`, `.confidence`, etc.) without re-fixing contrast themselves.

This task is a sequence of exact string replacements in `global.css`. Apply each one; the file uses long single-line rule blocks, so match on the shown fragment exactly.

- [ ] **Step 1: Strengthen card/table border contrast (both themes)**

Replace all occurrences of the light border token with a stronger one:

Old: `#e3eaf3`
New: `#d7e0ec`
(`replace_all: true` — this hex only ever appears as a `border-color`/`border` value for `.kpi-card`, `.dash-panel`, `.metric-tile`, `.provider-card`, `.modal-panel` in the file.)

Replace all occurrences of the dark border token with a stronger one:

Old: `#26364d`
New: `#2f4160`
(`replace_all: true` — only appears as `border-color` for the dark-mode variants of the same cards/tables.)

- [ ] **Step 2: Strengthen muted/secondary text contrast**

Old:
```css
.data-panel td small, .cell-muted { color: #75839c; }
```
New:
```css
.data-panel td small, .cell-muted { color: #5c6b83; }
```

Old:
```css
[data-theme='dark'] .data-panel td small, [data-theme='dark'] .cell-muted { color: #8592ab; }
```
New:
```css
[data-theme='dark'] .data-panel td small, [data-theme='dark'] .cell-muted { color: #a7b4c9; }
```

- [ ] **Step 3: Make table headers stand out more in dark mode**

Old:
```css
[data-theme='dark'] .data-panel th, [data-theme='dark'] .decisions-panel th { background: #101a29; color: #9fadc4; }
```
New:
```css
[data-theme='dark'] .data-panel th, [data-theme='dark'] .decisions-panel th { background: #101a29; color: #b7c2d8; }
```

- [ ] **Step 4: Make row hover more obvious in both themes**

Old:
```css
.data-panel tbody tr:hover, .decisions-panel tbody tr:hover { background: #f4f7fc; }
```
New:
```css
.data-panel tbody tr:hover, .decisions-panel tbody tr:hover { background: #e9f0fb; }
```

Old:
```css
[data-theme='dark'] .data-panel tbody tr:hover, [data-theme='dark'] .decisions-panel tbody tr:hover { background: #16233690; }
```
New:
```css
[data-theme='dark'] .data-panel tbody tr:hover, [data-theme='dark'] .decisions-panel tbody tr:hover { background: #1c2d47; }
```

- [ ] **Step 5: Add dark-mode badge colors (currently badges reuse the light pastel colors verbatim in dark mode, which is the single worst contrast/legibility bug in the app)**

Old:
```css
.status-badge.tone-success { background: #e8f8ed; color: #24984b; }
.status-badge.tone-warning { background: #fff3d9; color: #b7790a; }
.status-badge.tone-danger { background: #fde2e2; color: #d13b3b; }
.status-badge.tone-neutral { background: #edf2fa; color: #556278; }
.status-badge.tone-info { background: #eaf1ff; color: #2563eb; }
```
New:
```css
.status-badge.tone-success { background: #e8f8ed; color: #178a44; }
.status-badge.tone-warning { background: #fff3d9; color: #a06600; }
.status-badge.tone-danger { background: #fde2e2; color: #c22f2f; }
.status-badge.tone-neutral { background: #edf2fa; color: #46536b; }
.status-badge.tone-info { background: #eaf1ff; color: #2563eb; }
[data-theme='dark'] .status-badge.tone-success { background: rgba(34,197,94,.16); color: #4ade80; }
[data-theme='dark'] .status-badge.tone-warning { background: rgba(245,158,11,.18); color: #fbbf24; }
[data-theme='dark'] .status-badge.tone-danger { background: rgba(239,68,68,.16); color: #f87171; }
[data-theme='dark'] .status-badge.tone-neutral { background: rgba(148,163,184,.16); color: #c2cbdb; }
[data-theme='dark'] .status-badge.tone-info { background: rgba(37,99,235,.18); color: #8fb4ff; }
```

- [ ] **Step 6: Add confidence-tier tone modifiers to the existing `.confidence` bar (used by Task 3)**

Old:
```css
[data-theme='dark'] .confidence { background: rgba(37,99,235,.18); color: #8fb4ff; }
[data-theme='dark'] .confidence span { background: #8fb4ff; }
```
New:
```css
[data-theme='dark'] .confidence { background: rgba(37,99,235,.18); color: #8fb4ff; }
[data-theme='dark'] .confidence span { background: #8fb4ff; }
.confidence.tone-success { background: #e8f8ed; color: #178a44; }
.confidence.tone-success span { background: #178a44; }
.confidence.tone-warning { background: #fff3d9; color: #a06600; }
.confidence.tone-warning span { background: #a06600; }
.confidence.tone-danger { background: #fde2e2; color: #c22f2f; }
.confidence.tone-danger span { background: #c22f2f; }
[data-theme='dark'] .confidence.tone-success { background: rgba(34,197,94,.16); color: #4ade80; }
[data-theme='dark'] .confidence.tone-success span { background: #4ade80; }
[data-theme='dark'] .confidence.tone-warning { background: rgba(245,158,11,.18); color: #fbbf24; }
[data-theme='dark'] .confidence.tone-warning span { background: #fbbf24; }
[data-theme='dark'] .confidence.tone-danger { background: rgba(239,68,68,.16); color: #f87171; }
[data-theme='dark'] .confidence.tone-danger span { background: #f87171; }
```

- [ ] **Step 7: Fix placeholder contrast (light mode is currently ~2.9:1, fails AA)**

Old (appears once, inside the `.search` rule block on the navbar line):
```css
.search input::placeholder { color: #98a5b6; }
```
New:
```css
.search input::placeholder { color: #7c8aa0; }
```

Old:
```css
.filter-search input::placeholder { color: #98a5b6; }
```
New:
```css
.filter-search input::placeholder { color: #7c8aa0; }
```

- [ ] **Step 8: Fix pagination readability (add a missing dark-mode override, darken the light one)**

Old:
```css
.pagination-range { color: #8c9aab; font-size: 11px; margin-right: auto; }
```
New:
```css
.pagination-range { color: #647089; font-size: 11px; margin-right: auto; }
[data-theme='dark'] .pagination-range { color: #9fabc2; }
```

- [ ] **Step 9: Add disabled-state styling (buttons and inputs currently have none — a disabled Pagination button looks identical to an enabled one)**

Old:
```css
.secondary-button:hover { border-color: #a9bfe4; color: #2563eb; }
```
New:
```css
.secondary-button:hover { border-color: #a9bfe4; color: #2563eb; }
.primary-button:disabled, .secondary-button:disabled { opacity: .5; cursor: not-allowed; box-shadow: none; }
.primary-button:disabled:hover, .secondary-button:disabled:hover { border-color: inherit; color: inherit; }
.form-field input:disabled, .filter-select select:disabled, .settings-field select:disabled { opacity: .6; cursor: not-allowed; }
```

- [ ] **Step 10: Add a small reusable spin animation for loading icons (used by Tasks 10–12)**

Old:
```css
.skeleton-block { display: block; border-radius: 6px; background: linear-gradient(90deg, #edf1f6 25%, #e3e9f1 37%, #edf1f6 63%); background-size: 400% 100%; animation: skeleton-shimmer 1.4s ease infinite; }
```
New:
```css
.skeleton-block { display: block; border-radius: 6px; background: linear-gradient(90deg, #edf1f6 25%, #e3e9f1 37%, #edf1f6 63%); background-size: 400% 100%; animation: skeleton-shimmer 1.4s ease infinite; }
.spin { animation: spin 0.9s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
```

- [ ] **Step 11: Verify**

Run: `cd frontend && npx tsc -b --noEmit && npx eslint src`
Expected: both clean (this task only touches CSS, so this mainly guards against a stray syntax issue elsewhere; the real check is visual, done in Task 13).

- [ ] **Step 12: Commit**

```bash
git add frontend/src/styles/global.css
git commit -m "style: raise contrast for tables, badges, borders, hover, disabled and placeholder states"
```

---

### Task 2: Shared presentation helpers (confidence tone, decision-type badges, channel icons, timestamp tooltip)

**Files:**
- Modify: `frontend/src/utils/statusPresentation.ts`
- Create: `frontend/src/ui/Timestamp.tsx`

**Interfaces:**
- Consumes: `BadgeTone` from `../ui/StatusBadge` (existing).
- Produces: `confidenceTone(score: string): BadgeTone`, `decisionTypePresentation(type: string): { label: string; tone: BadgeTone }`, `communicationChannelIcon(channel: CommunicationChannel): LucideIcon` — all consumed by Tasks 3–4. `Timestamp({ iso: string | null })` component — consumed by Tasks 3–5.

- [ ] **Step 1: Add `confidenceTone` and `decisionTypePresentation` to `statusPresentation.ts`**

The real `decision_type` values recorded by this app are exactly `"retry_schedule"`, `"decline_classification"`, `"escalation_recommendation"` (verified against every call site of `DecisionService.record_ai_decision`, e.g. `backend/app/services/dev_seed_service.py`) — there is no `"communication"` decision type in this codebase, since communications are their own entity, not a decision. `decision_type` is a free-form string column with no backend enum, so the presentation function must have a safe fallback for any other value rather than assuming exhaustiveness.

Append to the end of `frontend/src/utils/statusPresentation.ts`:

```ts
/** 95–100 green, 80–94 blue, 60–79 yellow, below 60 red. */
export function confidenceTone(score: string): BadgeTone {
  const value = Number.parseFloat(score) * 100
  if (!Number.isFinite(value)) return 'neutral'
  if (value >= 95) return 'success'
  if (value >= 80) return 'info'
  if (value >= 60) return 'warning'
  return 'danger'
}

/**
 * decision_type is a free-form string (no backend enum) — the three values
 * actually ever recorded by this app are retry_schedule,
 * decline_classification, and escalation_recommendation (see every call
 * site of DecisionService.record_ai_decision). Anything else falls back to
 * a neutral badge with the raw value title-cased, rather than assuming a
 * fixed set.
 */
export function decisionTypePresentation(type: string): { label: string; tone: BadgeTone } {
  if (type === 'retry_schedule') return { label: 'Retry', tone: 'info' }
  if (type === 'decline_classification') return { label: 'Decline Classification', tone: 'warning' }
  if (type === 'escalation_recommendation') return { label: 'Escalate', tone: 'danger' }
  return { label: titleCase(type), tone: 'neutral' }
}
```

- [ ] **Step 2: Add `communicationChannelIcon` next to the existing `communicationChannelLabel`**

Modify the top of `frontend/src/utils/statusPresentation.ts` — change:

```ts
import type { BadgeTone } from '../ui/StatusBadge'
```

to:

```ts
import { Bell, Mail, MessageCircle, MessageSquare, type LucideIcon } from 'lucide-react'
import type { BadgeTone } from '../ui/StatusBadge'
```

Then replace:

```ts
export function communicationChannelLabel(channel: CommunicationChannel): string {
  return titleCase(channel)
}
```

with:

```ts
export function communicationChannelLabel(channel: CommunicationChannel): string {
  return titleCase(channel)
}

const CHANNEL_ICONS: Record<CommunicationChannel, LucideIcon> = {
  email: Mail,
  sms: MessageSquare,
  whatsapp: MessageCircle,
  push: Bell,
}

export function communicationChannelIcon(channel: CommunicationChannel): LucideIcon {
  return CHANNEL_ICONS[channel]
}
```

- [ ] **Step 3: Create the `Timestamp` component**

Create `frontend/src/ui/Timestamp.tsx`:

```tsx
import { formatDate, formatRelativeTime } from '../utils/format'

/** Renders an absolute timestamp with the relative time as a hover tooltip. */
export function Timestamp({ iso }: { iso: string | null }) {
  if (iso === null) return <span className="cell-muted">—</span>
  return (
    <span className="cell-muted" title={formatRelativeTime(iso)}>
      {formatDate(iso)}
    </span>
  )
}
```

- [ ] **Step 4: Verify**

Run: `cd frontend && npx tsc -b --noEmit && npx eslint src`
Expected: both clean.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/utils/statusPresentation.ts frontend/src/ui/Timestamp.tsx
git commit -m "feat: add confidence-tier, decision-type, channel-icon presentation helpers"
```

---

### Task 3: AI Decisions page — audit-console polish

**Files:**
- Modify: `frontend/src/pages/AiDecisionsPage.tsx`

**Interfaces:**
- Consumes: `confidenceTone`, `decisionTypePresentation` from `../utils/statusPresentation` (Task 2), `Timestamp` from `../ui/Timestamp` (Task 2), `StatusBadge` (existing).

- [ ] **Step 1: Update imports**

Replace:
```tsx
import { useDecisions } from '../hooks/useDecisions'
import { useSettings } from '../hooks/useSettings'
import type { DecisionLog } from '../types/decision'
import { DataTable, type DataTableColumn } from '../ui/DataTable'
import { EmptyState } from '../ui/EmptyState'
import { Modal } from '../ui/Modal'
import { PageHeader } from '../ui/PageHeader'
import { Pagination } from '../ui/Pagination'
import { QueryError } from '../ui/QueryError'
import { SectionCard } from '../ui/SectionCard'
import { Skeleton } from '../ui/Skeleton'
import { formatConfidencePercent, formatDate, truncateId, truncateText } from '../utils/format'
```
with:
```tsx
import { useDecisions } from '../hooks/useDecisions'
import { useSettings } from '../hooks/useSettings'
import type { DecisionLog } from '../types/decision'
import { DataTable, type DataTableColumn } from '../ui/DataTable'
import { EmptyState } from '../ui/EmptyState'
import { Modal } from '../ui/Modal'
import { PageHeader } from '../ui/PageHeader'
import { Pagination } from '../ui/Pagination'
import { QueryError } from '../ui/QueryError'
import { SectionCard } from '../ui/SectionCard'
import { Skeleton } from '../ui/Skeleton'
import { StatusBadge } from '../ui/StatusBadge'
import { Timestamp } from '../ui/Timestamp'
import { formatConfidencePercent, truncateId } from '../utils/format'
import { confidenceTone, decisionTypePresentation } from '../utils/statusPresentation'
```

(`formatDate` and `truncateText` are dropped — replaced by `Timestamp` and the wrapping `.wrap-cell` treatment below.)

- [ ] **Step 2: Add a small confidence-bar helper and use it in both the modal and the table**

Replace the modal's confidence field:
```tsx
            <div className="form-field">
              <label>Confidence</label>
              <p><span className="confidence"><span style={{ width: formatConfidencePercent(decision.confidence_score) }} />{formatConfidencePercent(decision.confidence_score)}</span></p>
            </div>
```
with:
```tsx
            <div className="form-field">
              <label>Confidence</label>
              <p><ConfidenceBar score={decision.confidence_score} /></p>
            </div>
```

Replace the modal's decision-type field:
```tsx
            <div className="form-field">
              <label>AI Decision</label>
              <p>{decision.decision_type.replace(/_/g, ' ')}</p>
            </div>
```
with:
```tsx
            <div className="form-field">
              <label>AI Decision</label>
              <p><StatusBadge {...decisionTypePresentation(decision.decision_type)} /></p>
            </div>
```

Replace the modal's timestamp field:
```tsx
          <div className="form-field">
            <label>Timestamp</label>
            <p>{formatDate(decision.created_at)}</p>
          </div>
```
with:
```tsx
          <div className="form-field">
            <label>Timestamp</label>
            <p><Timestamp iso={decision.created_at} /></p>
          </div>
```

Add the `ConfidenceBar` helper above `DecisionDetailModal`:
```tsx
function ConfidenceBar({ score }: { score: string }) {
  const tone = confidenceTone(score)
  return (
    <span className={`confidence ${tone !== 'info' ? `tone-${tone}` : ''}`}>
      <span style={{ width: formatConfidencePercent(score) }} />
      {formatConfidencePercent(score)}
    </span>
  )
}
```

- [ ] **Step 3: Update the table columns**

Replace the `columns` array body:
```tsx
  const columns: DataTableColumn<DecisionLog>[] = [
    { key: 'mandate_id', header: 'Mandate ID', render: decision => <span className="cell-muted">{truncateId(decision.mandate_id)}</span> },
    { key: 'decision_type', header: 'AI Decision', render: decision => <strong>{decision.decision_type.replace(/_/g, ' ')}</strong> },
    { key: 'confidence_score', header: 'Confidence', render: decision => <span className="confidence"><span style={{ width: formatConfidencePercent(decision.confidence_score) }} />{formatConfidencePercent(decision.confidence_score)}</span> },
    { key: 'explanation', header: 'Reasoning', render: decision => truncateText(decision.explanation, 130) },
    { key: 'created_at', header: 'Timestamp', render: decision => <span className="cell-muted">{formatDate(decision.created_at)}</span> },
```
with:
```tsx
  const columns: DataTableColumn<DecisionLog>[] = [
    { key: 'mandate_id', header: 'Mandate ID', render: decision => <span className="cell-muted" title={decision.mandate_id}>{truncateId(decision.mandate_id)}</span> },
    { key: 'decision_type', header: 'AI Decision', render: decision => <StatusBadge {...decisionTypePresentation(decision.decision_type)} /> },
    { key: 'confidence_score', header: 'Confidence', render: decision => <ConfidenceBar score={decision.confidence_score} /> },
    { key: 'explanation', header: 'Reasoning', render: decision => <span className="wrap-cell" title={decision.explanation}>{decision.explanation}</span> },
    { key: 'created_at', header: 'Timestamp', render: decision => <Timestamp iso={decision.created_at} /> },
```

- [ ] **Step 4: Add the wrapping-cell CSS class**

Modify `frontend/src/styles/global.css` — after the `.cell-muted { font-size: 11px; }` rule, add:
```css
.wrap-cell { display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; white-space: normal; max-width: 380px; line-height: 1.4; }
```

- [ ] **Step 5: Verify**

Run: `cd frontend && npx tsc -b --noEmit && npx eslint src`
Expected: both clean. `noUnusedLocals` will fail the build if `formatDate`/`truncateText` are still imported anywhere in this file but unused — double-check both are gone from the import line.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/AiDecisionsPage.tsx frontend/src/styles/global.css
git commit -m "feat: AI Decisions audit-console polish (confidence tiers, decision badges, wrapping reasoning)"
```

---

### Task 4: Communications page polish

**Files:**
- Modify: `frontend/src/pages/CommunicationsPage.tsx`

**Interfaces:**
- Consumes: `communicationChannelIcon` (Task 2), `Timestamp` (Task 2), `.wrap-cell` (Task 3).

- [ ] **Step 1: Update imports**

Replace:
```tsx
import { formatDate, truncateId, truncateText } from '../utils/format'
import { communicationChannelLabel, deliveryStatusPresentation } from '../utils/statusPresentation'
```
with:
```tsx
import { truncateId } from '../utils/format'
import { communicationChannelIcon, communicationChannelLabel, deliveryStatusPresentation } from '../utils/statusPresentation'
import { Timestamp } from '../ui/Timestamp'
```

- [ ] **Step 2: Update the table columns**

Replace:
```tsx
  const columns: DataTableColumn<Communication>[] = [
    { key: 'mandate_id', header: 'Mandate ID', render: communication => <span className="cell-muted">{truncateId(communication.mandate_id)}</span> },
    { key: 'channel', header: 'Channel', render: communication => <strong>{communicationChannelLabel(communication.channel)}</strong> },
    { key: 'delivery_status', header: 'Delivery Status', render: communication => { const { label, tone } = deliveryStatusPresentation(communication.delivery_status); return <StatusBadge label={label} tone={tone} /> } },
    { key: 'message', header: 'Message', render: communication => truncateText(communication.message, 130) },
    { key: 'sent_at', header: 'Timestamp', render: communication => <span className="cell-muted">{formatDate(communication.sent_at)}</span> },
  ]
```
with:
```tsx
  const columns: DataTableColumn<Communication>[] = [
    { key: 'mandate_id', header: 'Mandate ID', render: communication => <span className="cell-muted" title={communication.mandate_id}>{truncateId(communication.mandate_id)}</span> },
    {
      key: 'channel',
      header: 'Channel',
      render: communication => {
        const Icon = communicationChannelIcon(communication.channel)
        return <span className="channel-cell"><Icon size={14} />{communicationChannelLabel(communication.channel)}</span>
      },
    },
    { key: 'delivery_status', header: 'Delivery Status', render: communication => { const { label, tone } = deliveryStatusPresentation(communication.delivery_status); return <StatusBadge label={label} tone={tone} /> } },
    { key: 'message', header: 'Message', render: communication => <span className="wrap-cell" title={communication.message}>{communication.message}</span> },
    { key: 'sent_at', header: 'Timestamp', render: communication => <Timestamp iso={communication.sent_at} /> },
  ]
```

- [ ] **Step 3: Add the channel-cell CSS class**

Modify `frontend/src/styles/global.css` — after the `.wrap-cell` rule added in Task 3, add:
```css
.channel-cell { display: inline-flex; align-items: center; gap: 6px; font-weight: 700; color: #263349; }
[data-theme='dark'] .channel-cell { color: #eef4fc; }
```

- [ ] **Step 4: Verify**

Run: `cd frontend && npx tsc -b --noEmit && npx eslint src`
Expected: both clean.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/CommunicationsPage.tsx frontend/src/styles/global.css
git commit -m "feat: Communications page polish (channel icons, wrapping message, timestamp tooltip)"
```

---

### Task 5: Escalations page polish

**Files:**
- Modify: `frontend/src/pages/EscalationsPage.tsx`

**Interfaces:**
- Consumes: `Timestamp` (Task 2), `.wrap-cell` (Task 3).

- [ ] **Step 1: Update imports**

Replace:
```tsx
import { formatDate, truncateId, truncateText } from '../utils/format'
import { escalationLevelPresentation } from '../utils/statusPresentation'
```
with:
```tsx
import { truncateId } from '../utils/format'
import { escalationLevelPresentation } from '../utils/statusPresentation'
import { Timestamp } from '../ui/Timestamp'
```

- [ ] **Step 2: Update the table columns**

Replace:
```tsx
  const columns: DataTableColumn<Escalation>[] = [
    { key: 'mandate_id', header: 'Mandate ID', render: escalation => <span className="cell-muted">{truncateId(escalation.mandate_id)}</span> },
    { key: 'escalation_level', header: 'Escalation Level', render: escalation => { const { label, tone } = escalationLevelPresentation(escalation.escalation_level); return <StatusBadge label={label} tone={tone} /> } },
    { key: 'resolved', header: 'Status', render: escalation => <StatusBadge label={escalation.resolved ? 'Resolved' : 'Open'} tone={escalation.resolved ? 'success' : 'warning'} /> },
    { key: 'reason', header: 'Reason', render: escalation => <strong>{truncateText(escalation.reason, 130)}</strong> },
    { key: 'assigned_to', header: 'Assigned To', render: escalation => <span className="cell-muted">{escalation.assigned_to ?? 'Unassigned'}</span> },
    // The backend has no created_at for escalations — resolved_at is the only
    // real timestamp, and it's null until resolved. Do not invent a creation time.
    { key: 'resolved_at', header: 'Resolved At', render: escalation => <span className="cell-muted">{formatDate(escalation.resolved_at)}</span> },
  ]
```
with:
```tsx
  const columns: DataTableColumn<Escalation>[] = [
    { key: 'mandate_id', header: 'Mandate ID', render: escalation => <span className="cell-muted" title={escalation.mandate_id}>{truncateId(escalation.mandate_id)}</span> },
    { key: 'escalation_level', header: 'Escalation Level', render: escalation => { const { label, tone } = escalationLevelPresentation(escalation.escalation_level); return <StatusBadge label={label} tone={tone} /> } },
    { key: 'resolved', header: 'Status', render: escalation => <StatusBadge label={escalation.resolved ? 'Resolved' : 'Open'} tone={escalation.resolved ? 'success' : 'warning'} /> },
    { key: 'reason', header: 'Reason', render: escalation => <span className="wrap-cell" title={escalation.reason}>{escalation.reason}</span> },
    { key: 'assigned_to', header: 'Assigned To', render: escalation => <span className="cell-muted">{escalation.assigned_to ?? 'Unassigned'}</span> },
    // The backend has no created_at for escalations — resolved_at is the only
    // real timestamp, and it's null until resolved. Do not invent a creation time.
    { key: 'resolved_at', header: 'Resolved At', render: escalation => <Timestamp iso={escalation.resolved_at} /> },
  ]
```

- [ ] **Step 3: Verify**

Run: `cd frontend && npx tsc -b --noEmit && npx eslint src`
Expected: both clean.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/EscalationsPage.tsx
git commit -m "style: Escalations page polish (wrapping reason, timestamp tooltip)"
```

---

### Task 6: Request-metrics instrumentation (API grouping + ring buffer + axios interceptors)

**Files:**
- Create: `frontend/src/observability/apiGroups.ts`
- Create: `frontend/src/observability/requestMetrics.ts`
- Modify: `frontend/src/services/api.ts`

**Interfaces:**
- Produces: `API_GROUPS: ApiGroup[]`, `groupLabelForUrl(url): string`, `groupLabelForQueryKey(key): string | null` (from `apiGroups.ts`, consumed by Task 8's `useQueryHealth` and this task's `requestMetrics.ts`). `RequestMetricEntry`, `recordRequestFromUrl(...)`, `subscribeRequestMetrics(listener)`, `getRequestMetricsSnapshot()` (from `requestMetrics.ts`, consumed by Task 7's `useRequestMetrics`).

- [ ] **Step 1: Create the API group table**

Create `frontend/src/observability/apiGroups.ts`:

```ts
export interface ApiGroup {
  label: string
  /** URL path prefix as passed to the shared axios instance, e.g. "/mandates". */
  urlPrefix: string
  /** First segment of this group's React Query keys, e.g. "mandates". */
  queryKeyPrefix: string
}

/** The seven frontend-facing APIs this app calls, in display order. */
export const API_GROUPS: ApiGroup[] = [
  { label: 'Dashboard', urlPrefix: '/dashboard', queryKeyPrefix: 'dashboard' },
  { label: 'Mandates', urlPrefix: '/mandates', queryKeyPrefix: 'mandates' },
  { label: 'Payments', urlPrefix: '/payments', queryKeyPrefix: 'payments' },
  { label: 'Retry', urlPrefix: '/retry-schedules', queryKeyPrefix: 'retry-schedules' },
  { label: 'Communications', urlPrefix: '/communications', queryKeyPrefix: 'communications' },
  { label: 'Decisions', urlPrefix: '/decisions', queryKeyPrefix: 'decisions' },
  { label: 'Escalations', urlPrefix: '/escalations', queryKeyPrefix: 'escalations' },
]

/**
 * Maps a request URL (relative, as passed to the shared axios instance) to
 * its API group label, or 'Other' for anything outside the seven tracked
 * groups (e.g. /observability, /health).
 */
export function groupLabelForUrl(url: string | undefined): string {
  if (!url) return 'Other'
  const path = url.split('?')[0]
  const match = API_GROUPS.find(group => path === group.urlPrefix || path.startsWith(`${group.urlPrefix}/`))
  return match ? match.label : 'Other'
}

/**
 * Maps a React Query key's first segment to its API group label, or null
 * if it isn't one of the seven tracked groups.
 */
export function groupLabelForQueryKey(queryKey: readonly unknown[]): string | null {
  const first = queryKey[0]
  if (typeof first !== 'string') return null
  const match = API_GROUPS.find(group => group.queryKeyPrefix === first)
  return match ? match.label : null
}
```

- [ ] **Step 2: Create the request-metrics ring buffer**

Create `frontend/src/observability/requestMetrics.ts`:

```ts
import { groupLabelForUrl } from './apiGroups'

export interface RequestMetricEntry {
  id: number
  apiGroup: string
  method: string
  path: string
  status: 'success' | 'error'
  durationMs: number
  timestamp: number
}

const MAX_ENTRIES = 200

let entries: RequestMetricEntry[] = []
let nextId = 1
const listeners = new Set<() => void>()

function notify(): void {
  for (const listener of listeners) listener()
}

/** Records one completed request, newest-first, capped at MAX_ENTRIES. */
export function recordRequestFromUrl(params: {
  url: string | undefined
  method: string | undefined
  status: 'success' | 'error'
  durationMs: number
}): void {
  const entry: RequestMetricEntry = {
    id: nextId++,
    apiGroup: groupLabelForUrl(params.url),
    method: (params.method ?? 'GET').toUpperCase(),
    path: params.url ?? 'unknown',
    status: params.status,
    durationMs: params.durationMs,
    timestamp: Date.now(),
  }
  entries = [entry, ...entries].slice(0, MAX_ENTRIES)
  notify()
}

export function subscribeRequestMetrics(listener: () => void): () => void {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

export function getRequestMetricsSnapshot(): RequestMetricEntry[] {
  return entries
}
```

- [ ] **Step 3: Wire request/response interceptors into the shared axios instance**

Read the current `frontend/src/services/api.ts` first — it's a 6-line file. Replace its entire contents with:

```ts
import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios'
import { recordRequestFromUrl } from '../observability/requestMetrics'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1',
  headers: { 'Content-Type': 'application/json' },
})

// Keyed by the request's own config object rather than a module-augmented
// field on it — avoids fighting axios's generic InternalAxiosRequestConfig<D>
// type in a `declare module` augmentation, and entries are garbage-collected
// automatically once each request completes.
const requestStartTimes = new WeakMap<InternalAxiosRequestConfig, number>()

function elapsedMs(config: InternalAxiosRequestConfig | undefined): number {
  if (!config) return 0
  const startTime = requestStartTimes.get(config)
  return startTime === undefined ? 0 : Math.round((performance.now() - startTime) * 100) / 100
}

api.interceptors.request.use(config => {
  requestStartTimes.set(config, performance.now())
  return config
})

api.interceptors.response.use(
  response => {
    recordRequestFromUrl({
      url: response.config.url,
      method: response.config.method,
      status: 'success',
      durationMs: elapsedMs(response.config),
    })
    return response
  },
  (error: AxiosError) => {
    recordRequestFromUrl({
      url: error.config?.url,
      method: error.config?.method,
      status: 'error',
      durationMs: elapsedMs(error.config),
    })
    return Promise.reject(error)
  },
)
```

This is the only place HTTP timing is measured — every existing service/hook/page gets it automatically since they all import `api` from this file already.

- [ ] **Step 4: Verify**

Run: `cd frontend && npx tsc -b --noEmit && npx eslint src`
Expected: both clean. If `noUnusedLocals` complains about `AxiosError` or `InternalAxiosRequestConfig`, confirm both are actually referenced (they are, in the response interceptor and `elapsedMs`).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/observability/apiGroups.ts frontend/src/observability/requestMetrics.ts frontend/src/services/api.ts
git commit -m "feat: instrument shared axios instance with request timing"
```

---

### Task 7: `useRequestMetrics` hook

**Files:**
- Create: `frontend/src/hooks/useRequestMetrics.ts`

**Interfaces:**
- Consumes: `getRequestMetricsSnapshot`, `subscribeRequestMetrics`, `RequestMetricEntry` from `../observability/requestMetrics` (Task 6).
- Produces: `useRequestMetrics(): RequestMetricsSummary` where `RequestMetricsSummary` has `entries`, `feed` (newest-first, capped 30), `totalCount`, `successCount`, `failureCount`, `successRate` (0–100), `averageDurationMs`, `fastestDurationMs: number | null`, `slowestDurationMs: number | null`. Consumed by Task 10 (`ActivityFeed`) and Task 11 (`SystemHealthPanel`).

- [ ] **Step 1: Create the hook**

Create `frontend/src/hooks/useRequestMetrics.ts`:

```ts
import { useSyncExternalStore } from 'react'
import { getRequestMetricsSnapshot, subscribeRequestMetrics, type RequestMetricEntry } from '../observability/requestMetrics'

export interface RequestMetricsSummary {
  entries: RequestMetricEntry[]
  /** Newest-first, capped at 30 — for the Live Activity Feed. */
  feed: RequestMetricEntry[]
  totalCount: number
  successCount: number
  failureCount: number
  /** 0–100. */
  successRate: number
  averageDurationMs: number
  fastestDurationMs: number | null
  slowestDurationMs: number | null
}

function summarize(entries: RequestMetricEntry[]): RequestMetricsSummary {
  const totalCount = entries.length
  const successCount = entries.filter(entry => entry.status === 'success').length
  const durations = entries.map(entry => entry.durationMs)
  return {
    entries,
    feed: entries.slice(0, 30),
    totalCount,
    successCount,
    failureCount: totalCount - successCount,
    successRate: totalCount > 0 ? (successCount / totalCount) * 100 : 0,
    averageDurationMs: totalCount > 0 ? durations.reduce((sum, value) => sum + value, 0) / totalCount : 0,
    fastestDurationMs: totalCount > 0 ? Math.min(...durations) : null,
    slowestDurationMs: totalCount > 0 ? Math.max(...durations) : null,
  }
}

/**
 * Live view over the shared request-metrics ring buffer — every request
 * made through the shared `api` axios instance, across the whole app.
 * Never issues a request itself.
 */
export function useRequestMetrics(): RequestMetricsSummary {
  const entries = useSyncExternalStore(subscribeRequestMetrics, getRequestMetricsSnapshot, getRequestMetricsSnapshot)
  return summarize(entries)
}
```

- [ ] **Step 2: Verify**

Run: `cd frontend && npx tsc -b --noEmit && npx eslint src`
Expected: both clean.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/hooks/useRequestMetrics.ts
git commit -m "feat: add useRequestMetrics hook over the request-metrics ring buffer"
```

---

### Task 8: `useQueryHealth` hook

**Files:**
- Create: `frontend/src/hooks/useQueryHealth.ts`

**Interfaces:**
- Consumes: `API_GROUPS`, `groupLabelForQueryKey` from `../observability/apiGroups` (Task 6).
- Produces: `ApiGroupStatus = 'healthy' | 'error' | 'loading' | 'idle'`, `ApiGroupHealth { label, status }`, `useQueryHealth(): QueryHealthSummary` where `QueryHealthSummary` has `cachedCount`, `activeCount`, `staleCount`, `fetchingCount`, `lastRefresh: number | null`, `groups: ApiGroupHealth[]`. Consumed by Task 10 (`ApiStatusGrid`) and Task 11 (`SystemHealthPanel`).

- [ ] **Step 1: Create the hook**

Create `frontend/src/hooks/useQueryHealth.ts`:

```ts
import { useSyncExternalStore } from 'react'
import { useQueryClient, type Query } from '@tanstack/react-query'
import { API_GROUPS, groupLabelForQueryKey } from '../observability/apiGroups'

export type ApiGroupStatus = 'healthy' | 'error' | 'loading' | 'idle'

export interface ApiGroupHealth {
  label: string
  status: ApiGroupStatus
}

export interface QueryHealthSummary {
  cachedCount: number
  activeCount: number
  staleCount: number
  fetchingCount: number
  lastRefresh: number | null
  groups: ApiGroupHealth[]
}

function statusForQueries(queries: Query[]): ApiGroupStatus {
  if (queries.length === 0) return 'idle'
  if (queries.some(query => query.state.fetchStatus === 'fetching')) return 'loading'
  if (queries.some(query => query.state.status === 'error')) return 'error'
  return 'healthy'
}

function summarize(queries: Query[]): QueryHealthSummary {
  const lastUpdatedTimestamps = queries.map(query => query.state.dataUpdatedAt).filter(value => value > 0)
  const groups: ApiGroupHealth[] = API_GROUPS.map(group => ({
    label: group.label,
    status: statusForQueries(queries.filter(query => groupLabelForQueryKey(query.queryKey) === group.label)),
  }))
  return {
    cachedCount: queries.length,
    activeCount: queries.filter(query => query.getObserversCount() > 0).length,
    staleCount: queries.filter(query => query.isStale()).length,
    fetchingCount: queries.filter(query => query.state.fetchStatus === 'fetching').length,
    lastRefresh: lastUpdatedTimestamps.length > 0 ? Math.max(...lastUpdatedTimestamps) : null,
    groups,
  }
}

/**
 * Live view over the app's shared QueryClient cache — reads state every
 * other hook in the app already produces; never issues a request itself.
 */
export function useQueryHealth(): QueryHealthSummary {
  const queryCache = useQueryClient().getQueryCache()
  return useSyncExternalStore(
    onStoreChange => queryCache.subscribe(onStoreChange),
    () => summarize(queryCache.getAll()),
    () => summarize(queryCache.getAll()),
  )
}
```

- [ ] **Step 2: Verify**

Run: `cd frontend && npx tsc -b --noEmit && npx eslint src`
Expected: both clean. If TS complains that bare `Query` needs type arguments, change every `Query[]`/`Query` usage in this file to `Query<unknown, unknown, unknown, readonly unknown[]>` — try the bare form first, since all four of `Query`'s generic parameters default in v5.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/hooks/useQueryHealth.ts
git commit -m "feat: add useQueryHealth hook reading the shared QueryClient cache"
```

---

### Task 9: Real backend health check

**Files:**
- Create: `frontend/src/services/healthApi.ts`
- Create: `frontend/src/hooks/useHealthCheck.ts`

**Interfaces:**
- Consumes: `api` from `../services/api` (Task 6, for `healthApi.ts`).
- Produces: `fetchHealth(): Promise<HealthResponse>`, `useHealthCheck()` (a `useQuery` result). Consumed by Task 11 (`SystemHealthPanel`).

`GET /health` is real and already exists in the backend (`backend/app/api/routes/health.py`), mounted at the app root — not under `/api/v1` like every other route. This is the one deliberately-recurring request in this whole feature (30s poll) — it's the correct, honest way to answer "is the backend reachable," replacing any inference from other query failures.

- [ ] **Step 1: Create the service function**

Create `frontend/src/services/healthApi.ts`:

```ts
import { api } from './api'

export interface HealthResponse {
  status: string
  version: string
  environment: string
}

/**
 * GET /health — see backend/app/api/routes/health.py. Mounted at the app
 * root (no /api/v1 prefix), unlike every other endpoint this app calls, so
 * the shared instance's baseURL is overridden per-request rather than
 * creating a second axios instance.
 */
export async function fetchHealth(): Promise<HealthResponse> {
  const baseURL = (api.defaults.baseURL ?? '').replace(/\/api\/v1\/?$/, '')
  const { data } = await api.get<HealthResponse>('/health', { baseURL })
  return data
}
```

- [ ] **Step 2: Create the hook**

Create `frontend/src/hooks/useHealthCheck.ts`:

```ts
import { useQuery } from '@tanstack/react-query'
import { fetchHealth } from '../services/healthApi'

export const healthKeys = {
  check: ['health', 'check'] as const,
}

/** Polls the real backend health endpoint to answer "is the backend reachable". */
export function useHealthCheck() {
  return useQuery({
    queryKey: healthKeys.check,
    queryFn: fetchHealth,
    staleTime: 15_000,
    gcTime: 60_000,
    retry: 0,
    refetchInterval: 30_000,
  })
}
```

- [ ] **Step 3: Verify**

Run: `cd frontend && npx tsc -b --noEmit && npx eslint src`
Expected: both clean.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/services/healthApi.ts frontend/src/hooks/useHealthCheck.ts
git commit -m "feat: add real backend health check via GET /health"
```

---

### Task 10: System Health subcomponents

**Files:**
- Create: `frontend/src/pages/observability/ApiStatusGrid.tsx`
- Create: `frontend/src/pages/observability/ActivityFeed.tsx`
- Create: `frontend/src/pages/observability/WorkflowOverview.tsx`
- Create: `frontend/src/pages/observability/DevInfoPanel.tsx`

**Interfaces:**
- Consumes: `useQueryHealth` (Task 8), `useRequestMetrics` (Task 7), `useDashboardSummary` (existing `../../hooks/useDashboard`), `useObservabilityOverview` (existing `../../hooks/useObservability`), `EmptyState`, `QueryError`, `Skeleton` (existing `ui/`), `formatDurationMs`, `formatRelativeTime`, `formatCount` (existing `../../utils/format`), `api` from `../../services/api` (Task 6).
- Produces: `ApiStatusGrid()`, `ActivityFeed()`, `WorkflowOverview()`, `DevInfoPanel()` — all consumed by Task 11 (`SystemHealthPanel`).

- [ ] **Step 1: `ApiStatusGrid`**

Create `frontend/src/pages/observability/ApiStatusGrid.tsx`:

```tsx
import { CheckCircle2, CircleDot, Loader2, MinusCircle } from 'lucide-react'
import { useQueryHealth, type ApiGroupStatus } from '../../hooks/useQueryHealth'

const STATUS_PRESENTATION: Record<ApiGroupStatus, { label: string; icon: typeof CheckCircle2; className: string }> = {
  healthy: { label: 'Healthy', icon: CheckCircle2, className: 'api-status-healthy' },
  error: { label: 'Error', icon: CircleDot, className: 'api-status-error' },
  loading: { label: 'Loading', icon: Loader2, className: 'api-status-loading' },
  idle: { label: 'Not yet queried', icon: MinusCircle, className: 'api-status-idle' },
}

/** Every API group's live status, derived from React Query's own cache — no requests issued here. */
export function ApiStatusGrid() {
  const { groups } = useQueryHealth()
  return (
    <div className="api-status-grid">
      {groups.map(group => {
        const presentation = STATUS_PRESENTATION[group.status]
        const Icon = presentation.icon
        return (
          <div className={`api-status-card ${presentation.className}`} key={group.label}>
            <Icon size={15} className={group.status === 'loading' ? 'spin' : undefined} />
            <span>{group.label}</span>
            <strong>{presentation.label}</strong>
          </div>
        )
      })}
    </div>
  )
}
```

- [ ] **Step 2: `ActivityFeed`**

Create `frontend/src/pages/observability/ActivityFeed.tsx`:

```tsx
import { CheckCircle2, XCircle } from 'lucide-react'
import { useRequestMetrics } from '../../hooks/useRequestMetrics'
import { EmptyState } from '../../ui/EmptyState'
import { formatDurationMs, formatRelativeTime } from '../../utils/format'

function describeEntry(apiGroup: string, status: 'success' | 'error'): string {
  return status === 'success' ? `${apiGroup} refreshed` : `${apiGroup} failed to load`
}

/** Every completed request this session, newest first, capped at 30. */
export function ActivityFeed() {
  const { feed } = useRequestMetrics()

  if (feed.length === 0) {
    return <EmptyState compact title="No activity yet" description="Requests made by this app during this session will appear here as they complete." />
  }

  return (
    <ul className="activity-feed">
      {feed.map(entry => (
        <li key={entry.id} className={entry.status === 'error' ? 'activity-feed-error' : undefined}>
          {entry.status === 'success' ? <CheckCircle2 size={14} /> : <XCircle size={14} />}
          <span>{describeEntry(entry.apiGroup, entry.status)}</span>
          <small>{formatDurationMs(entry.durationMs)}</small>
          <time>{formatRelativeTime(new Date(entry.timestamp).toISOString())}</time>
        </li>
      ))}
    </ul>
  )
}
```

- [ ] **Step 3: `WorkflowOverview`**

Communications has no aggregate-count endpoint (verified: `GET /communications` returns a plain array, no total field or header — see `backend/app/api/routes/communications.py`). Rather than fetch every page to count them (an unnecessary request this plan explicitly forbids), read whatever's already cached from a visit to the Communications page this session, and say so plainly.

Create `frontend/src/pages/observability/WorkflowOverview.tsx`:

```tsx
import { useQueryClient } from '@tanstack/react-query'
import { useDashboardSummary } from '../../hooks/useDashboard'
import { useObservabilityOverview } from '../../hooks/useObservability'
import type { Communication } from '../../types/communication'
import { QueryError } from '../../ui/QueryError'
import { Skeleton } from '../../ui/Skeleton'
import { formatCount } from '../../utils/format'

/**
 * Reads whatever communications-list queries are already in the cache
 * (e.g. from a visit to the Communications page this session) rather than
 * issuing a new request — there is no backend endpoint that returns a
 * total count.
 */
function useSessionCommunicationsCount(): number | null {
  const queryClient = useQueryClient()
  const queries = queryClient.getQueryCache().findAll({ queryKey: ['communications', 'list'] })
  if (queries.length === 0) return null
  const latest = queries.reduce((mostRecent, query) => (query.state.dataUpdatedAt > mostRecent.state.dataUpdatedAt ? query : mostRecent))
  return (latest.state.data as Communication[] | undefined)?.length ?? null
}

/** Computed entirely from data this app already fetches elsewhere — no new endpoints. */
export function WorkflowOverview() {
  const dashboard = useDashboardSummary()
  const observabilityOverview = useObservabilityOverview()
  const sessionCommunications = useSessionCommunicationsCount()

  if (dashboard.isPending) return <Skeleton style={{ height: 100 }} />
  if (dashboard.isError) {
    return <QueryError message={dashboard.error instanceof Error ? dashboard.error.message : 'Failed to load workflow overview.'} onRetry={() => void dashboard.refetch()} />
  }

  const summary = dashboard.data
  const totalMandates = Object.values(summary.mandate_counts_by_status).reduce((sum, count) => sum + (count ?? 0), 0)
  const totalPaymentAttempts = Object.values(summary.payment_attempt_counts_by_status).reduce((sum, count) => sum + (count ?? 0), 0)

  const tiles: Array<{ label: string; value: string; note?: string }> = [
    { label: 'Total mandates', value: formatCount(totalMandates) },
    { label: 'Pending retries', value: formatCount(summary.pending_retries) },
    { label: 'Payment attempts', value: formatCount(totalPaymentAttempts) },
    { label: 'Open escalations', value: formatCount(summary.open_escalations) },
    {
      label: 'AI decisions',
      value: observabilityOverview.data ? formatCount(observabilityOverview.data.total_ai_calls) : '—',
      note: observabilityOverview.isPending ? 'Loading…' : undefined,
    },
    {
      label: 'Communications',
      value: sessionCommunications === null ? '—' : formatCount(sessionCommunications),
      note: sessionCommunications === null ? 'Not visited this session' : "Loaded this session — the API has no total-count endpoint",
    },
  ]

  return (
    <div className="metric-grid">
      {tiles.map(tile => (
        <div className="metric-tile" key={tile.label}>
          <span>{tile.label}</span>
          <strong>{tile.value}</strong>
          {tile.note && <small className="metric-tile-note">{tile.note}</small>}
        </div>
      ))}
    </div>
  )
}
```

- [ ] **Step 4: `DevInfoPanel`**

Create `frontend/src/pages/observability/DevInfoPanel.tsx`:

```tsx
import { version as reactVersion } from 'react'
import { api } from '../../services/api'

/** Only ever rendered when import.meta.env.DEV is true (gated in SystemHealthPanel). */
export function DevInfoPanel() {
  const rows: Array<[string, string]> = [
    ['APP_ENV', import.meta.env.MODE],
    ['API base URL', api.defaults.baseURL ?? 'unset'],
    ['React version', reactVersion],
    ['Vite mode', import.meta.env.DEV ? 'development' : 'production'],
    ['Browser', navigator.userAgent],
    ['Window size', `${window.innerWidth} × ${window.innerHeight}`],
  ]
  return (
    <div className="dev-info-grid">
      {rows.map(([label, value]) => (
        <div key={label}>
          <span>{label}</span>
          <strong>{value}</strong>
        </div>
      ))}
    </div>
  )
}
```

- [ ] **Step 5: Add CSS for the four new components**

Modify `frontend/src/styles/global.css` — append at the end of the file:

```css
.api-status-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; margin-top: 12px; }
.api-status-card { display: flex; align-items: center; gap: 8px; padding: 12px 14px; border: 1px solid #d7e0ec; border-radius: 8px; background: rgba(255,255,255,.6); }
.api-status-card span { color: #5c6b83; font-size: 11px; font-weight: 700; flex: 1; }
.api-status-card strong { font-size: 11px; }
.api-status-healthy { color: #178a44; } .api-status-healthy strong { color: #178a44; }
.api-status-error { color: #c22f2f; } .api-status-error strong { color: #c22f2f; }
.api-status-loading { color: #2563eb; } .api-status-loading strong { color: #2563eb; }
.api-status-idle { color: #8090a5; } .api-status-idle strong { color: #8090a5; }
[data-theme='dark'] .api-status-card { background: rgba(17,28,44,.5); border-color: #2f4160; }
[data-theme='dark'] .api-status-card span { color: #a7b4c9; }
[data-theme='dark'] .api-status-healthy, [data-theme='dark'] .api-status-healthy strong { color: #4ade80; }
[data-theme='dark'] .api-status-error, [data-theme='dark'] .api-status-error strong { color: #f87171; }
[data-theme='dark'] .api-status-loading, [data-theme='dark'] .api-status-loading strong { color: #8fb4ff; }
[data-theme='dark'] .api-status-idle, [data-theme='dark'] .api-status-idle strong { color: #96a5bd; }

.activity-feed { display: grid; gap: 2px; margin-top: 12px; max-height: 340px; overflow-y: auto; }
.activity-feed li { display: flex; align-items: center; gap: 9px; padding: 9px 4px; border-bottom: 1px solid #edf1f6; color: #178a44; font-size: 12px; }
.activity-feed li span { flex: 1; color: #33445d; font-weight: 600; }
.activity-feed li small { color: #6b7690; font-size: 10px; }
.activity-feed li time { color: #8c9aab; font-size: 10px; }
.activity-feed li.activity-feed-error { color: #c22f2f; }
[data-theme='dark'] .activity-feed li { border-color: #2f4160; color: #4ade80; }
[data-theme='dark'] .activity-feed li span { color: #e1eaf7; }
[data-theme='dark'] .activity-feed li small, [data-theme='dark'] .activity-feed li time { color: #96a5bd; }
[data-theme='dark'] .activity-feed li.activity-feed-error { color: #f87171; }

.dev-info-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; margin-top: 12px; }
.dev-info-grid div { padding: 10px 12px; border: 1px solid #d7e0ec; border-radius: 7px; background: rgba(255,255,255,.6); overflow: hidden; }
.dev-info-grid span { display: block; color: #5c6b83; font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: .04em; }
.dev-info-grid strong { display: block; margin-top: 4px; color: #263349; font-size: 11px; font-weight: 600; overflow-wrap: break-word; }
[data-theme='dark'] .dev-info-grid div { background: rgba(17,28,44,.5); border-color: #2f4160; }
[data-theme='dark'] .dev-info-grid span { color: #a7b4c9; }
[data-theme='dark'] .dev-info-grid strong { color: #eef4fc; }

.metric-tile-note { display: block; margin-top: 4px; color: #8090a5; font-size: 9px; }
[data-theme='dark'] .metric-tile-note { color: #96a5bd; }

.tab-bar { display: flex; gap: 6px; margin-bottom: 20px; border-bottom: 1px solid #d7e0ec; }
.tab-button { padding: 10px 4px; margin-right: 20px; border: 0; border-bottom: 2px solid transparent; background: transparent; color: #8090a5; font-size: 13px; font-weight: 700; }
.tab-button:hover { color: #2563eb; }
.tab-button.active { color: #2563eb; border-bottom-color: #2563eb; }
[data-theme='dark'] .tab-bar { border-color: #2f4160; }
[data-theme='dark'] .tab-button { color: #96a5bd; }
[data-theme='dark'] .tab-button:hover, [data-theme='dark'] .tab-button.active { color: #8fb4ff; }
[data-theme='dark'] .tab-button.active { border-bottom-color: #8fb4ff; }
```

- [ ] **Step 6: Verify**

Run: `cd frontend && npx tsc -b --noEmit && npx eslint src`
Expected: both clean.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/pages/observability frontend/src/styles/global.css
git commit -m "feat: add System Health subcomponents (API status, activity feed, workflow overview, dev info)"
```

---

### Task 11: `SystemHealthPanel` root component

**Files:**
- Create: `frontend/src/pages/observability/SystemHealthPanel.tsx`

**Interfaces:**
- Consumes: `useHealthCheck` (Task 9), `useRequestMetrics` (Task 7), `useQueryHealth` (Task 8), `ApiStatusGrid`, `ActivityFeed`, `WorkflowOverview`, `DevInfoPanel` (Task 10), `SectionCard`, `StatusBadge` (existing), `formatDurationMs`, `formatRelativeTime` (existing).
- Produces: `SystemHealthPanel()` — consumed by Task 12 (`ObservabilityPage.tsx`).

- [ ] **Step 1: Create the component**

Create `frontend/src/pages/observability/SystemHealthPanel.tsx`:

```tsx
import { useQueryClient } from '@tanstack/react-query'
import { RefreshCw } from 'lucide-react'
import { useState } from 'react'
import { useHealthCheck } from '../../hooks/useHealthCheck'
import { useQueryHealth } from '../../hooks/useQueryHealth'
import { useRequestMetrics } from '../../hooks/useRequestMetrics'
import { SectionCard } from '../../ui/SectionCard'
import { StatusBadge } from '../../ui/StatusBadge'
import { formatDurationMs, formatRelativeTime } from '../../utils/format'
import { ActivityFeed } from './ActivityFeed'
import { ApiStatusGrid } from './ApiStatusGrid'
import { DevInfoPanel } from './DevInfoPanel'
import { WorkflowOverview } from './WorkflowOverview'

export function SystemHealthPanel() {
  const health = useHealthCheck()
  const requestMetrics = useRequestMetrics()
  const queryHealth = useQueryHealth()
  const queryClient = useQueryClient()
  const [isRefreshing, setIsRefreshing] = useState(false)

  const handleRefreshAll = async () => {
    setIsRefreshing(true)
    try {
      await queryClient.refetchQueries()
    } finally {
      setIsRefreshing(false)
    }
  }

  return (
    <>
      <SectionCard title="System health" meta="Backend reachability (GET /health) and client-observed request latency">
        <div className="metric-grid">
          <div className="metric-tile">
            <span>Backend reachable</span>
            <strong>
              {health.isPending ? 'Checking…' : <StatusBadge label={health.isSuccess ? 'Yes' : 'No'} tone={health.isSuccess ? 'success' : 'danger'} />}
            </strong>
          </div>
          <div className="metric-tile"><span>Average response time</span><strong>{formatDurationMs(requestMetrics.averageDurationMs)}</strong></div>
          <div className="metric-tile"><span>Fastest response</span><strong>{formatDurationMs(requestMetrics.fastestDurationMs)}</strong></div>
          <div className="metric-tile"><span>Slowest response</span><strong>{formatDurationMs(requestMetrics.slowestDurationMs)}</strong></div>
          <div className="metric-tile"><span>Successful requests</span><strong>{requestMetrics.successCount}</strong></div>
          <div className="metric-tile"><span>Failed requests</span><strong>{requestMetrics.failureCount}</strong></div>
          <div className="metric-tile"><span>Success rate</span><strong>{requestMetrics.successRate.toFixed(1)}%</strong></div>
        </div>
      </SectionCard>

      <SectionCard title="API status" meta="Live status of each API this app calls, read from React Query's own cache">
        <ApiStatusGrid />
      </SectionCard>

      <SectionCard title="React Query cache" meta="Live state of the client-side query cache">
        <div className="metric-grid">
          <div className="metric-tile"><span>Cached queries</span><strong>{queryHealth.cachedCount}</strong></div>
          <div className="metric-tile"><span>Active queries</span><strong>{queryHealth.activeCount}</strong></div>
          <div className="metric-tile"><span>Stale queries</span><strong>{queryHealth.staleCount}</strong></div>
          <div className="metric-tile"><span>Fetching queries</span><strong>{queryHealth.fetchingCount}</strong></div>
          <div className="metric-tile"><span>Last refresh</span><strong>{queryHealth.lastRefresh ? formatRelativeTime(new Date(queryHealth.lastRefresh).toISOString()) : 'Never'}</strong></div>
        </div>
      </SectionCard>

      <SectionCard title="Workflow overview" meta="Computed from data this app has already fetched — no new endpoints">
        <WorkflowOverview />
      </SectionCard>

      <SectionCard title="Manual refresh" meta="Refetch every active query across the app">
        <button type="button" className="primary-button" onClick={() => void handleRefreshAll()} disabled={isRefreshing}>
          <RefreshCw size={15} className={isRefreshing ? 'spin' : undefined} />
          {isRefreshing ? 'Refreshing…' : 'Refresh all'}
        </button>
      </SectionCard>

      <div className="chart-grid">
        <SectionCard title="Live activity feed" meta="Every completed request this session, newest first">
          <ActivityFeed />
        </SectionCard>
        <SectionCard title="Performance" meta="This session's client-observed request timing">
          <div className="metric-grid">
            <div className="metric-tile"><span>Average fetch time</span><strong>{formatDurationMs(requestMetrics.averageDurationMs)}</strong></div>
            <div className="metric-tile"><span>Longest fetch</span><strong>{formatDurationMs(requestMetrics.slowestDurationMs)}</strong></div>
            <div className="metric-tile"><span>Shortest fetch</span><strong>{formatDurationMs(requestMetrics.fastestDurationMs)}</strong></div>
            <div className="metric-tile"><span>Queries this session</span><strong>{requestMetrics.totalCount}</strong></div>
            <div className="metric-tile"><span>Failed queries</span><strong>{requestMetrics.failureCount}</strong></div>
            <div className="metric-tile"><span>Success percentage</span><strong>{requestMetrics.successRate.toFixed(1)}%</strong></div>
          </div>
        </SectionCard>
      </div>

      {import.meta.env.DEV && (
        <SectionCard title="Developer" meta="Only visible in development">
          <DevInfoPanel />
        </SectionCard>
      )}
    </>
  )
}
```

- [ ] **Step 2: Verify**

Run: `cd frontend && npx tsc -b --noEmit && npx eslint src`
Expected: both clean.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/observability/SystemHealthPanel.tsx
git commit -m "feat: add SystemHealthPanel root component"
```

---

### Task 12: Wire the tab switcher into `ObservabilityPage` + fix the two honest-zero fields

**Files:**
- Modify: `frontend/src/pages/ObservabilityPage.tsx`

**Interfaces:**
- Consumes: `SystemHealthPanel` (Task 11).

- [ ] **Step 1: Add tab state and imports**

Add to the top of `frontend/src/pages/ObservabilityPage.tsx` (after the existing `useState` import, which already exists):

Replace:
```tsx
import { useState } from 'react'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import {
  useObservabilityMetrics,
  useObservabilityOverview,
  useProviderHealth,
  useWorkflowErrors,
  useWorkflowExecutionDetail,
  useWorkflowExecutions,
} from '../hooks/useObservability'
```
with:
```tsx
import { useState } from 'react'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import {
  useObservabilityMetrics,
  useObservabilityOverview,
  useProviderHealth,
  useWorkflowErrors,
  useWorkflowExecutionDetail,
  useWorkflowExecutions,
} from '../hooks/useObservability'
import { SystemHealthPanel } from './observability/SystemHealthPanel'
```

- [ ] **Step 2: Fix the "Avg AI Latency" overview tile**

Replace:
```tsx
            <div className="metric-tile"><span>Avg AI Latency</span><strong>{formatDurationMs(overview.data.average_ai_latency_ms)}</strong></div>
```
with:
```tsx
            <div className="metric-tile" title="The backend does not yet attach AI-call latency to workflow executions."><span>Avg AI Latency</span><strong>Not tracked</strong></div>
```

- [ ] **Step 3: Drop the fake "AI" bar from the latency chart and note why**

Replace:
```tsx
  const latencyChartData = metrics.data
    ? [
        { name: 'Workflow', ms: Math.round(metrics.data.average_workflow_duration_ms * 100) / 100 },
        { name: 'Node (avg)', ms: Math.round(metrics.data.average_node_duration_ms * 100) / 100 },
        { name: 'Retry', ms: Math.round(metrics.data.retry_scheduling_latency_ms * 100) / 100 },
        { name: 'Comms', ms: Math.round(metrics.data.communication_latency_ms * 100) / 100 },
        { name: 'Escalation', ms: Math.round(metrics.data.escalation_latency_ms * 100) / 100 },
        { name: 'AI', ms: Math.round(metrics.data.ai_latency_ms * 100) / 100 },
        { name: 'DB Persist', ms: Math.round(metrics.data.database_persistence_latency_ms * 100) / 100 },
      ]
    : []
```
with:
```tsx
  // AI latency is intentionally omitted here — the backend hardcodes
  // ai_latency_ms to 0.0 (never wires AI-trace latency onto a workflow
  // execution), so plotting it would show a false "0ms" rather than a real
  // measurement. See the "Avg AI Latency" tile above for the honest state.
  const latencyChartData = metrics.data
    ? [
        { name: 'Workflow', ms: Math.round(metrics.data.average_workflow_duration_ms * 100) / 100 },
        { name: 'Node (avg)', ms: Math.round(metrics.data.average_node_duration_ms * 100) / 100 },
        { name: 'Retry', ms: Math.round(metrics.data.retry_scheduling_latency_ms * 100) / 100 },
        { name: 'Comms', ms: Math.round(metrics.data.communication_latency_ms * 100) / 100 },
        { name: 'Escalation', ms: Math.round(metrics.data.escalation_latency_ms * 100) / 100 },
        { name: 'DB Persist', ms: Math.round(metrics.data.database_persistence_latency_ms * 100) / 100 },
      ]
    : []
```

- [ ] **Step 4: Fix the provider card's "Failures" and "Avg Latency" fields**

Replace:
```tsx
                  <div className="provider-stats">
                    <div><span>Requests Today</span><strong>{formatCount(provider.requests_today)}</strong></div>
                    <div><span>Failures</span><strong>{formatCount(provider.failures)}</strong></div>
                    <div><span>Avg Latency</span><strong>{formatDurationMs(provider.average_latency_ms)}</strong></div>
                    <div><span>Avg Confidence</span><strong>{(provider.average_confidence * 100).toFixed(1)}%</strong></div>
                  </div>
```
with:
```tsx
                  <div className="provider-stats">
                    <div><span>Requests Today</span><strong>{formatCount(provider.requests_today)}</strong></div>
                    <div title="The backend does not yet track per-provider failure counts."><span>Failures</span><strong>Not tracked</strong></div>
                    <div title="The backend does not yet attach AI-call latency to workflow executions."><span>Avg Latency</span><strong>Not tracked</strong></div>
                    <div><span>Avg Confidence</span><strong>{(provider.average_confidence * 100).toFixed(1)}%</strong></div>
                  </div>
```

- [ ] **Step 5: Add the caveat to the Performance metrics section's `meta`**

Replace:
```tsx
      <SectionCard
        title="Performance metrics"
        meta="Current aggregate latencies from GET /observability/metrics — shown as a comparison, not a trend, since the backend only reports point-in-time aggregates"
      >
```
with:
```tsx
      <SectionCard
        title="Performance metrics"
        meta="Current aggregate latencies from GET /observability/metrics — shown as a comparison, not a trend, since the backend only reports point-in-time aggregates. AI latency is omitted (not tracked end-to-end by the backend yet — see the Avg AI Latency tile above)."
      >
```

- [ ] **Step 6: Add the tab switcher, wrapping the existing five sections under "Workflow Insights"**

Replace the component body's opening (from `export function ObservabilityPage()` through the `return` statement's outer wrapper) — specifically, replace:
```tsx
export function ObservabilityPage() {
  const { settings } = useSettings()
  const [offset, setOffset] = useState(0)
  const [selectedExecutionId, setSelectedExecutionId] = useState<string | null>(null)
```
with:
```tsx
type ObservabilityTab = 'workflow-insights' | 'system-health'

export function ObservabilityPage() {
  const { settings } = useSettings()
  const [offset, setOffset] = useState(0)
  const [selectedExecutionId, setSelectedExecutionId] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<ObservabilityTab>('workflow-insights')
```

Then replace:
```tsx
      <PageHeader title="Observability" description="Monitor AI execution quality and workflow behavior." />

      <SectionCard title="Overview" meta="Real metrics from GET /observability/overview">
```
with:
```tsx
      <PageHeader title="Observability" description="Monitor AI execution quality and workflow behavior." />

      <div className="tab-bar">
        <button type="button" className={`tab-button ${activeTab === 'workflow-insights' ? 'active' : ''}`} onClick={() => setActiveTab('workflow-insights')}>
          Workflow Insights
        </button>
        <button type="button" className={`tab-button ${activeTab === 'system-health' ? 'active' : ''}`} onClick={() => setActiveTab('system-health')}>
          System Health
        </button>
      </div>

      {activeTab === 'system-health' && <SystemHealthPanel />}

      {activeTab === 'workflow-insights' && <>

      <SectionCard title="Overview" meta="Real metrics from GET /observability/overview">
```

Then replace the very end of the component — find:
```tsx
      <WorkflowDetailModal executionId={selectedExecutionId} onClose={() => setSelectedExecutionId(null)} />
    </motion.section>
  )
}
```
with:
```tsx
      <WorkflowDetailModal executionId={selectedExecutionId} onClose={() => setSelectedExecutionId(null)} />
      </>}
    </motion.section>
  )
}
```

- [ ] **Step 7: Verify**

Run: `cd frontend && npx tsc -b --noEmit && npx eslint src`
Expected: both clean. Pay attention to JSX fragment balance from Step 6 — the added `<>` must close exactly once, right before `</motion.section>`.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/pages/ObservabilityPage.tsx
git commit -m "feat: add System Health tab to Observability page; show honest 'Not tracked' for backend-placeholder AI latency fields"
```

---

### Task 13: Full verification and report

**Files:** none (verification only).

- [ ] **Step 1: Build**

Run: `cd frontend && npm run build`
Expected: succeeds with no TypeScript or Vite errors. Record actual output.

- [ ] **Step 2: Type check**

Run: `cd frontend && npx tsc -b --noEmit`
Expected: no errors. Record actual output.

- [ ] **Step 3: Lint**

Run: `cd frontend && npx eslint src`
Expected: no errors (warnings, if any, must be reviewed and either fixed or justified — do not silently ignore). Record actual output.

- [ ] **Step 4: Manual verification**

Use the `run` skill to start the dev server (or `npm run dev` directly if no project-specific skill is found) and check, in both light and dark theme:
- Table contrast, badge colors, row hover, disabled Pagination buttons (navigate to the last page of any list), input placeholders, and filter controls read clearly.
- AI Decisions: confidence bars show the correct tier color at a few different scores; decision-type badges show distinct colors; reasoning wraps and its full text appears on hover; the modal shows the same.
- Communications: each channel shows its icon; message wraps with a hover tooltip.
- Escalations: level and status badges are legible; reason wraps with a hover tooltip.
- Observability → System Health tab: "Backend reachable" shows Yes with the backend running; stop the backend and confirm it flips to No within ~30s; API Status grid reflects real navigation (visit a couple of other pages, then return — their group should show Healthy); React Query cache counts change as you navigate; Workflow Overview numbers match the Dashboard page's own numbers; Live Activity Feed populates and caps at 30; Manual Refresh shows a loading state and updates data; the Developer section only appears when running `npm run dev`, not in a production build preview.
- Observability → Workflow Insights tab: "Avg AI Latency" tile shows "Not tracked" (not "0.00 ms"); the latency bar chart has six bars, no "AI" bar; each provider card shows "Not tracked" for Failures and Avg Latency.

Record what actually happened — pass/fail per bullet, not an assumption.

- [ ] **Step 5: Report**

Produce the final report using the actual verification results:
1. Files created
2. Files modified
3. Features added
4. Performance-relevant notes (interceptor overhead is one extra function call per request; ring buffer capped at 200 entries so memory is bounded; the only new recurring network request is the 30s `/health` poll)
5. Screens/pages improved
6. Assumptions (copy from spec §6, confirm each still holds after implementation)

No commit for this task — it's verification and reporting only.
