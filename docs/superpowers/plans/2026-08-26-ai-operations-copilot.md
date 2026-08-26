# AI Operations Copilot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a floating, streaming AI Copilot that answers natural-language operational questions using real backend data, reusing the existing service layer and Groq integration.

**Architecture:** A deterministic Python context builder inspects each question and pulls only the relevant data from existing services (dashboard, mandates, payments, retries, escalations, communications, decisions, workflow executions). A thin Copilot service renders that context into a system prompt and streams a Groq chat completion back over Server-Sent Events. The frontend is a floating launcher + slide-in drawer that renders markdown, streams tokens live, and shows exactly which real data grounded each answer.

**Tech Stack:** FastAPI (sync routes, `StreamingResponse`), SQLAlchemy Session-based services (existing), Groq SDK `stream=True`, React 19 + TypeScript, `framer-motion`, `lucide-react`, `react-markdown` + `remark-gfm` (new), native `fetch` + manual SSE parsing (no new HTTP client).

**Spec:** `docs/superpowers/specs/2026-08-26-ai-operations-copilot-design.md`

## Global Constraints

- No new database tables or migrations. Conversation history is client-side only (`localStorage`), per the spec.
- No agentic tool-calling loop. All context assembly is deterministic Python, not LLM-driven.
- Backend stays synchronous throughout (SQLAlchemy `Session`, sync route functions, sync Groq SDK calls) — matches every existing route/service in this codebase.
- The only new frontend dependencies are `react-markdown` and `remark-gfm` (required for the explicitly-requested markdown rendering).
- This repo has **no frontend automated test runner** (no vitest/jest in `frontend/package.json`). Frontend tasks are verified with `tsc -b`, `eslint .`, and `vite build` instead of a red/green test cycle — do not invent a test framework.
- Follow existing conventions exactly: `PromptManager`'s `$context`-substitution templates (`backend/app/prompts/*.txt`), dataclass-based service DTOs (see `DashboardService`, `WorkflowExecutionService`), `NotFoundError` for missing entities, the `redial-` `localStorage` key prefix (see `ThemeProvider`), and the single `frontend/src/styles/global.css` stylesheet (no CSS-in-JS).
- Run all backend commands from the project root using `.venv/bin/python -m pytest ...` (confirmed working invocation for this repo).

---

### Task 1: `GroqLLM.stream()` — the streaming provider method

**Files:**
- Modify: `backend/app/llm/base_llm.py`
- Modify: `backend/app/llm/providers/groq_provider.py`
- Test: `backend/tests/llm/__init__.py` (new, empty)
- Test: `backend/tests/llm/test_groq_provider_stream.py` (new)

**Interfaces:**
- Consumes: nothing new (existing `GroqLLM.__init__(settings=None, client=None)`, existing exception classes `AuthenticationError`, `ProviderTimeoutError`, `RateLimitError`, `ProviderUnavailableError` in `groq_provider.py`).
- Produces: `BaseLLM.stream(messages: Sequence[Mapping[str, str]], *, system_prompt: str | None = None, **options: Any) -> Iterator[str]` (abstract) and `GroqLLM.stream(...)` (concrete) — later tasks call `ai_service.llm.stream(messages, system_prompt=...)` and iterate it for content deltas.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/llm/__init__.py` (empty file).

Create `backend/tests/llm/test_groq_provider_stream.py`:

```python
"""Tests for GroqLLM.stream() — the Copilot's streaming code path.

Uses a fake Groq client (not a real network call) so these tests are fast,
deterministic, and never touch a real Groq account, matching how the rest
of this codebase avoids live third-party calls in tests.
"""

from __future__ import annotations

import httpx
import pytest
from groq import AuthenticationError as GroqAuthenticationError, RateLimitError as GroqRateLimitError

from backend.app.config.settings import Settings
from backend.app.llm.providers.groq_provider import AuthenticationError, GroqLLM, RateLimitError


class _FakeDelta:
    def __init__(self, content: str | None) -> None:
        self.content = content


class _FakeChoice:
    def __init__(self, content: str | None) -> None:
        self.delta = _FakeDelta(content)


class _FakeChunk:
    def __init__(self, content: str | None) -> None:
        self.choices = [_FakeChoice(content)]


class _FakeCompletions:
    def __init__(self, *, chunks: list[_FakeChunk] | None = None, error: Exception | None = None) -> None:
        self.chunks = chunks or []
        self.error = error
        self.last_kwargs: dict | None = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        if self.error is not None:
            raise self.error
        return iter(self.chunks)


class _FakeChat:
    def __init__(self, completions: _FakeCompletions) -> None:
        self.completions = completions


class _FakeGroqClient:
    def __init__(self, *, chunks: list[_FakeChunk] | None = None, error: Exception | None = None) -> None:
        self.chat = _FakeChat(_FakeCompletions(chunks=chunks, error=error))


def _make_llm(client: _FakeGroqClient) -> GroqLLM:
    settings = Settings(GROQ_API_KEY="test-key", GROQ_MODEL="test-model")
    return GroqLLM(settings=settings, client=client)


def test_stream_yields_only_non_empty_content_deltas_in_order() -> None:
    client = _FakeGroqClient(chunks=[_FakeChunk("Hello "), _FakeChunk("world"), _FakeChunk(None)])
    llm = _make_llm(client)

    deltas = list(llm.stream([{"role": "user", "content": "hi"}]))

    assert deltas == ["Hello ", "world"]


def test_stream_sends_system_prompt_as_first_message() -> None:
    client = _FakeGroqClient(chunks=[_FakeChunk("ok")])
    llm = _make_llm(client)

    list(llm.stream([{"role": "user", "content": "hi"}], system_prompt="be helpful"))

    sent_messages = client.chat.completions.last_kwargs["messages"]
    assert sent_messages[0] == {"role": "system", "content": "be helpful"}
    assert sent_messages[1] == {"role": "user", "content": "hi"}


def test_stream_requests_streaming_mode_from_the_sdk() -> None:
    client = _FakeGroqClient(chunks=[_FakeChunk("ok")])
    llm = _make_llm(client)

    list(llm.stream([{"role": "user", "content": "hi"}]))

    assert client.chat.completions.last_kwargs["stream"] is True


def test_stream_translates_rate_limit_error() -> None:
    request = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    response = httpx.Response(429, request=request)
    client = _FakeGroqClient(error=GroqRateLimitError("rate limited", response=response, body=None))
    llm = _make_llm(client)

    with pytest.raises(RateLimitError):
        list(llm.stream([{"role": "user", "content": "hi"}]))


def test_stream_translates_authentication_error() -> None:
    request = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    response = httpx.Response(401, request=request)
    client = _FakeGroqClient(error=GroqAuthenticationError("bad key", response=response, body=None))
    llm = _make_llm(client)

    with pytest.raises(AuthenticationError):
        list(llm.stream([{"role": "user", "content": "hi"}]))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest backend/tests/llm/test_groq_provider_stream.py -v`
Expected: FAIL — `AttributeError: 'GroqLLM' object has no attribute 'stream'` (or collection error if `BaseLLM` isn't imported yet — either way, failure, not pass).

- [ ] **Step 3: Implement `BaseLLM.stream()` and `GroqLLM.stream()`**

In `backend/app/llm/base_llm.py`, add the `collections.abc` import and the new abstract method:

```python
"""Provider-independent interface for future LLM adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator, Mapping, Sequence
from typing import Any


class BaseLLM(ABC):
    """Contract implemented by all synchronous LLM provider adapters.

    Provider-specific concerns such as SDK clients, authentication, retries,
    and model parameters belong in subclasses. Callers interact only with
    this interface and therefore do not depend on a particular LLM vendor.
    """

    @abstractmethod
    def generate(self, prompt: str, *, system_prompt: str | None = None, **options: Any) -> str:
        """Generate a raw text response for a fully rendered prompt."""

    @abstractmethod
    def stream(self, messages: Sequence[Mapping[str, str]], *, system_prompt: str | None = None, **options: Any) -> Iterator[str]:
        """Yield content deltas for a multi-turn conversation as they arrive."""

    @abstractmethod
    def health_check(self) -> bool:
        """Return whether the provider is reachable and ready to serve requests."""

    @abstractmethod
    def get_model_name(self) -> str:
        """Return the provider's configured model identifier for observability."""
```

In `backend/app/llm/providers/groq_provider.py`, add `Iterator, Mapping, Sequence` to the imports (the file currently has `from typing import Any` only — add a new import line above it):

```python
from collections.abc import Iterator, Mapping, Sequence
from time import perf_counter, sleep
from typing import Any
from uuid import uuid4
```

Then add the `stream` method to `GroqLLM`, directly after the existing `generate` method:

```python
    def stream(self, messages: Sequence[Mapping[str, str]], *, system_prompt: str | None = None, **options: Any) -> Iterator[str]:
        """Stream content deltas for a multi-turn conversation.

        Unlike ``generate``, this makes no retry attempt on transient failure
        once streaming has started — retrying a partially-yielded stream
        risks duplicating content the caller has already forwarded on.
        """
        trace_id = str(uuid4())
        started_at = perf_counter()
        client = self._client
        if client is None:
            raise ProviderUnavailableError("Groq client is not configured")
        chat_messages: list[ChatCompletionMessageParam] = []
        if system_prompt is not None:
            chat_messages.append({"role": "system", "content": system_prompt})
        chat_messages.extend({"role": message["role"], "content": message["content"]} for message in messages)
        request_options = {"model": self._model, "temperature": self.settings.LLM_TEMPERATURE, **options}
        log_request(trace_id=trace_id, prompt_name="groq.stream", provider="groq", model=self._model)

        try:
            stream = client.chat.completions.create(messages=chat_messages, stream=True, **request_options)
            for chunk in stream:
                delta = chunk.choices[0].delta.content if chunk.choices else None
                if delta:
                    yield delta
        except GroqAuthenticationError as exc:
            log_error(trace_id=trace_id, error="Groq authentication failed", provider="groq", model=self._model)
            raise AuthenticationError("Groq authentication failed") from exc
        except GroqAPITimeoutError as exc:
            self._log_failure(trace_id, started_at, 0, exc)
            raise ProviderTimeoutError("Groq request timed out") from exc
        except GroqRateLimitError as exc:
            self._log_failure(trace_id, started_at, 0, exc)
            raise RateLimitError("Groq rate limit exceeded") from exc
        except (GroqAPIConnectionError, GroqAPIStatusError) as exc:
            self._log_failure(trace_id, started_at, 0, exc)
            raise ProviderUnavailableError("Groq is temporarily unavailable") from exc
        except Exception as exc:
            self._log_failure(trace_id, started_at, 0, exc)
            raise ProviderUnavailableError("Groq streaming request failed") from exc
        else:
            latency_ms = (perf_counter() - started_at) * 1000
            log_response(trace_id=trace_id, latency_ms=latency_ms, success=True, provider="groq", model=self._model, retries=0)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest backend/tests/llm/test_groq_provider_stream.py -v`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/llm/base_llm.py backend/app/llm/providers/groq_provider.py backend/tests/llm/
git commit -m "feat: add streaming support to the LLM provider interface"
```

---

### Task 2: `MandateService.get_by_reference` + `context_builder.py`

**Files:**
- Modify: `backend/app/services/mandate_service.py`
- Create: `backend/app/copilot/__init__.py`
- Create: `backend/app/copilot/context_builder.py`
- Test: `backend/tests/services/test_mandate_service.py` (add two tests to the existing file)
- Test: `backend/tests/copilot/__init__.py` (new, empty)
- Test: `backend/tests/copilot/test_context_builder.py` (new)

**Interfaces:**
- Consumes: `DashboardService.get_summary(recent_decision_limit=)`, `.get_trend(days=)`; `MandateService.get_mandate`, `.list_mandates(customer_id=, limit=)`; `PaymentService.get_attempt`, `.list_attempts(mandate_id, limit=)`; `EscalationService.get_escalation`, `.list_open_escalations(mandate_id=None, limit=)`, `.list_resolved_escalations(mandate_id=None, limit=)`; `CommunicationService.list_communications(mandate_id=None, limit=)`; `DecisionService.get_latest_decision`, `.list_decisions(limit=)`; `WorkflowExecutionService.get_execution_detail`, `.get_overview()`, `.list_executions(limit=)`, `.get_provider_health()`, `.list_errors(limit=)`, `.get_metrics()`; `RetryService.list_pending_retries(limit=)`; `backend.app.core.exceptions.NotFoundError`.
- Produces: `ChatTurn(role: str, content: str)` (frozen dataclass), `CopilotContext(sources: list[str], data: dict[str, Any])`, `build_context(*, message, history, page_path, dashboard, mandates, payments, retries, escalations, communications, decisions, workflow_executions) -> CopilotContext` — Task 3 imports all three of these from `backend.app.copilot.context_builder`. Also `MandateService.get_by_reference(mandate_reference: str) -> Mandate | None`.

- [ ] **Step 1: Write the failing tests**

Add to `backend/tests/services/test_mandate_service.py` (append at the end of the file — check the file's existing imports first; it already imports `Decimal` and `MandateService` given the existing test suite pattern):

```python
def test_get_by_reference_returns_the_matching_mandate(db_session: Session) -> None:
    service = MandateService(db_session)
    created = service.register_mandate("cust-1", "REF-42", Decimal("500.00"))

    found = service.get_by_reference("REF-42")

    assert found is not None
    assert found.id == created.id


def test_get_by_reference_returns_none_when_no_mandate_matches(db_session: Session) -> None:
    service = MandateService(db_session)

    assert service.get_by_reference("does-not-exist") is None
```

Create `backend/tests/copilot/__init__.py` (empty file).

Create `backend/tests/copilot/test_context_builder.py`:

```python
"""Tests for the Copilot's deterministic, keyword- and entity-driven context assembly.

No LLM involvement in this module or these tests — build_context is pure
Python over the real service layer, backed by a real (SQLite) database per
test via the shared `db_session` fixture.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from backend.app.copilot.context_builder import build_context
from backend.app.services.communication_service import CommunicationService
from backend.app.services.dashboard_service import DashboardService
from backend.app.services.decision_service import DecisionService
from backend.app.services.escalation_service import EscalationService
from backend.app.services.mandate_service import MandateService
from backend.app.services.payment_service import PaymentService
from backend.app.services.retry_service import RetryService
from backend.app.services.workflow_execution_service import WorkflowExecutionService


def _services(db_session: Session) -> dict:
    return {
        "dashboard": DashboardService(
            mandate_service=MandateService(db_session),
            payment_service=PaymentService(db_session),
            retry_service=RetryService(db_session),
            escalation_service=EscalationService(db_session),
            decision_service=DecisionService(db_session),
        ),
        "mandates": MandateService(db_session),
        "payments": PaymentService(db_session),
        "retries": RetryService(db_session),
        "escalations": EscalationService(db_session),
        "communications": CommunicationService(db_session),
        "decisions": DecisionService(db_session),
        "workflow_executions": WorkflowExecutionService(db_session),
    }


def test_dashboard_summary_is_always_included(db_session: Session) -> None:
    context = build_context(message="hello", history=[], page_path=None, **_services(db_session))

    assert "dashboard_summary" in context.data
    assert any("Dashboard summary" in source for source in context.sources)


def test_mandate_reference_in_message_pulls_full_mandate_detail(db_session: Session) -> None:
    services = _services(db_session)
    mandate = services["mandates"].register_mandate("cust-1", "REF-42", Decimal("500.00"))
    services["payments"].record_payment_attempt(mandate.id, amount=Decimal("500.00"))

    context = build_context(message="Why was REF-42 retried?", history=[], page_path=None, **services)

    assert context.data["mandate"]["mandate_reference"] == "REF-42"
    assert len(context.data["mandate"]["payment_attempts"]) == 1
    assert any("REF-42" in source for source in context.sources)


def test_unknown_mandate_reference_is_reported_as_not_found_not_fabricated(db_session: Session) -> None:
    services = _services(db_session)

    context = build_context(message="What happened to REF-999?", history=[], page_path=None, **services)

    assert any("not found" in source for source in context.sources)
    assert "mandate" not in context.data


def test_trend_keyword_adds_the_payment_trend(db_session: Session) -> None:
    services = _services(db_session)

    context = build_context(message="Show payment success trends", history=[], page_path=None, **services)

    assert "payment_trend" in context.data


def test_escalation_keyword_adds_open_escalations(db_session: Session) -> None:
    services = _services(db_session)
    mandate = services["mandates"].register_mandate("cust-1", "REF-1", Decimal("500.00"))
    services["escalations"].create_escalation(mandate.id, "Needs manual review")

    context = build_context(message="Which mandates need attention?", history=[], page_path=None, **services)

    assert len(context.data["open_escalations"]) == 1


def test_page_path_is_recorded_only_when_no_entity_matched(db_session: Session) -> None:
    services = _services(db_session)

    context = build_context(message="what should I look at?", history=[], page_path="/escalations", **services)

    assert context.data["current_page"] == "/escalations"


def test_page_path_is_not_recorded_when_an_entity_already_matched(db_session: Session) -> None:
    services = _services(db_session)
    services["mandates"].register_mandate("cust-1", "REF-7", Decimal("500.00"))

    context = build_context(message="status of REF-7", history=[], page_path="/escalations", **services)

    assert "current_page" not in context.data
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest backend/tests/services/test_mandate_service.py backend/tests/copilot/test_context_builder.py -v`
Expected: FAIL — `AttributeError: 'MandateService' object has no attribute 'get_by_reference'` and `ModuleNotFoundError: No module named 'backend.app.copilot'`.

- [ ] **Step 3: Implement `MandateService.get_by_reference` and `context_builder.py`**

In `backend/app/services/mandate_service.py`, add this method directly after `get_mandate`:

```python
    def get_by_reference(self, mandate_reference: str) -> Mandate | None:
        """Return a mandate by its external reference, or None if none exists."""
        return self.mandates.get_by_reference(mandate_reference)
```

Create `backend/app/copilot/__init__.py` (empty file).

Create `backend/app/copilot/context_builder.py`:

```python
"""Deterministic, keyword- and entity-driven context assembly for the Copilot.

No LLM involvement here — this module decides, in plain Python, which of the
existing read-only services to call for a given question. Every fetch is
capped and every miss becomes a "not found" source entry instead of a
silent no-op, so the caller can honestly tell the model what real data is
and isn't available (see the ``copilot_system`` prompt template).
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from typing import Any

from backend.app.core.exceptions import NotFoundError
from backend.app.models.communication import Communication
from backend.app.models.decision_log import DecisionLog
from backend.app.models.escalation import Escalation
from backend.app.models.mandate import Mandate
from backend.app.models.payment_attempt import PaymentAttempt
from backend.app.services.communication_service import CommunicationService
from backend.app.services.dashboard_service import DashboardService
from backend.app.services.decision_service import DecisionService
from backend.app.services.escalation_service import EscalationService
from backend.app.services.mandate_service import MandateService
from backend.app.services.payment_service import PaymentService
from backend.app.services.retry_service import RetryService
from backend.app.services.workflow_execution_service import WorkflowExecutionService

_UUID_RE = re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b")
_REFERENCE_TOKEN_RE = re.compile(r"\b[A-Za-z]{2,}-[A-Za-z0-9-]{1,}\b")
_CUSTOMER_MENTION_RE = re.compile(r"customer[s]?\s+([A-Za-z0-9_-]{2,})", re.IGNORECASE)

_TOPIC_KEYWORDS: dict[str, tuple[str, ...]] = {
    "trend": ("trend", "success rate", "today", "summar"),
    "workflow": ("workflow", "execution", "slowest", "longest"),
    "escalation": ("escalat", "risk", "attention", "priorit"),
    "observability": ("anomal", "error", "provider", "health", "observab"),
    "communication": ("communicat", "sms", "email", "whatsapp", "message"),
    "retry": ("retry", "retries", "queue"),
    "decision": ("decision", "recommend", "confidence"),
}


@dataclass(frozen=True)
class ChatTurn:
    """One prior turn of the conversation, as sent by the frontend."""

    role: str  # "user" | "assistant"
    content: str


@dataclass
class CopilotContext:
    """The real data assembled for one question, plus a human-readable trail of where it came from."""

    sources: list[str] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)


def build_context(
    *,
    message: str,
    history: list[ChatTurn],
    page_path: str | None,
    dashboard: DashboardService,
    mandates: MandateService,
    payments: PaymentService,
    retries: RetryService,
    escalations: EscalationService,
    communications: CommunicationService,
    decisions: DecisionService,
    workflow_executions: WorkflowExecutionService,
) -> CopilotContext:
    """Assemble the minimal, real-data context needed to answer one question."""
    context = CopilotContext()
    _add_dashboard_summary(context, dashboard)

    search_text = message if message.strip() else _last_user_turn(history)
    matched_entity = _add_entity_matches(
        context,
        search_text,
        mandates=mandates,
        payments=payments,
        escalations=escalations,
        workflow_executions=workflow_executions,
        communications=communications,
        decisions=decisions,
    )

    lowered = search_text.lower()
    if _matches_topic(lowered, "trend"):
        _add_trend(context, dashboard, days=7 if "today" in lowered else 14)
    if _matches_topic(lowered, "workflow"):
        _add_workflow_overview(context, workflow_executions)
    if _matches_topic(lowered, "escalation"):
        _add_open_escalations(context, escalations)
    if _matches_topic(lowered, "observability"):
        _add_observability(context, workflow_executions)
    if _matches_topic(lowered, "communication"):
        _add_recent_communications(context, communications)
    if _matches_topic(lowered, "retry"):
        _add_pending_retries(context, retries)
    if _matches_topic(lowered, "decision"):
        _add_recent_decisions(context, decisions)

    if page_path and not matched_entity:
        context.data["current_page"] = page_path
        context.sources.append(f"Operator is currently viewing {page_path}")

    return context


def _last_user_turn(history: list[ChatTurn]) -> str:
    for turn in reversed(history):
        if turn.role == "user":
            return turn.content
    return ""


def _matches_topic(lowered_text: str, topic: str) -> bool:
    return any(keyword in lowered_text for keyword in _TOPIC_KEYWORDS[topic])


def _add_dashboard_summary(context: CopilotContext, dashboard: DashboardService) -> None:
    summary = dashboard.get_summary(recent_decision_limit=5)
    context.data["dashboard_summary"] = {
        "mandate_counts_by_status": {status.value: count for status, count in summary.mandate_counts_by_status.items()},
        "payment_attempt_counts_by_status": {status.value: count for status, count in summary.payment_attempt_counts_by_status.items()},
        "revenue_recovered": str(summary.revenue_recovered),
        "pending_retries": summary.pending_retries,
        "open_escalations": summary.open_escalations,
        "recent_decisions": [_decision_dict(decision) for decision in summary.recent_decisions],
    }
    context.sources.append(
        f"Dashboard summary ({summary.pending_retries} pending retries, {summary.open_escalations} open escalations, "
        f"{summary.revenue_recovered} revenue recovered)"
    )


def _add_entity_matches(
    context: CopilotContext,
    text: str,
    *,
    mandates: MandateService,
    payments: PaymentService,
    escalations: EscalationService,
    workflow_executions: WorkflowExecutionService,
    communications: CommunicationService,
    decisions: DecisionService,
) -> bool:
    for token in _UUID_RE.findall(text):
        candidate_id = uuid.UUID(token)

        try:
            mandate = mandates.get_mandate(candidate_id)
            _add_mandate_detail(context, mandate, payments=payments, decisions=decisions, communications=communications, escalations=escalations)
            return True
        except NotFoundError:
            pass

        try:
            attempt = payments.get_attempt(candidate_id)
            mandate = mandates.get_mandate(attempt.mandate_id)
            _add_mandate_detail(context, mandate, payments=payments, decisions=decisions, communications=communications, escalations=escalations)
            return True
        except NotFoundError:
            pass

        try:
            escalation = escalations.get_escalation(candidate_id)
            mandate = mandates.get_mandate(escalation.mandate_id)
            _add_mandate_detail(context, mandate, payments=payments, decisions=decisions, communications=communications, escalations=escalations)
            return True
        except NotFoundError:
            pass

        try:
            detail = workflow_executions.get_execution_detail(candidate_id)
            context.data["workflow_execution"] = {
                "id": str(detail.summary.id),
                "workflow_id": detail.summary.workflow_id,
                "status": detail.summary.status,
                "duration_ms": detail.summary.duration_ms,
                "reasoning": detail.reasoning,
                "error_message": detail.error_message,
                "failed_node": detail.failed_node,
            }
            context.sources.append(f"Workflow execution {detail.summary.workflow_id}")
            return True
        except NotFoundError:
            pass

    reference_tokens = _REFERENCE_TOKEN_RE.findall(text)
    for token in reference_tokens:
        mandate = mandates.get_by_reference(token)
        if mandate is not None:
            _add_mandate_detail(context, mandate, payments=payments, decisions=decisions, communications=communications, escalations=escalations)
            return True
    if reference_tokens:
        context.sources.append(f"Mandate reference '{reference_tokens[0]}': not found")

    customer_match = _CUSTOMER_MENTION_RE.search(text)
    if customer_match:
        customer_id = customer_match.group(1)
        customer_mandates = mandates.list_mandates(customer_id=customer_id, limit=10)
        if customer_mandates:
            context.data["customer_mandates"] = [_mandate_dict(item) for item in customer_mandates]
            context.sources.append(f"Mandates for customer {customer_id} ({len(customer_mandates)})")
            return True
        context.sources.append(f"Customer {customer_id}: no mandates found")

    return False


def _add_mandate_detail(
    context: CopilotContext,
    mandate: Mandate,
    *,
    payments: PaymentService,
    decisions: DecisionService,
    communications: CommunicationService,
    escalations: EscalationService,
) -> None:
    attempts = payments.list_attempts(mandate.id, limit=10)
    latest_decision = decisions.get_latest_decision(mandate.id)
    mandate_communications = communications.list_communications(mandate.id, limit=10)
    mandate_escalations = escalations.list_open_escalations(mandate.id, limit=10) + escalations.list_resolved_escalations(mandate.id, limit=5)

    context.data["mandate"] = {
        **_mandate_dict(mandate),
        "payment_attempts": [_payment_dict(attempt) for attempt in attempts],
        "latest_decision": _decision_dict(latest_decision) if latest_decision else None,
        "communications": [_communication_dict(item) for item in mandate_communications],
        "escalations": [_escalation_dict(item) for item in mandate_escalations],
    }
    context.sources.append(f"Mandate {mandate.mandate_reference} (customer {mandate.customer_id})")


def _add_trend(context: CopilotContext, dashboard: DashboardService, *, days: int) -> None:
    trend = dashboard.get_trend(days=days)
    context.data["payment_trend"] = [
        {
            "day": point.day.isoformat(),
            "attempts_total": point.attempts_total,
            "attempts_succeeded": point.attempts_succeeded,
            "attempts_failed": point.attempts_failed,
            "collected_amount": str(point.collected_amount),
            "recovered_amount": str(point.recovered_amount),
        }
        for point in trend
    ]
    context.sources.append(f"{days}-day payment trend")


def _add_workflow_overview(context: CopilotContext, workflow_executions: WorkflowExecutionService) -> None:
    overview = workflow_executions.get_overview()
    recent = workflow_executions.list_executions(limit=10)
    context.data["workflow_overview"] = {
        "workflows_executed": overview.workflows_executed,
        "successful_workflows": overview.successful_workflows,
        "failed_workflows": overview.failed_workflows,
        "average_execution_time_ms": overview.average_execution_time_ms,
        "average_confidence": overview.average_confidence,
    }
    context.data["recent_workflow_executions"] = [
        {"id": str(item.id), "workflow_id": item.workflow_id, "status": item.status, "duration_ms": item.duration_ms, "started_at": item.started_at.isoformat()}
        for item in recent
    ]
    context.sources.append(f"Workflow execution overview ({overview.workflows_executed} runs)")


def _add_open_escalations(context: CopilotContext, escalations: EscalationService) -> None:
    open_escalations = escalations.list_open_escalations(limit=15)
    context.data["open_escalations"] = [_escalation_dict(item) for item in open_escalations]
    context.sources.append(f"Open escalations ({len(open_escalations)})")


def _add_observability(context: CopilotContext, workflow_executions: WorkflowExecutionService) -> None:
    provider_health = workflow_executions.get_provider_health()
    errors = workflow_executions.list_errors(limit=10)
    metrics = workflow_executions.get_metrics()
    context.data["provider_health"] = [
        {"provider": item.provider, "model": item.model, "status": item.status, "requests_today": item.requests_today, "failures": item.failures}
        for item in provider_health
    ]
    context.data["recent_errors"] = [
        {"workflow_id": item.workflow_id, "mandate_id": str(item.mandate_id), "node": item.node, "exception": item.exception, "timestamp": item.timestamp.isoformat()}
        for item in errors
    ]
    context.data["observability_metrics"] = {
        "average_workflow_duration_ms": metrics.average_workflow_duration_ms,
        "average_node_duration_ms": metrics.average_node_duration_ms,
    }
    context.sources.append(f"Observability (provider health, {len(errors)} recent errors)")


def _add_recent_communications(context: CopilotContext, communications: CommunicationService) -> None:
    recent = communications.list_communications(limit=15)
    context.data["recent_communications"] = [_communication_dict(item) for item in recent]
    context.sources.append(f"Recent communications ({len(recent)})")


def _add_pending_retries(context: CopilotContext, retries: RetryService) -> None:
    pending = retries.list_pending_retries(limit=15)
    context.data["pending_retries"] = [
        {
            "id": str(item.id),
            "mandate_id": str(item.mandate_id),
            "retry_strategy": item.retry_strategy,
            "recommended_time": item.recommended_time.isoformat(),
            "status": item.status.value,
        }
        for item in pending
    ]
    context.sources.append(f"Pending retries ({len(pending)})")


def _add_recent_decisions(context: CopilotContext, decisions: DecisionService) -> None:
    recent = decisions.list_decisions(limit=15)
    context.data["recent_decisions_detail"] = [_decision_dict(item) for item in recent]
    context.sources.append(f"Recent AI decisions ({len(recent)})")


def _mandate_dict(mandate: Mandate) -> dict[str, Any]:
    return {
        "id": str(mandate.id),
        "customer_id": mandate.customer_id,
        "mandate_reference": mandate.mandate_reference,
        "amount": str(mandate.amount),
        "currency": mandate.currency,
        "status": mandate.status.value,
        "created_at": mandate.created_at.isoformat(),
    }


def _payment_dict(attempt: PaymentAttempt) -> dict[str, Any]:
    return {
        "id": str(attempt.id),
        "attempt_number": attempt.attempt_number,
        "attempted_at": attempt.attempted_at.isoformat(),
        "amount": str(attempt.amount),
        "status": attempt.status.value,
        "decline_category": attempt.decline_category.value if attempt.decline_category else None,
        "bank_response_message": attempt.bank_response_message,
        "ai_reasoning": attempt.ai_reasoning,
    }


def _escalation_dict(escalation: Escalation) -> dict[str, Any]:
    return {
        "id": str(escalation.id),
        "mandate_id": str(escalation.mandate_id),
        "escalation_level": escalation.escalation_level.value,
        "reason": escalation.reason,
        "resolved": escalation.resolved,
        "assigned_to": escalation.assigned_to,
    }


def _communication_dict(communication: Communication) -> dict[str, Any]:
    return {
        "id": str(communication.id),
        "mandate_id": str(communication.mandate_id),
        "channel": communication.channel.value,
        "message": communication.message,
        "sent_at": communication.sent_at.isoformat(),
        "delivery_status": communication.delivery_status.value,
    }


def _decision_dict(decision: DecisionLog) -> dict[str, Any]:
    return {
        "id": str(decision.id),
        "mandate_id": str(decision.mandate_id),
        "decision_type": decision.decision_type,
        "explanation": decision.explanation,
        "confidence_score": str(decision.confidence_score),
        "created_at": decision.created_at.isoformat(),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest backend/tests/services/test_mandate_service.py backend/tests/copilot/test_context_builder.py -v`
Expected: all passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/mandate_service.py backend/app/copilot/ backend/tests/services/test_mandate_service.py backend/tests/copilot/
git commit -m "feat: add deterministic Copilot context assembly over existing services"
```

---

### Task 3: `CopilotService` + system prompt template

**Files:**
- Create: `backend/app/prompts/copilot_system.txt`
- Create: `backend/app/copilot/service.py`
- Test: `backend/tests/copilot/test_service.py` (new)

**Interfaces:**
- Consumes: `ChatTurn`, `CopilotContext`, `build_context` from `backend.app.copilot.context_builder` (Task 2); `AIService` (has public `.llm: BaseLLM | None` and `.recorder: AITraceRecorder | None`, from `backend.app.llm.ai_service`); `BaseLLM.stream(...)` (Task 1); `backend.app.llm.providers.{ProviderError, AuthenticationError, ProviderTimeoutError, RateLimitError}`; `backend.app.observability.metrics.{record_latency, record_success, record_failure}`; `backend.app.prompts.manager.prompt_manager.render_prompt(name, **kwargs)`.
- Produces: `CopilotEvent(type: Literal["sources","delta","error","done"], content: str | None = None, items: list[str] | None = None, message: str | None = None)` (frozen dataclass) and `CopilotService(*, ai_service, dashboard, mandates, payments, retries, escalations, communications, decisions, workflow_executions).stream_reply(*, message: str, history: list[ChatTurn], page_path: str | None) -> Iterator[CopilotEvent]` — Task 4 imports both from `backend.app.copilot.service` and Task 5 (dependency wiring) constructs `CopilotService` with these exact keyword arguments.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/copilot/test_service.py`:

```python
"""Tests for CopilotService.stream_reply's event sequencing and error handling.

Uses a fake BaseLLM (not a real Groq call) so these tests are fast and
deterministic — GroqLLM.stream() itself is covered in test_groq_provider_stream.py.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from backend.app.copilot.service import CopilotEvent, CopilotService
from backend.app.llm.ai_service import AIService
from backend.app.llm.providers import ProviderTimeoutError
from backend.app.observability.ai_trace import AITraceRecorder
from backend.app.services.communication_service import CommunicationService
from backend.app.services.dashboard_service import DashboardService
from backend.app.services.decision_service import DecisionService
from backend.app.services.escalation_service import EscalationService
from backend.app.services.mandate_service import MandateService
from backend.app.services.payment_service import PaymentService
from backend.app.services.retry_service import RetryService
from backend.app.services.workflow_execution_service import WorkflowExecutionService


class _FakeLLM:
    provider = "fake"

    def __init__(self, chunks: list[str] | None = None, error: Exception | None = None) -> None:
        self._chunks = chunks or []
        self._error = error

    def get_model_name(self) -> str:
        return "fake-model"

    def stream(self, messages, *, system_prompt=None, **options):
        if self._error is not None:
            raise self._error
        yield from self._chunks

    def generate(self, prompt, *, system_prompt=None, **options):  # pragma: no cover - unused by the Copilot
        raise NotImplementedError

    def health_check(self) -> bool:  # pragma: no cover - unused by the Copilot
        return True


def _build_service(db_session: Session, *, llm=None) -> CopilotService:
    ai_service = AIService(llm=llm, recorder=AITraceRecorder()) if llm is not None else None
    return CopilotService(
        ai_service=ai_service,
        dashboard=DashboardService(
            mandate_service=MandateService(db_session),
            payment_service=PaymentService(db_session),
            retry_service=RetryService(db_session),
            escalation_service=EscalationService(db_session),
            decision_service=DecisionService(db_session),
        ),
        mandates=MandateService(db_session),
        payments=PaymentService(db_session),
        retries=RetryService(db_session),
        escalations=EscalationService(db_session),
        communications=CommunicationService(db_session),
        decisions=DecisionService(db_session),
        workflow_executions=WorkflowExecutionService(db_session),
    )


def test_stream_reply_yields_only_sources_then_error_when_ai_unavailable(db_session: Session) -> None:
    service = _build_service(db_session, llm=None)

    events = list(service.stream_reply(message="Summarize today", history=[], page_path=None))

    assert [event.type for event in events] == ["sources", "error"]
    assert events[-1].message is not None


def test_stream_reply_yields_deltas_then_done_on_success(db_session: Session) -> None:
    service = _build_service(db_session, llm=_FakeLLM(chunks=["Hello ", "operator."]))

    events = list(service.stream_reply(message="Summarize today", history=[], page_path=None))

    assert [event.type for event in events] == ["sources", "delta", "delta", "done"]
    assert [event.content for event in events if event.type == "delta"] == ["Hello ", "operator."]


def test_stream_reply_yields_terminal_error_on_provider_failure(db_session: Session) -> None:
    service = _build_service(db_session, llm=_FakeLLM(error=ProviderTimeoutError("timed out")))

    events = list(service.stream_reply(message="Summarize today", history=[], page_path=None))

    assert [event.type for event in events] == ["sources", "error"]
    assert "long" in events[-1].message.lower() or "time" in events[-1].message.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest backend/tests/copilot/test_service.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'backend.app.copilot.service'`.

- [ ] **Step 3: Implement the prompt template and `CopilotService`**

Create `backend/app/prompts/copilot_system.txt`:

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

Create `backend/app/copilot/service.py`:

```python
"""Orchestrates context assembly and Groq streaming for the AI Operations Copilot."""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Literal

from backend.app.copilot.context_builder import ChatTurn, build_context
from backend.app.llm.ai_service import AIService
from backend.app.llm.providers import AuthenticationError, ProviderError, ProviderTimeoutError, RateLimitError
from backend.app.observability.logger import log_error
from backend.app.observability.metrics import record_failure, record_latency, record_success
from backend.app.prompts.manager import prompt_manager
from backend.app.services.communication_service import CommunicationService
from backend.app.services.dashboard_service import DashboardService
from backend.app.services.decision_service import DecisionService
from backend.app.services.escalation_service import EscalationService
from backend.app.services.mandate_service import MandateService
from backend.app.services.payment_service import PaymentService
from backend.app.services.retry_service import RetryService
from backend.app.services.workflow_execution_service import WorkflowExecutionService

CopilotEventType = Literal["sources", "delta", "error", "done"]


@dataclass(frozen=True)
class CopilotEvent:
    """One frame of the Copilot's SSE response."""

    type: CopilotEventType
    content: str | None = None
    items: list[str] | None = None
    message: str | None = None


_UNAVAILABLE_MESSAGE = (
    "The AI assistant isn't configured right now (no LLM provider available). "
    "Operational data is still fully available across the dashboard."
)


class CopilotService:
    """Assembles real-data context, then streams a grounded Groq reply."""

    def __init__(
        self,
        *,
        ai_service: AIService | None,
        dashboard: DashboardService,
        mandates: MandateService,
        payments: PaymentService,
        retries: RetryService,
        escalations: EscalationService,
        communications: CommunicationService,
        decisions: DecisionService,
        workflow_executions: WorkflowExecutionService,
    ) -> None:
        self.ai_service = ai_service
        self.dashboard = dashboard
        self.mandates = mandates
        self.payments = payments
        self.retries = retries
        self.escalations = escalations
        self.communications = communications
        self.decisions = decisions
        self.workflow_executions = workflow_executions

    def stream_reply(self, *, message: str, history: list[ChatTurn], page_path: str | None) -> Iterator[CopilotEvent]:
        context = build_context(
            message=message,
            history=history,
            page_path=page_path,
            dashboard=self.dashboard,
            mandates=self.mandates,
            payments=self.payments,
            retries=self.retries,
            escalations=self.escalations,
            communications=self.communications,
            decisions=self.decisions,
            workflow_executions=self.workflow_executions,
        )
        yield CopilotEvent(type="sources", items=context.sources)

        if self.ai_service is None or self.ai_service.llm is None:
            yield CopilotEvent(type="error", message=_UNAVAILABLE_MESSAGE)
            return

        system_prompt = prompt_manager.render_prompt(
            "copilot_system",
            context=json.dumps(context.data, ensure_ascii=False, default=str, indent=2),
        )
        messages = [{"role": turn.role, "content": turn.content} for turn in history] + [{"role": "user", "content": message}]

        recorder = self.ai_service.recorder
        trace = (
            recorder.start_trace(provider=self.ai_service.llm.provider, model=self.ai_service.llm.get_model_name(), prompt_name="copilot_chat", prompt=system_prompt)
            if recorder
            else None
        )

        collected: list[str] = []
        try:
            for delta in self.ai_service.llm.stream(messages, system_prompt=system_prompt):
                collected.append(delta)
                yield CopilotEvent(type="delta", content=delta)
        except ProviderError as exc:
            if trace is not None and recorder is not None:
                recorder.record_failure(trace, exc)
            record_failure()
            log_error(trace_id=trace.trace_id if trace else "unknown", error=exc)
            yield CopilotEvent(type="error", message=_friendly_provider_message(exc))
            return

        if trace is not None and recorder is not None:
            finished = recorder.finish_trace(trace, response="".join(collected))
            record_latency(finished.latency_ms or 0.0)
        record_success()
        yield CopilotEvent(type="done")


def _friendly_provider_message(exc: ProviderError) -> str:
    if isinstance(exc, AuthenticationError):
        return "The AI provider rejected our credentials. Please check the Groq API key configuration."
    if isinstance(exc, RateLimitError):
        return "The AI provider is rate-limited right now. Please try again in a moment."
    if isinstance(exc, ProviderTimeoutError):
        return "The AI provider took too long to respond. Please try again."
    return "The AI assistant is temporarily unavailable. Please try again shortly."
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest backend/tests/copilot/ -v`
Expected: all passed (context_builder tests from Task 2 plus the new service tests).

- [ ] **Step 5: Commit**

```bash
git add backend/app/prompts/copilot_system.txt backend/app/copilot/service.py backend/tests/copilot/test_service.py
git commit -m "feat: add CopilotService orchestrating context assembly and Groq streaming"
```

---

### Task 4: API route + dependency wiring

**Files:**
- Create: `backend/app/api/routes/copilot.py`
- Modify: `backend/app/api/dependencies.py`
- Modify: `backend/app/api/router.py`
- Test: `backend/tests/api/test_copilot_api.py` (new)

**Interfaces:**
- Consumes: `CopilotEvent`, `CopilotService` from `backend.app.copilot.service` (Task 3); `ChatTurn` from `backend.app.copilot.context_builder` (Task 2); existing `get_db`, `get_ai_service` dependencies.
- Produces: `POST /api/v1/copilot/chat` (SSE `text/event-stream`); `get_copilot_service(db=Depends(get_db), ai_service=Depends(get_ai_service)) -> CopilotService` dependency, usable by any future route.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/api/test_copilot_api.py`:

```python
"""API tests for POST /api/v1/copilot/chat — the SSE streaming contract.

`client` (from conftest.py) already overrides get_ai_service -> None, so the
"AI unavailable" path is exercised with zero extra setup — exactly the
honest-degradation behavior the Copilot must have when no provider is
configured. The "AI available" path overrides get_ai_service locally with a
fake streaming LLM, following the same dependency-override pattern.
"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from backend.app.api.dependencies import get_ai_service
from backend.app.llm.ai_service import AIService
from backend.app.main import app


def _parse_sse(body: str) -> list[dict]:
    events = []
    for frame in body.split("\n\n"):
        frame = frame.strip()
        if not frame:
            continue
        for line in frame.splitlines():
            if line.startswith("data: "):
                events.append(json.loads(line[len("data: "):]))
    return events


def test_chat_streams_sources_then_error_when_ai_unavailable(client: TestClient) -> None:
    response = client.post(
        "/api/v1/copilot/chat",
        json={"message": "Summarize today's activity", "history": [], "page_path": "/dashboard"},
    )

    assert response.status_code == 200
    events = _parse_sse(response.text)
    assert events[0]["type"] == "sources"
    assert len(events[0]["items"]) >= 1
    assert events[-1]["type"] == "error"


class _FakeStreamingLLM:
    provider = "fake"

    def get_model_name(self) -> str:
        return "fake-model"

    def stream(self, messages, *, system_prompt=None, **options):
        yield "Hello "
        yield "operator."

    def generate(self, prompt, *, system_prompt=None, **options):  # pragma: no cover - unused by the Copilot
        raise NotImplementedError

    def health_check(self) -> bool:  # pragma: no cover - unused by the Copilot
        return True


def test_chat_streams_deltas_then_done_when_ai_available(client: TestClient) -> None:
    app.dependency_overrides[get_ai_service] = lambda: AIService(llm=_FakeStreamingLLM())
    try:
        response = client.post(
            "/api/v1/copilot/chat",
            json={"message": "Summarize today's activity", "history": [], "page_path": "/dashboard"},
        )
    finally:
        app.dependency_overrides[get_ai_service] = lambda: None

    assert response.status_code == 200
    events = _parse_sse(response.text)
    assert events[0]["type"] == "sources"
    deltas = [event["content"] for event in events if event["type"] == "delta"]
    assert deltas == ["Hello ", "operator."]
    assert events[-1] == {"type": "done"}


def test_chat_rejects_an_empty_message(client: TestClient) -> None:
    response = client.post("/api/v1/copilot/chat", json={"message": "", "history": [], "page_path": None})

    assert response.status_code == 422
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest backend/tests/api/test_copilot_api.py -v`
Expected: FAIL — 404s (`copilot` route not registered) / import errors.

- [ ] **Step 3: Implement the route and wiring**

Create `backend/app/api/routes/copilot.py`:

```python
"""SSE endpoint for the AI Operations Copilot — streams grounded, real-data answers."""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import asdict
from typing import Literal

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.app.api.dependencies import get_copilot_service
from backend.app.copilot.context_builder import ChatTurn
from backend.app.copilot.service import CopilotEvent, CopilotService

router = APIRouter(prefix="/copilot", tags=["Copilot"])

_MAX_HISTORY_TURNS = 10


class ChatTurnRequest(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=8_000)


class CopilotChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4_000)
    history: list[ChatTurnRequest] = Field(default_factory=list)
    page_path: str | None = None


def _serialize(event: CopilotEvent) -> str:
    payload = {key: value for key, value in asdict(event).items() if value is not None}
    return f"data: {json.dumps(payload)}\n\n"


def _stream(service: CopilotService, request: CopilotChatRequest) -> Iterator[str]:
    history = [ChatTurn(role=turn.role, content=turn.content) for turn in request.history[-_MAX_HISTORY_TURNS:]]
    for event in service.stream_reply(message=request.message, history=history, page_path=request.page_path):
        yield _serialize(event)


@router.post("/chat")
def chat(request: CopilotChatRequest, service: CopilotService = Depends(get_copilot_service)) -> StreamingResponse:
    return StreamingResponse(_stream(service, request), media_type="text/event-stream")
```

In `backend/app/api/dependencies.py`, add the import and the dependency function. Add `CopilotService` to the imports near the top (alongside the other service imports):

```python
from backend.app.copilot.service import CopilotService
```

Then add this function after `get_workflow_runner_service` (before `get_workflow`):

```python
def get_copilot_service(db: Session = Depends(get_db), ai_service: AIService | None = Depends(get_ai_service)) -> CopilotService:
    """Provide one Copilot service composing the same per-request services the dashboard uses."""
    return CopilotService(
        ai_service=ai_service,
        dashboard=DashboardService(
            mandate_service=MandateService(db),
            payment_service=PaymentService(db),
            retry_service=RetryService(db),
            escalation_service=EscalationService(db),
            decision_service=DecisionService(db),
        ),
        mandates=MandateService(db),
        payments=PaymentService(db),
        retries=RetryService(db),
        escalations=EscalationService(db),
        communications=CommunicationService(db),
        decisions=DecisionService(db),
        workflow_executions=WorkflowExecutionService(db),
    )
```

In `backend/app/api/router.py`, add `copilot` to the routes import and register it:

```python
from backend.app.api.routes import (
    communications,
    copilot,
    dashboard,
    decisions,
    dev_seed,
    dev_workflow,
    escalations,
    health,
    mandates,
    observability,
    payments,
    retry_schedules,
    webhooks,
    workflow,
)
```

```python
api_router.include_router(copilot.router, prefix="/api/v1")
```

(Add this line alongside the other `api_router.include_router(...)` calls, e.g. right after the `observability.router` line.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest backend/tests/api/test_copilot_api.py -v`
Expected: 3 passed.

Then run the full backend suite to confirm nothing else broke:

Run: `.venv/bin/python -m pytest backend/tests/ -v`
Expected: all passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/routes/copilot.py backend/app/api/dependencies.py backend/app/api/router.py backend/tests/api/test_copilot_api.py
git commit -m "feat: add POST /api/v1/copilot/chat SSE endpoint"
```

---

### Task 5: Frontend types + SSE client (`copilotApi.ts`)

**Files:**
- Create: `frontend/src/types/copilot.ts`
- Create: `frontend/src/services/copilotApi.ts`

**Interfaces:**
- Consumes: `VITE_API_URL` env var (existing convention, see `frontend/src/services/api.ts`).
- Produces: `CopilotRole = 'user' | 'assistant'`; `CopilotMessage { id, role: CopilotRole | 'error', content, sources: string[], createdAt: string, pending: boolean }`; `CopilotChatTurn { role: CopilotRole, content: string }`; `CopilotStreamEvent` discriminated union; `streamCopilotChat(params: { message: string; history: CopilotChatTurn[]; pagePath: string }, onEvent: (event: CopilotStreamEvent) => void, signal: AbortSignal): Promise<void>` — Task 6's `useCopilotChat` hook imports and calls this directly.

No backend test runner applies here (frontend has none) — this task is verified by `tsc` in Task 8's final check plus manual exercise once the UI exists (Task 8/9). Write the files directly.

- [ ] **Step 1: Create the type definitions**

Create `frontend/src/types/copilot.ts`:

```typescript
export type CopilotRole = 'user' | 'assistant'

export interface CopilotMessage {
  id: string
  role: CopilotRole | 'error'
  content: string
  sources: string[]
  createdAt: string
  pending: boolean
}

export interface CopilotChatTurn {
  role: CopilotRole
  content: string
}

export type CopilotStreamEvent =
  | { type: 'sources'; items: string[] }
  | { type: 'delta'; content: string }
  | { type: 'error'; message: string }
  | { type: 'done' }
```

- [ ] **Step 2: Create the SSE-over-fetch client**

Create `frontend/src/services/copilotApi.ts`:

```typescript
import type { CopilotChatTurn, CopilotStreamEvent } from '../types/copilot'

const COPILOT_CHAT_URL = `${import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1'}/copilot/chat`

/**
 * POSTs to the Copilot chat endpoint and parses its Server-Sent Events response.
 * Native `EventSource` can't send a POST body, so this parses SSE frames by hand
 * over a streaming `fetch` response instead.
 */
export async function streamCopilotChat(
  params: { message: string; history: CopilotChatTurn[]; pagePath: string },
  onEvent: (event: CopilotStreamEvent) => void,
  signal: AbortSignal,
): Promise<void> {
  const response = await fetch(COPILOT_CHAT_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
    body: JSON.stringify({ message: params.message, history: params.history, page_path: params.pagePath }),
    signal,
  })

  if (!response.ok || !response.body) {
    throw new Error(`Copilot request failed with status ${response.status}`)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    let boundary = buffer.indexOf('\n\n')
    while (boundary !== -1) {
      const frame = buffer.slice(0, boundary)
      buffer = buffer.slice(boundary + 2)
      const dataLine = frame.split('\n').find(line => line.startsWith('data: '))
      if (dataLine) {
        onEvent(JSON.parse(dataLine.slice('data: '.length)) as CopilotStreamEvent)
      }
      boundary = buffer.indexOf('\n\n')
    }
  }
}
```

- [ ] **Step 3: Typecheck**

Run: `cd frontend && npx tsc -b --noEmit 2>&1 | grep -i copilot || echo "no copilot errors"`
Expected: `no copilot errors` (the two new files compile cleanly; `useCopilotChat`/components that consume them don't exist yet, so no wider build is expected to pass at this point).

- [ ] **Step 4: Commit**

```bash
git add frontend/src/types/copilot.ts frontend/src/services/copilotApi.ts
git commit -m "feat: add Copilot SSE client and message types"
```

---

### Task 6: `useCopilotChat` hook

**Files:**
- Create: `frontend/src/copilot/useCopilotChat.ts`

**Interfaces:**
- Consumes: `streamCopilotChat` from `../services/copilotApi` (Task 5); `CopilotMessage`, `CopilotChatTurn` from `../types/copilot` (Task 5).
- Produces: `useCopilotChat(pagePath: string) -> { messages: CopilotMessage[]; isStreaming: boolean; sendMessage: (text: string) => void; stop: () => void; reset: () => void }` — Task 8's `CopilotDrawer` calls this directly.

- [ ] **Step 1: Create the hook**

Create `frontend/src/copilot/useCopilotChat.ts`:

```typescript
import { useCallback, useEffect, useRef, useState } from 'react'
import { streamCopilotChat } from '../services/copilotApi'
import type { CopilotMessage } from '../types/copilot'

const STORAGE_KEY = 'redial-copilot-messages'
const HISTORY_TURNS = 10

function loadStoredMessages(): CopilotMessage[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? (JSON.parse(raw) as CopilotMessage[]) : []
  } catch {
    return []
  }
}

function createId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`
}

export function useCopilotChat(pagePath: string) {
  const [messages, setMessages] = useState<CopilotMessage[]>(loadStoredMessages)
  const [isStreaming, setIsStreaming] = useState(false)
  const abortRef = useRef<AbortController | null>(null)

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(messages))
    } catch {
      // localStorage can throw in private-browsing/storage-full contexts — losing
      // persisted history is acceptable, the in-memory conversation still works.
    }
  }, [messages])

  const sendMessage = useCallback(
    async (text: string) => {
      const trimmed = text.trim()
      if (!trimmed || isStreaming) return

      const history = messages
        .filter((message): message is CopilotMessage & { role: 'user' | 'assistant' } => message.role === 'user' || message.role === 'assistant')
        .slice(-HISTORY_TURNS)
        .map(message => ({ role: message.role, content: message.content }))

      const userMessage: CopilotMessage = { id: createId(), role: 'user', content: trimmed, sources: [], createdAt: new Date().toISOString(), pending: false }
      const assistantId = createId()
      const assistantMessage: CopilotMessage = { id: assistantId, role: 'assistant', content: '', sources: [], createdAt: new Date().toISOString(), pending: true }
      setMessages(current => [...current, userMessage, assistantMessage])
      setIsStreaming(true)

      const controller = new AbortController()
      abortRef.current = controller

      try {
        await streamCopilotChat({ message: trimmed, history, pagePath }, event => {
          if (event.type === 'sources') {
            setMessages(current => current.map(message => (message.id === assistantId ? { ...message, sources: event.items } : message)))
          } else if (event.type === 'delta') {
            setMessages(current => current.map(message => (message.id === assistantId ? { ...message, content: message.content + event.content } : message)))
          } else if (event.type === 'error') {
            setMessages(current => current.map(message => (message.id === assistantId ? { ...message, role: 'error', content: event.message, pending: false } : message)))
          } else if (event.type === 'done') {
            setMessages(current => current.map(message => (message.id === assistantId ? { ...message, pending: false } : message)))
          }
        }, controller.signal)
      } catch {
        if (controller.signal.aborted) return
        setMessages(current =>
          current.map(message =>
            message.id === assistantId
              ? { ...message, role: 'error', content: 'Could not reach the AI assistant. Check your connection and try again.', pending: false }
              : message,
          ),
        )
      } finally {
        setIsStreaming(false)
        abortRef.current = null
      }
    },
    [messages, isStreaming, pagePath],
  )

  const stop = useCallback(() => {
    abortRef.current?.abort()
  }, [])

  const reset = useCallback(() => {
    abortRef.current?.abort()
    setMessages([])
    localStorage.removeItem(STORAGE_KEY)
  }, [])

  return { messages, isStreaming, sendMessage, stop, reset }
}
```

- [ ] **Step 2: Typecheck**

Run: `cd frontend && npx tsc -b --noEmit 2>&1 | grep -i "copilot/useCopilotChat" || echo "no errors in useCopilotChat"`
Expected: `no errors in useCopilotChat`.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/copilot/useCopilotChat.ts
git commit -m "feat: add useCopilotChat hook with localStorage-persisted history"
```

---

### Task 7: `CopilotMessage` + `CopilotEmptyState` (markdown rendering)

**Files:**
- Modify: `frontend/package.json` (add `react-markdown`, `remark-gfm`)
- Create: `frontend/src/copilot/CopilotMessage.tsx`
- Create: `frontend/src/copilot/CopilotEmptyState.tsx`
- Modify: `frontend/src/styles/global.css` (append the Copilot message/empty-state styles)

**Interfaces:**
- Consumes: `CopilotMessage` type (Task 5); `Timestamp` from `../ui/Timestamp` (existing, reused as-is).
- Produces: `<CopilotMessage message={CopilotMessage} />`, `<CopilotEmptyState onSuggestion={(question: string) => void} />` — Task 8's `CopilotDrawer` renders both directly.

- [ ] **Step 1: Install the markdown dependencies**

Run: `cd frontend && npm install react-markdown remark-gfm`
Expected: `frontend/package.json` and `frontend/package-lock.json` gain `react-markdown` and `remark-gfm` under `dependencies`.

- [ ] **Step 2: Create `CopilotMessage.tsx`**

Create `frontend/src/copilot/CopilotMessage.tsx`:

```tsx
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Timestamp } from '../ui/Timestamp'
import type { CopilotMessage as CopilotMessageType } from '../types/copilot'

export function CopilotMessage({ message }: { message: CopilotMessageType }) {
  if (message.role === 'user') {
    return (
      <div className="copilot-message copilot-message-user">
        <div className="copilot-bubble">{message.content}</div>
        <Timestamp iso={message.createdAt} />
      </div>
    )
  }

  const isError = message.role === 'error'
  const isThinking = message.pending && message.content === ''

  return (
    <div className={`copilot-message copilot-message-assistant ${isError ? 'copilot-message-error' : ''}`}>
      <div className="copilot-bubble">
        {isThinking ? (
          <span className="thinking-pulse"><span /><span /><span /></span>
        ) : (
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
        )}
      </div>
      {message.sources.length > 0 && (
        <div className="copilot-sources">
          {message.sources.map(source => (
            <span key={source} className="route-chip">{source}</span>
          ))}
        </div>
      )}
      <Timestamp iso={message.createdAt} />
    </div>
  )
}
```

- [ ] **Step 3: Create `CopilotEmptyState.tsx`**

Create `frontend/src/copilot/CopilotEmptyState.tsx`:

```tsx
import { Sparkles } from 'lucide-react'

const SUGGESTIONS = [
  "Summarize today's activity",
  'Which mandates are highest risk?',
  'What should operations prioritize today?',
  'Show payment success trends',
  'Which workflows took the longest?',
  'What anomalies do you notice?',
]

export function CopilotEmptyState({ onSuggestion }: { onSuggestion: (question: string) => void }) {
  return (
    <div className="copilot-empty">
      <div className="copilot-empty-icon"><Sparkles size={22} /></div>
      <h3>Ask the Copilot anything</h3>
      <p>Grounded in your real payments, mandates, decisions, and operational data — never invented.</p>
      <div className="copilot-suggestions">
        {SUGGESTIONS.map(question => (
          <button key={question} type="button" className="copilot-suggestion" onClick={() => onSuggestion(question)}>
            {question}
          </button>
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Append the Copilot message styles to `global.css`**

At the end of `frontend/src/styles/global.css`, append:

```css
/* ============================================================
   AI Operations Copilot — messages & empty state
   ============================================================ */
.copilot-empty { margin: auto 0; text-align: center; padding: 20px 8px; }
.copilot-empty-icon { width: 46px; height: 46px; margin: 0 auto 14px; border-radius: 50%; background: var(--accent-soft); color: var(--accent); display: grid; place-items: center; }
.copilot-empty h3 { margin: 0 0 8px; color: var(--text); font-size: 15px; }
.copilot-empty p { margin: 0 0 20px; color: var(--text-muted); font-size: 12px; line-height: 1.6; }
.copilot-suggestions { display: grid; gap: 8px; }
.copilot-suggestion {
  text-align: left; padding: 10px 12px; border: 1px solid var(--border); border-radius: var(--radius-sm);
  background: var(--card); color: var(--text-secondary); font-size: 12px; transition: border-color .16s ease, color .16s ease, background .16s ease;
}
.copilot-suggestion:hover { border-color: var(--accent); color: var(--text); background: var(--card-hover); }

.copilot-message { display: flex; flex-direction: column; gap: 6px; max-width: 92%; }
.copilot-message-user { align-self: flex-end; align-items: flex-end; }
.copilot-message-assistant { align-self: flex-start; align-items: flex-start; }
.copilot-bubble { border-radius: var(--radius-md); padding: 10px 13px; font-size: 13px; line-height: 1.6; }
.copilot-message-user .copilot-bubble { background: var(--accent-strong); color: #fff; border-bottom-right-radius: 4px; }
.copilot-message-assistant .copilot-bubble { background: var(--card); border: 1px solid var(--border); color: var(--text); border-bottom-left-radius: 4px; }
.copilot-message-error .copilot-bubble { background: var(--danger-soft); border: 1px solid var(--danger-soft); color: var(--danger); }
.copilot-bubble p { margin: 0 0 8px; }
.copilot-bubble p:last-child { margin-bottom: 0; }
.copilot-bubble ul, .copilot-bubble ol { margin: 0 0 8px; padding-left: 18px; }
.copilot-bubble code { background: var(--card-hover); padding: 1px 5px; border-radius: 4px; font-size: 11.5px; }
.copilot-bubble strong { color: inherit; font-weight: 700; }
.copilot-sources { display: flex; flex-wrap: wrap; gap: 6px; }
```

- [ ] **Step 5: Typecheck**

Run: `cd frontend && npx tsc -b --noEmit 2>&1 | grep -i copilot || echo "no copilot errors"`
Expected: `no copilot errors`.

- [ ] **Step 6: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/src/copilot/CopilotMessage.tsx frontend/src/copilot/CopilotEmptyState.tsx frontend/src/styles/global.css
git commit -m "feat: add Copilot message rendering with markdown and source chips"
```

---

### Task 8: `CopilotDrawer` + `CopilotLauncher` + mount in `AppShell`

**Files:**
- Create: `frontend/src/copilot/CopilotDrawer.tsx`
- Create: `frontend/src/copilot/CopilotLauncher.tsx`
- Modify: `frontend/src/layout/AppShell.tsx`
- Modify: `frontend/src/styles/global.css` (append drawer/launcher styles)

**Interfaces:**
- Consumes: `useCopilotChat` (Task 6), `CopilotMessage`, `CopilotEmptyState` (Task 7).
- Produces: `<CopilotLauncher />` — a self-contained, drop-in component; `AppShell` renders it once so it appears on every `/dashboard/*` route.

- [ ] **Step 1: Create `CopilotDrawer.tsx`**

Create `frontend/src/copilot/CopilotDrawer.tsx`:

```tsx
import { AnimatePresence, motion } from 'framer-motion'
import { CornerDownLeft, RotateCcw, Sparkles, X } from 'lucide-react'
import { useEffect, useRef, useState, type KeyboardEvent } from 'react'
import { useLocation } from 'react-router-dom'
import { CopilotEmptyState } from './CopilotEmptyState'
import { CopilotMessage } from './CopilotMessage'
import { useCopilotChat } from './useCopilotChat'

export function CopilotDrawer({ open, onClose }: { open: boolean; onClose: () => void }) {
  const location = useLocation()
  const { messages, isStreaming, sendMessage, reset } = useCopilotChat(location.pathname)
  const [draft, setDraft] = useState('')
  const listRef = useRef<HTMLDivElement>(null)
  const [isNearBottom, setIsNearBottom] = useState(true)

  useEffect(() => {
    if (!open) return
    function handleKeyDown(event: globalThis.KeyboardEvent) {
      if (event.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [open, onClose])

  useEffect(() => {
    if (!listRef.current || !isNearBottom) return
    listRef.current.scrollTop = listRef.current.scrollHeight
  }, [messages, isNearBottom])

  function handleScroll() {
    const el = listRef.current
    if (!el) return
    setIsNearBottom(el.scrollHeight - el.scrollTop - el.clientHeight < 80)
  }

  function handleSend() {
    if (!draft.trim()) return
    sendMessage(draft)
    setDraft('')
    setIsNearBottom(true)
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      handleSend()
    }
  }

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.button
            className="scrim copilot-scrim"
            aria-label="Close Copilot"
            onClick={onClose}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          />
          <motion.aside
            className="copilot-drawer"
            role="dialog"
            aria-modal="true"
            aria-label="AI Operations Copilot"
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 30, stiffness: 300 }}
          >
            <header className="copilot-header">
              <div className="copilot-header-title">
                <Sparkles size={17} />
                <span>Copilot</span>
                <em className="copilot-model-pill">Groq · Llama 3</em>
              </div>
              <div className="copilot-header-actions">
                <button type="button" className="icon-button" aria-label="Reset conversation" onClick={reset} disabled={messages.length === 0}>
                  <RotateCcw size={16} />
                </button>
                <button type="button" className="icon-button" aria-label="Close Copilot" onClick={onClose}>
                  <X size={18} />
                </button>
              </div>
            </header>

            <div className="copilot-messages" ref={listRef} onScroll={handleScroll}>
              {messages.length === 0 ? (
                <CopilotEmptyState onSuggestion={question => sendMessage(question)} />
              ) : (
                messages.map(message => <CopilotMessage key={message.id} message={message} />)
              )}
            </div>

            {!isNearBottom && messages.length > 0 && (
              <button
                type="button"
                className="copilot-jump-latest"
                onClick={() => {
                  setIsNearBottom(true)
                  listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: 'smooth' })
                }}
              >
                ↓ New content
              </button>
            )}

            <div className="copilot-composer">
              <textarea
                value={draft}
                onChange={event => setDraft(event.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask about payments, mandates, decisions..."
                rows={1}
                disabled={isStreaming}
              />
              <button type="button" className="primary-button copilot-send" onClick={handleSend} disabled={isStreaming || !draft.trim()} aria-label="Send message">
                <CornerDownLeft size={15} />
              </button>
            </div>
            <p className="copilot-hint">Enter to send · Shift+Enter for a new line · Esc to close</p>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  )
}
```

- [ ] **Step 2: Create `CopilotLauncher.tsx`**

Create `frontend/src/copilot/CopilotLauncher.tsx`:

```tsx
import { motion } from 'framer-motion'
import { Sparkles } from 'lucide-react'
import { useEffect, useState } from 'react'
import { CopilotDrawer } from './CopilotDrawer'

export function CopilotLauncher() {
  const [open, setOpen] = useState(false)

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        setOpen(value => !value)
      }
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [])

  return (
    <>
      {!open && (
        <motion.button
          type="button"
          className="copilot-launcher"
          aria-label="Open AI Copilot"
          onClick={() => setOpen(true)}
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          whileHover={{ scale: 1.06 }}
          whileTap={{ scale: 0.96 }}
        >
          <span className="copilot-launcher-pulse" />
          <Sparkles size={20} />
        </motion.button>
      )}
      <CopilotDrawer open={open} onClose={() => setOpen(false)} />
    </>
  )
}
```

- [ ] **Step 3: Mount the launcher in `AppShell`**

In `frontend/src/layout/AppShell.tsx`, add the import and render `<CopilotLauncher />`:

```tsx
import { useState, type ReactNode } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { Menu, X } from 'lucide-react'
import { CopilotLauncher } from '../copilot/CopilotLauncher'
import { Navbar } from '../navbar/Navbar'
import { Sidebar } from '../sidebar/Sidebar'

export function AppShell({ children }: { children: ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  return <div className="app-shell">
    <AnimatePresence>{sidebarOpen && <motion.button className="scrim" aria-label="Close navigation" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setSidebarOpen(false)} />}</AnimatePresence>
    <Sidebar open={sidebarOpen} onNavigate={() => setSidebarOpen(false)} />
    <div className="shell-main"><Navbar /><button className="mobile-menu" aria-label="Open navigation" onClick={() => setSidebarOpen(true)}>{sidebarOpen ? <X size={20} /> : <Menu size={20} />}</button><main>{children}</main><footer><span>REDIAL / OPERATIONS CONSOLE</span><span>v0.1.0 <i /> All systems nominal</span></footer></div>
    <CopilotLauncher />
  </div>
}
```

- [ ] **Step 4: Append the drawer/launcher styles to `global.css`**

At the end of `frontend/src/styles/global.css`, append:

```css
/* ============================================================
   AI Operations Copilot — launcher & drawer
   ============================================================ */
.copilot-launcher {
  position: fixed; right: 28px; bottom: 28px; z-index: 40;
  width: 54px; height: 54px; border-radius: 50%; border: 0;
  display: grid; place-items: center; color: #fff;
  background: linear-gradient(155deg, var(--accent), var(--accent-strong));
  box-shadow: 0 10px 28px rgba(79, 70, 229, .4);
}
.copilot-launcher-pulse {
  position: absolute; inset: -6px; border-radius: 50%; border: 2px solid var(--accent);
  opacity: .5; animation: copilot-pulse 2.4s ease-out infinite; pointer-events: none;
}
@keyframes copilot-pulse {
  0% { transform: scale(.85); opacity: .55; }
  100% { transform: scale(1.35); opacity: 0; }
}

.copilot-scrim { z-index: 45; }
.copilot-drawer {
  position: fixed; top: 0; right: 0; bottom: 0; z-index: 46; width: 420px; max-width: 100vw;
  background: var(--bg-elevated); border-left: 1px solid var(--border-strong); box-shadow: var(--shadow-lg);
  display: flex; flex-direction: column;
}
.copilot-header { display: flex; align-items: center; justify-content: space-between; padding: 16px 18px; border-bottom: 1px solid var(--border); }
.copilot-header-title { display: flex; align-items: center; gap: 8px; color: var(--text); font-size: 14px; font-weight: 700; }
.copilot-header-title svg { color: var(--accent); }
.copilot-model-pill { color: var(--text-muted); font-size: 10px; font-style: normal; font-weight: 700; border: 1px solid var(--border); background: var(--card); padding: 3px 8px; border-radius: 999px; margin-left: 4px; }
.copilot-header-actions { display: flex; gap: 6px; }

.copilot-messages { flex: 1; overflow-y: auto; padding: 18px; display: flex; flex-direction: column; gap: 16px; position: relative; }

.copilot-jump-latest {
  position: absolute; bottom: 84px; left: 50%; transform: translateX(-50%); z-index: 2;
  border: 1px solid var(--border-strong); background: var(--card); color: var(--text-secondary);
  border-radius: 999px; padding: 5px 12px; font-size: 11px; font-weight: 700; box-shadow: var(--shadow-md);
}

.copilot-composer { display: flex; align-items: flex-end; gap: 8px; padding: 12px 16px; border-top: 1px solid var(--border); }
.copilot-composer textarea {
  flex: 1; resize: none; max-height: 120px; border: 1px solid var(--border); border-radius: var(--radius-sm);
  background: var(--card); color: var(--text); font: inherit; font-size: 13px; padding: 9px 11px;
  transition: border-color .16s ease;
}
.copilot-composer textarea:focus { outline: none; border-color: var(--accent); box-shadow: var(--focus-ring); }
.copilot-send { width: 36px; height: 36px; padding: 0; flex: 0 0 auto; }
.copilot-hint { margin: 0; padding: 0 16px 12px; color: var(--text-muted); font-size: 10px; text-align: center; }

@media (max-width: 640px) {
  .copilot-drawer { width: 100vw; }
  .copilot-launcher { right: 18px; bottom: 18px; }
}
```

- [ ] **Step 5: Full frontend verification**

Run: `cd frontend && npx tsc -b`
Expected: no errors.

Run: `cd frontend && npm run lint`
Expected: no errors.

Run: `cd frontend && npm run build`
Expected: build succeeds.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/copilot/CopilotDrawer.tsx frontend/src/copilot/CopilotLauncher.tsx frontend/src/layout/AppShell.tsx frontend/src/styles/global.css
git commit -m "feat: add floating Copilot launcher and slide-in drawer"
```

---

### Task 9: Final verification and E2E smoke test

**Files:** none (verification only).

**Interfaces:** none — this task exercises the full stack built in Tasks 1-8.

- [ ] **Step 1: Run the full backend test suite**

Run: `.venv/bin/python -m pytest backend/tests/ -v`
Expected: all tests pass, including every Copilot test added in Tasks 1-4.

- [ ] **Step 2: Run full frontend verification**

Run: `cd frontend && npx tsc -b && npm run lint && npm run build`
Expected: all three succeed with no errors.

- [ ] **Step 3: Manual end-to-end smoke test**

Start the backend: `.venv/bin/uvicorn backend.app.main:app --reload` (from the project root).
Start the frontend: `cd frontend && npm run dev`.

With `GROQ_API_KEY` configured in `backend/.env` (real key), open the app in a browser and verify:

1. A floating Copilot button appears in the bottom-right on `/dashboard` and other internal routes, but not on `/`, `/login`, or `/signup`.
2. Pressing `⌘K`/`Ctrl+K` opens and closes the drawer from anywhere inside the dashboard.
3. With no messages, the empty state with suggested questions is shown.
4. Clicking a suggested question (e.g. "Summarize today's activity") sends it, shows a typing/thinking indicator, then streams markdown text progressively (not all at once).
5. The assistant's reply shows a row of "source" chips naming real data it used (e.g. "Dashboard summary (...)").
6. Ask a question referencing a real seeded mandate reference (use `/api/v1/dev/seed` or the Settings/dev-seed flow to create demo data first) and confirm the answer cites that mandate's real numbers.
7. Ask about a mandate reference that does not exist and confirm the Copilot says it has no such record, rather than inventing one.
8. Refresh the page and confirm the conversation persists (localStorage).
9. Click reset and confirm the conversation clears back to the empty state.
10. Scroll up mid-conversation and confirm streaming doesn't yank the scroll position, and a "↓ New content" affordance appears.

Then, temporarily unset/comment out `GROQ_API_KEY` in `backend/.env`, restart the backend, and verify:

11. Asking any question now yields a clear "AI assistant isn't configured" message, not an error page and not a fabricated answer, and the sources chip row still reflects real (if sparse) operational data.

Restore `GROQ_API_KEY` afterward.

- [ ] **Step 4: Report**

Summarize in chat: files created, files modified, any deviations from this plan and why, and confirmation that all steps in Step 3 passed (or note which did not and what was done about it).
