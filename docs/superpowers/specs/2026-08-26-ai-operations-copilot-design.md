# AI Operations Copilot — Design

Status: approved for planning
Date: 2026-08-26

## Goal

Transform the platform from "a dashboard with AI running in the background" into
an AI-first operations platform by adding a premium, floating AI Copilot that
answers natural-language questions about payments, mandates, workflow
decisions, communications, escalations, and operational health — grounded
entirely in real backend data, via the existing Groq integration.

## Non-goals

- No new database tables or migrations. Chat history is client-side only.
- No agentic tool-calling loop. Context is assembled deterministically in
  Python before a single call to Groq.
- No changes to existing AI decision flows (`AIService.generate_retry_decision`
  etc.) — the Copilot is an additive, read-only slice.
- No auth/session system changes. The app has none today; the Copilot doesn't
  add one.

## Architecture overview

```
Frontend (drawer) --POST /api/v1/copilot/chat (SSE)--> FastAPI route
                                                             |
                                                     CopilotService
                                                    /                \
                                     ContextBuilder                   GroqLLM.stream()
                                (reuses existing services)         (new streaming method)
                                             |
                     DashboardService, MandateService, PaymentService,
                     RetryService, EscalationService, CommunicationService,
                     DecisionService, WorkflowExecutionService
```

Every box on the right side of `ContextBuilder` already exists. The Copilot
adds an orchestration layer on top, not new data-access logic.

## Backend design

### 1. `BaseLLM.stream()` / `GroqLLM.stream()`

`base_llm.py` gains a second abstract method:

```python
@abstractmethod
def stream(self, messages: Sequence[Mapping[str, str]], *, system_prompt: str | None = None, **options: Any) -> Iterator[str]:
    """Yield content deltas for a multi-turn conversation as they arrive."""
```

Unlike `generate()`, `stream()` takes a full `messages` list (role/content
pairs) rather than a single prompt string, because the Copilot is
conversational (needs prior turns), not single-shot. `GroqLLM.stream()`
mirrors `generate()`'s error translation (`AuthenticationError`,
`ProviderTimeoutError`, `RateLimitError`, `ProviderUnavailableError`) but
calls `client.chat.completions.create(..., stream=True)` and yields
`chunk.choices[0].delta.content` for each chunk that has content. No retry
loop on a stream already in progress — if it fails mid-stream, the generator
raises and the route turns that into a terminal SSE `error` event.

### 2. `app/copilot/context_builder.py`

```python
@dataclass(frozen=True)
class CopilotContext:
    sources: list[str]        # human-readable labels, e.g. "Mandate DEMO-1029", "14-day payment trend"
    data: dict[str, Any]      # JSON-serializable, fed into the prompt template
```

```python
def build_context(
    *, message: str, history: Sequence[ChatTurn], page_path: str | None,
    dashboard: DashboardService, mandates: MandateService, payments: PaymentService,
    retries: RetryService, escalations: EscalationService, communications: CommunicationService,
    decisions: DecisionService, workflow_executions: WorkflowExecutionService,
) -> CopilotContext: ...
```

Logic (pure Python, no LLM involved):

1. **Always**: `dashboard.get_summary()` (counts, revenue recovered, pending
   retries, open escalations, recent decisions) — this is the one guaranteed,
   cheap query, giving the model baseline situational awareness for prioritization/summary questions.
2. **Entity detection** — regex/scan over `message` (and, if nothing matches
   there, the last user turn in `history`) for:
   - a bare UUID → tried against mandate id, then payment attempt id, then
     escalation id, then workflow execution id (first hit wins; each lookup
     is a single indexed `get_by_id` call, so trying a couple in sequence is
     cheap).
   - a reference-shaped token (`mandate_reference` is a free-text unique
     string, e.g. seed data uses a `DEMO-` prefix; the detector looks for a
     short alphanumeric/hyphen token that isn't a common English word,
     confirmed against `mandate_repository.get_by_reference`) → that
     mandate's payment history (`payments.list_attempts`), latest decision
     (`decisions.get_latest_decision`), open communications
     (`communications.list_communications`), and escalations. A miss here is
     cheap (one indexed lookup) and simply produces no match, not an error.
   - a `customer_id` token (mandates carry a free-text `customer_id`; a
     quoted or prefixed token, or the phrase "customer <token>", is tried
     against `mandate_repository.search_by_customer`).
3. **Keyword-driven topic fetches** (independent, only the matched ones run):
   | keywords | data pulled |
   |---|---|
   | trend, success rate, today, summar* | `dashboard.get_trend(days=7 or 14 depending on "today" vs "week")` |
   | workflow, execution, slowest, longest | `workflow_executions.list_executions()` + `.get_overview()` |
   | escalat*, risk, attention, priorit* | `escalations.list_open_escalations()` |
   | anomal*, error, provider, health, observability | `workflow_executions.get_provider_health()` + `.list_errors()` + `.get_metrics()` |
   | communicat*, sms, email, whatsapp, message | `communications.list_communications(limit=20)` |
   | retry, retries, queue | `retries.list_pending_retries()` |
   | decision, ai recommend*, confidence | `decisions.list_decisions(limit=10)` (already in dashboard summary, but a full list for decision-focused questions) |
4. **Page context**: if `page_path` is one of the known routes (e.g.
   `/escalations`, `/retry-queue`), and no keyword already triggered that
   topic's fetch, add a light hint to `sources`/`data` noting "the user is
   currently viewing the Escalations page" — grounds pronoun questions like
   "what should I look at here?" without any new plumbing (the frontend
   already knows its own route).
5. Every fetch appends a human-readable label to `sources` (e.g. `"Mandate
   DEMO-1029 (customer CUST-4471)"`, `"Open escalations (3)"`) — this list is
   what the frontend renders as the "grounded in" chip row, and what the
   system prompt is told to cite from and only from.
6. Cap every list fetch (`limit=`) — this is a chat context, not a report;
   nothing here needs more than 10-20 rows to answer well, keeping the
   prompt concise per the performance requirement.

All exceptions from a lookup (e.g. `NotFoundError` for a mandate reference
that doesn't exist) are caught inside `build_context` and turned into a
`sources` entry like `"Mandate <reference>: not found"` — this is what lets
the model say "I don't have a mandate with that reference" instead of
silently guessing.

### 3. `app/copilot/service.py`

```python
class CopilotService:
    def __init__(self, *, ai_service: AIService | None, dashboard, mandates, payments,
                 retries, escalations, communications, decisions, workflow_executions): ...

    def stream_reply(self, *, message: str, history: Sequence[ChatTurn], page_path: str | None) -> Iterator[CopilotEvent]:
        context = build_context(...)
        yield CopilotEvent(type="sources", items=context.sources)
        if self.ai_service is None or self.ai_service.llm is None:
            yield CopilotEvent(type="error", message="The AI assistant isn't configured right now (no LLM provider available). Operational data is still fully available across the dashboard.")
            return
        system_prompt = render_copilot_system_prompt(context.data)
        messages = [{"role": h.role, "content": h.content} for h in history] + [{"role": "user", "content": message}]
        try:
            for delta in self.ai_service.llm.stream(messages, system_prompt=system_prompt):
                yield CopilotEvent(type="delta", content=delta)
        except ProviderError as exc:
            yield CopilotEvent(type="error", message=_friendly_provider_message(exc))
            return
        yield CopilotEvent(type="done")
```

Reuses `AIService` purely as a container for the resolved `llm` — no new
prompt/parse/validate pipeline is needed since the Copilot's output is free
text, not a structured decision. Observability logging
(`log_request`/`log_response`/`record_latency`) wraps the stream the same
way `AIService._generate` does today, so Copilot calls show up in the
existing observability metrics without a separate tracking system.

### 4. `app/prompts/copilot_system.txt`

Follows the existing `$context`-substitution convention:

```
You are the AI Operations Copilot inside REDIAL, a mandate retry sequencing
platform. Answer the operator's question using ONLY the data below — never
invent payments, mandates, customers, decisions, or numbers that are not
present here.

If the data needed to answer is not present, say so plainly and suggest what
the operator could check instead. Do not guess.

Be concise and concrete: reference real IDs, amounts, and dates from the data.
Use markdown (short paragraphs, bullet lists, bold for key numbers) where it
aids scanning. Do not pad with generic advice unrelated to the data shown.

Data:
$context

Respond as REDIAL's Copilot, speaking directly to the operator.
```

### 5. `app/api/routes/copilot.py`

```
POST /api/v1/copilot/chat
Request:  { "message": str, "history": [{"role": "user"|"assistant", "content": str}], "page_path": str | null }
Response: text/event-stream
  data: {"type": "sources", "items": [...]}
  data: {"type": "delta", "content": "..."}       (repeated)
  data: {"type": "error", "message": "..."}       (terminal, only on failure)
  data: {"type": "done"}                          (terminal, only on success)
```

Implemented as a **sync** route function (matches the rest of this
synchronous, SQLAlchemy-`Session`-based codebase) returning
`StreamingResponse(generator, media_type="text/event-stream")`; FastAPI runs
sync route functions in a threadpool automatically, so this doesn't block
the event loop any more than the existing decision endpoints already do.
`history` is capped server-side (last ~10 turns) before being handed to
`build_context`/the LLM, bounding prompt size regardless of what the client
sends.

### 6. Wiring

- `get_copilot_service` added to `dependencies.py`, composing the same
  per-request services `get_dashboard_service` already composes, plus
  `get_ai_service`.
- `copilot.router` registered in `router.py` under `/api/v1`.

## Frontend design

### Module layout — `frontend/src/copilot/`

- `CopilotLauncher.tsx` — fixed-position floating button, bottom-right,
  mounted once inside `AppShell` (so present on every `/dashboard/*` route,
  absent from `/`, `/login`, `/signup`). Subtle idle animation (soft pulse on
  the icon), badge-free (no unread-count concept — it's a pull tool, not a
  notification stream).
- `CopilotDrawer.tsx` — slides in from the right with `framer-motion`
  (`AnimatePresence`, spring transition matching the sidebar's existing
  motion feel), backdrop scrim on mobile (reusing the `.scrim` pattern from
  `AppShell`), fixed width ~420px on desktop, full-viewport on narrow
  screens. Header: brand mark + "Copilot" + model/status pill + reset button
  + close button. Body: scrollable message list. Footer: composer.
- `CopilotMessage.tsx` — one bubble. User messages: right-aligned, accent
  background. Assistant messages: left-aligned, card surface, `react-markdown`
  (+`remark-gfm` for tables/lists) rendering, a monospace-styled "sources"
  chip row underneath listing what grounded the answer (reusing the
  `terminal-panel`/`route-chip` visual language already in the codebase),
  and a relative timestamp (reusing `ui/Timestamp.tsx`).
- `CopilotEmptyState.tsx` — shown when there are no messages: short framing
  copy + a grid of ~6 clickable suggested questions drawn directly from the
  brief's examples ("Summarize today's activity", "Which mandates are
  highest risk?", "What should operations prioritize today?", "Show payment
  success trends", "Which workflows took the longest?", "What anomalies do
  you notice?") — clicking one sends it immediately.
- `useCopilotChat.ts` — owns message state (`localStorage`-persisted under a
  single key, following the existing `useTheme`/localStorage pattern already
  in the codebase), the in-flight `AbortController`, and `sendMessage()`
  which POSTs via `copilotApi.streamChat(...)` and applies `delta` events to
  the in-progress assistant message as they arrive, `sources` events to that
  message's source list, and `error` events as a distinguishable
  system-error bubble with a "Retry" action.
- `src/services/copilotApi.ts` — `fetch`-based (not axios — axios doesn't
  expose a streaming body reader) POST with manual SSE frame parsing
  (`ReadableStreamDefaultReader` + `TextDecoder`, split on `\n\n`), yielding
  parsed events to a callback.
- `src/types/copilot.ts` — `CopilotMessage`, `CopilotEvent`,
  `CopilotChatRequest` types.

### UX details

- **Keyboard shortcuts**: `⌘/Ctrl+K` toggles the drawer from anywhere in
  `AppShell` (global `keydown` listener scoped to the shell, cleaned up on
  unmount); `Esc` closes the drawer; `Enter` sends, `Shift+Enter` inserts a
  newline in the composer.
- **Intelligent scrolling**: auto-scrolls to follow new streamed tokens only
  while already at (or near) the bottom; if the operator has scrolled up to
  re-read something, streaming continues without yanking their scroll
  position, and a small "↓ New content" pill appears to jump back down.
  Standard chat-app scroll behavior.
- **Streaming/typing indicator**: three-dot pulse (reusing the existing
  `.thinking-pulse` styling already defined in `global.css` for the landing
  page's AI section) shown from send until the first `delta` arrives; once
  text starts streaming, the pulse is replaced by the growing text itself.
- **Reset**: a header button clears `localStorage` + in-memory state and
  returns to the empty state, with a lightweight confirm only if there's an
  active conversation (skip the confirm on an already-empty thread).
- **Loading/error states**: connection failure (fetch throws before any SSE
  frame) renders a `QueryError`-styled inline notice with retry, matching
  the existing `ui/QueryError.tsx` pattern; a mid-stream `error` event
  renders as a distinct assistant bubble tone (not the user's normal
  markdown bubble) so a partial/failed answer is visually obvious, never
  mistaken for a complete one.
- **Responsive**: full-screen drawer below ~640px, matching the existing
  sidebar's mobile breakpoint conventions in `global.css`.

### Styling

A new, clearly delimited `Copilot` section appended to
`frontend/src/styles/global.css`, following the file's existing
single-stylesheet, CSS-custom-property convention (no CSS-in-JS, no new
styling system) — reusing `--accent`, `--card`, `--border`, `--radius-*`,
`--shadow-*` tokens so the Copilot is indistinguishable in material language
from the rest of the app, in both light and dark themes.

### New dependency

`react-markdown` + `remark-gfm` — the brief explicitly requires markdown
rendering; nothing in the current dependency tree provides it.

## API contract summary

```
POST /api/v1/copilot/chat
Request body:
{
  "message": "Which mandates are highest risk?",
  "history": [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}],
  "page_path": "/dashboard"
}

Response: text/event-stream, one JSON object per `data:` line:
{"type": "sources", "items": ["Dashboard summary", "Open escalations (4)"]}
{"type": "delta", "content": "Based on "}
{"type": "delta", "content": "current data, "}
...
{"type": "done"}
```

On failure at any point after `sources`, a single `{"type": "error", ...}`
line replaces the rest of the stream; the connection then closes normally
(no dangling `done`).

## Error handling & hallucination guardrails

- No LLM configured → `error` event with a clear, honest message; UI never
  presents this as a real answer.
- Unknown entity referenced (mandate reference / id not found) → surfaced as
  a `sources` entry saying so, which the system prompt instructs the model to
  relay ("I don't have a mandate with that reference") rather than
  fabricate.
- Provider error mid-stream (timeout, rate limit, auth) → terminal `error`
  event with a provider-appropriate message, no partial answer presented as
  final.
- System prompt explicitly forbids inventing data not present in `$context`
  and instructs the model to say when information is missing — this is the
  primary anti-hallucination control, backed by the fact that `$context`
  itself is assembled from real repository/service reads, never synthetic.

## Testing & verification plan

- Backend unit tests (`backend/tests/copilot/`): `context_builder` — given
  representative questions (mandate reference present, UUID present, no
  entity + trend keyword, no entity + no keyword, unknown mandate
  reference), assert the right service calls happen and the right `sources`
  labels are produced, using stub/fake services (following whatever
  fixture/fake pattern the existing `backend/tests/` suite already uses).
  `GroqLLM.stream()` — a fake Groq client stream is chunked correctly into
  deltas and error paths translate correctly, mirroring the existing
  `generate()` test style.
- Frontend: `tsc -b`, `eslint .`, `vite build` must all pass clean.
- End-to-end: run the dev server, open the Copilot from at least two
  different pages, ask several of the brief's example questions against
  real seeded data, confirm: markdown renders, streaming is visibly
  progressive, sources chips name real records, reset clears history,
  `⌘K`/`Esc` work, and (by temporarily unsetting `GROQ_API_KEY`) confirm the
  graceful "AI unavailable" path never fabricates an answer.

## Files touched

**New (backend)**: `app/copilot/__init__.py`, `app/copilot/context_builder.py`,
`app/copilot/service.py`, `app/prompts/copilot_system.txt`,
`app/api/routes/copilot.py`, `backend/tests/copilot/*`.

**Modified (backend)**: `app/llm/base_llm.py`,
`app/llm/providers/groq_provider.py`, `app/api/router.py`,
`app/api/dependencies.py`.

**New (frontend)**: `src/copilot/CopilotLauncher.tsx`,
`src/copilot/CopilotDrawer.tsx`, `src/copilot/CopilotMessage.tsx`,
`src/copilot/CopilotEmptyState.tsx`, `src/copilot/useCopilotChat.ts`,
`src/services/copilotApi.ts`, `src/types/copilot.ts`.

**Modified (frontend)**: `src/layout/AppShell.tsx`,
`src/styles/global.css`, `frontend/package.json`.
