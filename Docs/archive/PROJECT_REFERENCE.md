# PJA-Sensei — Full Project Reference

Reference of every Python module in the repository: purpose, imports, module-level variables, classes (fields/methods), and functions. Non-Python assets are listed at the end.

**Project:** FastAPI hexagonal microservice — socratic lab assistant (PJA-Sensei AI Module).

**Architecture layers** (see also `AGENTS.md`):

| Layer | Path | Role |
|-------|------|------|
| Domain | `app/domain` | Entities, ports, exceptions — no frameworks |
| Application | `app/application` | Use cases / services |
| Infrastructure | `app/infrastructure` | Adapters (LLM, Chroma, cache, webhooks) |
| API | `app/api` | FastAPI routers, middleware, DI, HTTP errors |
| Core | `app/core` | Settings from env |

## How a chat request flows

1. **Middleware** (`RequestId` → `JwtAuth` → `RateLimit` → CORS) attaches request id, JWT claims, and enforces rate limits.
2. **Router** `POST /conversations/{id}/messages` loads the owned session via `SessionService` / access checks.
3. **`ChatService.send_message`**: prelab gate → token budget → `SecurityGuard` → `PedagogyGates` → RAG retrieve → cache lookup → `LlmPort` → `ResponsePipeline` (JSON parse, penalties, goals, checkpoints) → save → webhook.
4. Domain exceptions become stable HTTP JSON via `app/api/errors.py`.

## Composition root

Shared adapters live in `app/api/deps.py` (`repo`, `llm_adapter`, `rag_adapter`, `llm_cache`, `webhook_adapter`) and are injected into services through FastAPI `Depends`.

---

## Table of contents

- **app/main.py**
  - [`app/main.py`](#app-main-py)
- **app/core**
  - [`app/core/config.py`](#app-core-config-py)
- **app/domain**
  - [`app/domain/conversation.py`](#app-domain-conversation-py)
  - [`app/domain/exceptions.py`](#app-domain-exceptions-py)
  - [`app/domain/ports.py`](#app-domain-ports-py)
  - [`app/domain/sensei.py`](#app-domain-sensei-py)
- **app/application**
  - [`app/application/access.py`](#app-application-access-py)
  - [`app/application/cache_keys.py`](#app-application-cache_keys-py)
  - [`app/application/chat_service.py`](#app-application-chat_service-py)
  - [`app/application/config_dry_run.py`](#app-application-config_dry_run-py)
  - [`app/application/dto.py`](#app-application-dto-py)
  - [`app/application/grade_payload.py`](#app-application-grade_payload-py)
  - [`app/application/metrics.py`](#app-application-metrics-py)
  - [`app/application/pedagogy_gates.py`](#app-application-pedagogy_gates-py)
  - [`app/application/prelab_service.py`](#app-application-prelab_service-py)
  - [`app/application/prompts.py`](#app-application-prompts-py)
  - [`app/application/response_pipeline.py`](#app-application-response_pipeline-py)
  - [`app/application/security.py`](#app-application-security-py)
  - [`app/application/session_service.py`](#app-application-session_service-py)
  - [`app/application/similarity.py`](#app-application-similarity-py)
- **app/api**
  - [`app/api/auth.py`](#app-api-auth-py)
  - [`app/api/deps.py`](#app-api-deps-py)
  - [`app/api/errors.py`](#app-api-errors-py)
  - [`app/api/middleware.py`](#app-api-middleware-py)
  - [`app/api/routers/config.py`](#app-api-routers-config-py)
  - [`app/api/routers/conversations.py`](#app-api-routers-conversations-py)
  - [`app/api/routers/health.py`](#app-api-routers-health-py)
  - [`app/api/routers/ui.py`](#app-api-routers-ui-py)
- **app/infrastructure**
  - [`app/infrastructure/cache_memory.py`](#app-infrastructure-cache_memory-py)
  - [`app/infrastructure/conversations_memory.py`](#app-infrastructure-conversations_memory-py)
  - [`app/infrastructure/llm_errors.py`](#app-infrastructure-llm_errors-py)
  - [`app/infrastructure/llm_openai.py`](#app-infrastructure-llm_openai-py)
  - [`app/infrastructure/rag_chroma.py`](#app-infrastructure-rag_chroma-py)
  - [`app/infrastructure/webhooks.py`](#app-infrastructure-webhooks-py)
- **tests**
  - [`tests/conftest.py`](#tests-conftest-py)
  - [`tests/test_abuse_hardening.py`](#tests-test_abuse_hardening-py)
  - [`tests/test_advanced_features.py`](#tests-test_advanced_features-py)
  - [`tests/test_auth_rate_limit.py`](#tests-test_auth_rate_limit-py)
  - [`tests/test_features_ui_api.py`](#tests-test_features_ui_api-py)
  - [`tests/test_m1.py`](#tests-test_m1-py)
  - [`tests/test_m2.py`](#tests-test_m2-py)
  - [`tests/test_m3.py`](#tests-test_m3-py)
  - [`tests/test_m4.py`](#tests-test_m4-py)
  - [`tests/test_m5.py`](#tests-test_m5-py)
  - [`tests/test_m6.py`](#tests-test_m6-py)
  - [`tests/test_m7.py`](#tests-test_m7-py)
  - [`tests/test_new_features.py`](#tests-test_new_features-py)
- [Non-Python assets](#non-python-assets)

# app/main.py

Application entrypoint: builds FastAPI app, middleware, exception handlers, routers, and background session purge.

## `app/main.py`

**Purpose:** Creates the FastAPI app: lifespan GC for sessions, CORS, JWT/rate-limit/request-id middleware, exception→HTTP map, conditional UI/docs.

**Layer / role:** Application entrypoint: builds FastAPI app, middleware, exception handlers, routers, and background session purge.

- **Lines:** 127
- **Imports:** 32 · **Classes:** 0 · **Functions:** 2 · **Module vars:** 2

### Imports

- L1: `import asyncio` — stdlib
- L2: `import logging` — stdlib
- L3: `from fastapi import FastAPI` — HTTP framework
- L4: `from fastapi.middleware.cors import CORSMiddleware` — HTTP framework
- L5: `from contextlib import asynccontextmanager` — stdlib
- L10: `from openai import RateLimitError` — OpenAI-compatible LLM client
- L10: `from openai import APIConnectionError` — OpenAI-compatible LLM client
- L10: `from openai import APITimeoutError` — OpenAI-compatible LLM client
- L12: `from app.api.errors import prelab_required_handler` — API helpers/routers
- L12: `from app.api.errors import token_budget_exceeded_handler` — API helpers/routers
- L12: `from app.api.errors import unknown_conversation_handler` — API helpers/routers
- L12: `from app.api.errors import unknown_message_handler` — API helpers/routers
- L12: `from app.api.errors import hint_reveal_forbidden_handler` — API helpers/routers
- L12: `from app.api.errors import ssrf_blocked_handler` — API helpers/routers
- L12: `from app.api.errors import llm_rate_limited_handler` — API helpers/routers
- L12: `from app.api.errors import llm_unavailable_handler` — API helpers/routers
- L22: `from app.api.middleware import RequestIdMiddleware` — API helpers/routers
- L22: `from app.api.middleware import JwtAuthMiddleware` — API helpers/routers
- L22: `from app.api.middleware import RateLimitMiddleware` — API helpers/routers
- L23: `from app.api.routers import health` — API helpers/routers
- L23: `from app.api.routers import config` — API helpers/routers
- L23: `from app.api.routers import conversations` — API helpers/routers
- L23: `from app.api.routers import ui` — API helpers/routers
- L24: `from app.core.config import settings` — settings
- L25: `from app.domain.exceptions import PrelabRequired` — domain types/ports/exceptions
- L25: `from app.domain.exceptions import TokenBudgetExceeded` — domain types/ports/exceptions
- L25: `from app.domain.exceptions import UnknownConversation` — domain types/ports/exceptions
- L25: `from app.domain.exceptions import UnknownMessage` — domain types/ports/exceptions
- L25: `from app.domain.exceptions import HintRevealForbidden` — domain types/ports/exceptions
- L25: `from app.domain.exceptions import SsrfBlockedError` — domain types/ports/exceptions
- L31: `from app.infrastructure.llm_errors import LlmRateLimitError` — infrastructure adapters
- L31: `from app.infrastructure.llm_errors import LlmUnavailableError` — infrastructure adapters

### Module-level variables / constants

- L33: **`logger`** — Module logger.
- L126: **`app`** — ASGI FastAPI application instance.

### Functions

- L37: @asynccontextmanager `async def lifespan(app: FastAPI)`
  - Starts background task that purges expired conversations every 5s; cancels on shutdown.
- L54: `def create_app() -> FastAPI`
  - Wires middleware, CORS, exception handlers, and routers; returns FastAPI instance.

---

# app/core

Cross-cutting runtime settings loaded from environment (.env).

## `app/core/config.py`

**Purpose:** Pydantic Settings: LLM, auth/JWT, CORS, cache, RAG, webhooks, frustration cooldown.

**Layer / role:** Cross-cutting runtime settings loaded from environment (.env).

- **Lines:** 40
- **Imports:** 4 · **Classes:** 1 · **Functions:** 0 · **Module vars:** 1

### Imports

- L1: `from pydantic_settings import BaseSettings` — env settings
- L1: `from pydantic_settings import SettingsConfigDict` — env settings
- L2: `from typing import List` — stdlib
- L2: `from typing import Optional` — stdlib

### Module-level variables / constants

- L39: **`settings`** — Singleton Settings instance loaded from environment / .env.

### Class `Settings(BaseSettings)`

- **Line:** 5
- **Description:** Environment-backed application settings.

#### Fields / class variables

- L6: **`LLM_BASE_URL`**: `str`
- L7: **`LLM_API_KEY`**: `str`
- L8: **`MAIN_MODEL`**: `str`
- L9: **`SECURITY_MODEL`**: `str`
- L10: **`AI_AUTH_ENABLED`**: `bool` = `True`
- L11: **`AI_JWT_SECRET`**: `str` = `''`
- L12: **`AI_JWT_AUDIENCE`**: `Optional[str]` = `'pja-sensei-ai'`
- L13: **`AI_JWT_ISSUER`**: `Optional[str]` = `'pja-spring'`
- L14: **`AI_EXPOSE_DOCS`**: `bool` = `False`
- L15: **`AI_EXPOSE_UI`**: `bool` = `False`
- L16: **`AI_PROFESSOR_ROLES`**: `List[str]` = `['professor', 'admin']`
- L17: **`RATE_LIMIT_PER_MINUTE`**: `int` = `60`
- L18: **`CONVERSATION_TTL_SECONDS`**: `int` = `7200`
- L19: **`CORS_ORIGINS`**: `List[str]` = `[]`
- L20: **`TRUST_X_FORWARDED_FOR`**: `bool` = `False`
- L21: **`SECURITY_FAIL_CLOSED`**: `bool` = `True`
- L22: **`SECURITY_ALWAYS_CLASSIFY`**: `bool` = `False`
- L23: **`MAIN_MODEL_FALLBACK`**: `Optional[str]` = `'qwen2.5-coder:3b'`
- L24: **`LLM_MAX_RETRIES`**: `int` = `2`
- L25: **`CACHE_SIZE`**: `int` = `128`
- L26: **`CACHE_TTL_SECONDS`**: `int` = `3600`
- L27: **`RAG_TOP_K`**: `int` = `3`
- L28: **`RAG_FETCH_TIMEOUT`**: `float` = `5.0`
- L29: **`RAG_FETCH_MAX_BYTES`**: `int` = `2000000`
- L30: **`FRUSTRATION_EVENT_COOLDOWN_SECONDS`**: `float` = `15.0`
- L32: **`TELEMETRY_URL`**: `str` = `''`
- L33: **`SUMMARY_WEBHOOK_URL`**: `str` = `''`
- L34: **`WEBHOOK_URL`**: `str` = `''`
- L35: **`WEBHOOK_TIMEOUT`**: `float` = `3.0`
- L36: **`WEBHOOK_EVENT_BUFFER_SIZE`**: `int` = `50`
- L38: **`model_config`** = `SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')`

---

# app/domain

Hexagonal core: entities, value objects, domain exceptions, and abstract ports. No FastAPI/DB/HTTP clients.

## `app/domain/conversation.py`

**Purpose:** Conversation aggregate: messages, progress, hints, focus mode, grade payload.

**Layer / role:** Hexagonal core: entities, value objects, domain exceptions, and abstract ports. No FastAPI/DB/HTTP clients.

- **Lines:** 78
- **Imports:** 11 · **Classes:** 3 · **Functions:** 0 · **Module vars:** 1

### Imports

- L1: `import time` — stdlib
- L2: `from pydantic import BaseModel` — validation models
- L2: `from pydantic import Field` — validation models
- L3: `from typing import Dict` — stdlib
- L3: `from typing import List` — stdlib
- L3: `from typing import Any` — stdlib
- L3: `from typing import Literal` — stdlib
- L3: `from typing import Optional` — stdlib
- L4: `from datetime import datetime` — stdlib
- L4: `from datetime import timezone` — stdlib
- L6: `from app.domain.sensei import SenseiConfig` — domain types/ports/exceptions

### Module-level variables / constants

- L8: **`GoalStatus`** — Literal alias for goal progress: not_started | in_progress | done.

### Class `MessageFeedback(BaseModel)`

- **Line:** 9
- **Description:** 1–5 rating + optional comment on an assistant message.

#### Fields / class variables

- L10: **`rating`**: `int` = `Field(ge=1, le=5)`
- L11: **`comment`**: `Optional[str]` = `None`
- L12: **`created_at`**: `datetime` = `Field(default_factory=lambda: datetime.now(timezone.utc))`

### Class `ChatMessage(BaseModel)`

- **Line:** 14
- **Description:** Single user/assistant message with scoring/metadata.

#### Fields / class variables

- L15: **`message_id`**: `str`
- L16: **`role`**: `Literal['user', 'assistant']`
- L17: **`content`**: `str`
- L18: **`client_message_id`**: `Optional[str]` = `None`
- L19: **`code_context`**: `Optional[Dict[str, Any]]` = `None`
- L20: **`prompt_score`**: `Optional[int]` = `None`
- L21: **`prompt_feedback`**: `Optional[str]` = `None`
- L22: **`penalty_applied`**: `Optional[bool]` = `None`
- L23: **`suggested_next_step`**: `Optional[str]` = `None`
- L24: **`tokens_used`**: `int` = `0`
- L25: **`model`**: `Optional[str]` = `None`
- L26: **`feedback`**: `Optional[MessageFeedback]` = `None`
- L27: **`timestamp`**: `datetime` = `Field(default_factory=lambda: datetime.now(timezone.utc))`

### Class `Conversation(BaseModel)`

- **Line:** 29
- **Description:** Session aggregate holding config, messages, progress, hints, grade.

#### Fields / class variables

- L30: **`id`**: `str`
- L31: **`config`**: `SenseiConfig`
- L32: **`messages`**: `List[ChatMessage]` = `[]`
- L33: **`prelab_completed`**: `bool` = `False`
- L34: **`goal_progress`**: `Dict[str, Literal['not_started', 'in_progress', 'done']]` = `{}`
- L35: **`unlocked_checkpoints`**: `List[str]` = `[]`
- L36: **`token_usage`**: `int` = `0`
- L37: **`last_activity`**: `datetime` = `Field(default_factory=lambda: datetime.now(timezone.utc))`
- L38: **`prelab_attempts`**: `int` = `0`
- L39: **`idempotency_cache`**: `Dict[str, Dict[str, Any]]` = `{}`
- L40: **`frustration_streak`**: `int` = `0`
- L41: **`hints_revealed`**: `int` = `0`
- L42: **`revealed_hints`**: `List[str]` = `[]`
- L43: **`last_frustration_at`**: `Optional[float]` = `None`
- L44: **`focus_until`**: `Optional[float]` = `None`
- L45: **`highest_hint_level`**: `Optional[str]` = `None`
- L46: **`intervention_notes`**: `List[Dict[str, Any]]` = `Field(default_factory=list)`
- L47: **`grade_payload`**: `Optional[Dict[str, Any]]` = `None`
- L49: **`owner_sub`**: `Optional[str]` = `None`
- L50: **`lab_id`**: `Optional[str]` = `None`
- L52: **`events`**: `List[Dict[str, Any]]` = `Field(default_factory=list)`
- L53: **`summary`**: `Optional[Dict[str, Any]]` = `None`
- L54: **`is_deleted`**: `bool` = `False`
- L55: **`deleted_at`**: `Optional[float]` = `None`

#### Methods

- L57: `def in_focus_mode(self, now: Optional[float]) -> bool`
  - True if focus_until is still in the future.
- L61: `def touch(self)`
  - Updates last_activity to now (UTC).
- L64: `def calculate_lab_score(self) -> int`
  - 0–10 score from fraction of goals done.
- L71: `def all_goals_done(self) -> bool`
  - True when every learning goal is done.

---

## `app/domain/exceptions.py`

**Purpose:** Typed domain errors mapped to HTTP by api/errors.py.

**Layer / role:** Hexagonal core: entities, value objects, domain exceptions, and abstract ports. No FastAPI/DB/HTTP clients.

- **Lines:** 35
- **Imports:** 0 · **Classes:** 6 · **Functions:** 0 · **Module vars:** 0

### Class `UnknownConversation(Exception)`

- **Line:** 1
- **Description:** Raised when conversation id is missing/deleted.

### Class `UnknownMessage(Exception)`

- **Line:** 3
- **Description:** Raised when message id is not in the conversation.

### Class `PrelabRequired(Exception)`

- **Line:** 5
- **Description:** Raised when chat is attempted before pre-lab pass.

#### Methods

- L6: `def __init__(self, language: str)`
  - Defined at line 6.

### Class `TokenBudgetExceeded(Exception)`

- **Line:** 8
- **Description:** Raised when session token budget is exhausted.

#### Methods

- L9: `def __init__(self, language: str, limit: int, used: int)`
  - Defined at line 9.

### Class `HintRevealForbidden(Exception)`

- **Line:** 14
- **Description:** Raised when hint reveal fails streak/quota rules.

#### Methods

- L15: `def __init__(self, reason: str, language: str, streak: int, required_streak: int, hints_used: int, max_hints: int)`
  - Defined at line 15.

### Class `SsrfBlockedError(Exception)`

- **Line:** 31
- **Description:** Raised when a material URL fails SSRF validation.

#### Methods

- L32: `def __init__(self, url: str, reason: str)`
  - Defined at line 32.

---

## `app/domain/ports.py`

**Purpose:** Abstract ports: ConversationRepository, LlmPort, RagPort, CachePort, WebhookPort + LlmResult/RagChunk.

**Layer / role:** Hexagonal core: entities, value objects, domain exceptions, and abstract ports. No FastAPI/DB/HTTP clients.

- **Lines:** 96
- **Imports:** 10 · **Classes:** 7 · **Functions:** 0 · **Module vars:** 0

### Imports

- L1: `from abc import ABC` — stdlib
- L1: `from abc import abstractmethod` — stdlib
- L2: `from typing import Optional` — stdlib
- L2: `from typing import List` — stdlib
- L2: `from typing import Dict` — stdlib
- L2: `from typing import Any` — stdlib
- L2: `from typing import Iterator` — stdlib
- L3: `from pydantic import BaseModel` — validation models
- L4: `from app.domain.conversation import Conversation` — domain types/ports/exceptions
- L5: `from app.domain.sensei import ReferenceMaterial` — domain types/ports/exceptions

### Class `LlmResult(BaseModel)`

- **Line:** 8
- **Description:** Normalized LLM output: content, tokens, model, optional debug.

#### Fields / class variables

- L9: **`raw_content`**: `str`
- L10: **`tokens_used`**: `int`
- L11: **`model`**: `str`
- L12: **`debug_info`**: `Optional[Dict[str, Any]]` = `None`

### Class `RagChunk(BaseModel)`

- **Line:** 14
- **Description:** Retrieved snippet with title/link for citations.

#### Fields / class variables

- L15: **`title`**: `str`
- L16: **`link`**: `str`
- L17: **`snippet`**: `str`

### Class `ConversationRepository(ABC)`

- **Line:** 19
- **Description:** Port: persist/load/list/purge conversations.

#### Methods

- L21: @abstractmethod `def save(self, conversation: Conversation) -> None`
  - Persist or update a Conversation.
- L24: @abstractmethod `def get(self, conversation_id: str) -> Optional[Conversation]`
  - Load Conversation by id, or None.
- L27: @abstractmethod `def delete(self, conversation_id: str) -> bool`
  - Hard-delete by id; return whether it existed.
- L30: @abstractmethod `def purge_expired(self, ttl_seconds: int) -> int`
  - Remove idle sessions older than ttl; return deleted count.
- L33: @abstractmethod `def list_active(self) -> List[Conversation]`
  - Return all non-deleted conversations.
- L37: @abstractmethod `def count_active(self) -> int`
  - Return count of active conversations.

### Class `LlmPort(ABC)`

- **Line:** 40
- **Description:** Port: generate/stream JSON-ish chat completions.

#### Methods

- L42: @abstractmethod `def generate_json(self, system_prompt: str, messages: List[Dict[str, str]], model_override: Optional[str]) -> LlmResult`
  - Run a chat completion; return LlmResult.
- L50: `def stream_json(self, system_prompt: str, messages: List[Dict[str, str]], model_override: Optional[str]) -> Iterator[str]`
  - Default streaming: yield full generate_json content once (adapters may override).
- L55: @abstractmethod `def is_configured(self) -> bool`
  - Whether the LLM backend has enough settings to call.

### Class `RagPort(ABC)`

- **Line:** 58
- **Description:** Port: ingest/retrieve/delete per-conversation materials.

#### Methods

- L60: @abstractmethod `def ingest(self, conversation_id: str, materials: List[ReferenceMaterial]) -> int`
  - Index reference materials for a conversation; return chunk count.
- L64: @abstractmethod `def retrieve(self, conversation_id: str, query: str, top_k: int) -> List[RagChunk]`
  - Return top-k RagChunks for a query.
- L68: @abstractmethod `def delete_conversation(self, conversation_id: str) -> None`
  - Drop indexed materials for a conversation id.
- L72: @abstractmethod `def is_healthy(self) -> bool`
  - Backend health probe for readiness checks.

### Class `CachePort(ABC)`

- **Line:** 76
- **Description:** Port: get/set/clear LLM result cache.

#### Methods

- L78: @abstractmethod `def get(self, key: str) -> Optional[LlmResult]`
  - Fetch cached LlmResult by key, or None.
- L82: @abstractmethod `def set(self, key: str, value: LlmResult) -> None`
  - Store LlmResult under key.
- L86: @abstractmethod `def size(self) -> int`
  - Current number of cache entries.
- L90: @abstractmethod `def clear(self) -> None`
  - Drop all cache entries.

### Class `WebhookPort(ABC)`

- **Line:** 93
- **Description:** Port: send named events to Spring/telemetry.

#### Methods

- L95: @abstractmethod `def send_event(self, event_type: str, payload: Dict[str, Any]) -> bool`
  - Send a named event payload; return success flag.

---

## `app/domain/sensei.py`

**Purpose:** SenseiConfig and nested lab config models (goals, persona, IDE restrictions, prelab, hints).

**Layer / role:** Hexagonal core: entities, value objects, domain exceptions, and abstract ports. No FastAPI/DB/HTTP clients.

- **Lines:** 141
- **Imports:** 10 · **Classes:** 13 · **Functions:** 0 · **Module vars:** 7

### Imports

- L1: `from pydantic import BaseModel` — validation models
- L1: `from pydantic import ConfigDict` — validation models
- L1: `from pydantic import Field` — validation models
- L1: `from pydantic import field_validator` — validation models
- L1: `from pydantic import model_validator` — validation models
- L2: `from pydantic.alias_generators import to_camel` — validation models
- L3: `from typing import List` — stdlib
- L3: `from typing import Optional` — stdlib
- L3: `from typing import Literal` — stdlib
- L3: `from typing import Any` — stdlib

### Module-level variables / constants

- L6: **`MAX_REFERENCE_MATERIALS`** — Cap on reference materials per SenseiConfig (abuse mitigation).
- L7: **`MAX_MATERIAL_CONTENT_CHARS`** — Max characters per material content body.
- L8: **`MAX_CODE_CONTEXT_CHARS`** — Max characters for code/context string fields.
- L9: **`MAX_QUESTION_CHARS`** — Max characters for a student question / prelab answer.
- L10: **`MAX_OPEN_FILES`** — Max open-files entries in CodeContext.
- L11: **`MAX_DIAGNOSTICS`** — Max diagnostics strings in CodeContext.
- L48: **`HintLevel`** — Literal alias for hint ladder levels: nudge | concept | almost.

### Class `DomainModel(BaseModel)`

- **Line:** 14
- **Description:** Base Pydantic model with camelCase aliases for domain payloads.

#### Fields / class variables

- L15: **`model_config`** = `ConfigDict(alias_generator=to_camel, populate_by_name=True)`

### Class `ReferenceMaterial(DomainModel)`

- **Line:** 17
- **Description:** Lab reference material (title, link, optional inline content).

#### Fields / class variables

- L18: **`title`**: `str` = `Field(max_length=500)`
- L19: **`link`**: `str` = `Field(max_length=2000)`
- L20: **`content`**: `Optional[str]` = `Field(default=None, max_length=MAX_MATERIAL_CONTENT_CHARS)`

### Class `Goal(DomainModel)`

- **Line:** 22
- **Description:** Learning goal id + description.

#### Fields / class variables

- L23: **`id`**: `str`
- L24: **`description`**: `str`

### Class `LearningContext(DomainModel)`

- **Line:** 26
- **Description:** Container requiring at least one Goal.

#### Fields / class variables

- L27: **`goals`**: `List[Goal]` = `Field(min_length=1)`

### Class `AgentPersona(DomainModel)`

- **Line:** 29
- **Description:** Assistant name/tone.

#### Fields / class variables

- L30: **`name`**: `str` = `'Sensei'`
- L31: **`tone`**: `str` = `'helpful and socratic'`

### Class `AgentBehavior(DomainModel)`

- **Line:** 33
- **Description:** Mode: theory | debug | review.

#### Fields / class variables

- L34: **`mode`**: `Literal['theory', 'debug', 'review']` = `'theory'`

### Class `IdeRestrictions(DomainModel)`

- **Line:** 36
- **Description:** Allowed/blocked files, require_file_context, pinned identifiers.

#### Fields / class variables

- L37: **`allowed_files`**: `Optional[List[str]]` = `None`
- L38: **`blocked_files`**: `Optional[List[str]]` = `None`
- L39: **`require_file_context`**: `bool` = `False`
- L40: **`pinned_identifiers`**: `List[str]` = `[]`

### Class `Checkpoint(DomainModel)`

- **Line:** 42
- **Description:** Pedagogy checkpoint unlocked after a goal; optional hint.

#### Fields / class variables

- L43: **`id`**: `str`
- L44: **`after_goal`**: `str`
- L45: **`hint`**: `Optional[str]` = `None`

### Class `HintStep(DomainModel)`

- **Line:** 51
- **Description:** One rung on the hint ladder (level + text).

#### Fields / class variables

- L52: **`level`**: `HintLevel` = `'nudge'`
- L53: **`text`**: `str`

### Class `PreLabQuestion(DomainModel)`

- **Line:** 56
- **Description:** Pre-lab question with expected keyword list.

#### Fields / class variables

- L57: **`id`**: `str`
- L58: **`question`**: `str`
- L59: **`expected_keywords`**: `List[str]` = `[]`

### Class `PreLabConfig(DomainModel)`

- **Line:** 61
- **Description:** Enablement, attempts, hint, and questions for entrance quiz.

#### Fields / class variables

- L62: **`enabled`**: `bool` = `False`
- L63: **`max_attempts`**: `int` = `3`
- L64: **`hint_after_fail`**: `Optional[str]` = `None`
- L65: **`questions`**: `List[PreLabQuestion]` = `[]`

#### Methods

- L68: @model_validator(mode='after') `def require_keywords_when_enabled(self) -> 'PreLabConfig'`
  - When preLab on, each question needs expectedKeywords.

### Class `SenseiConfig(DomainModel)`

- **Line:** 82
- **Description:** Full lab configuration document for a conversation.

#### Fields / class variables

- L83: **`language`**: `Literal['pl', 'en']` = `'pl'`
- L84: **`evaluation_criteria`**: `str`
- L85: **`max_tokens_per_session`**: `Optional[int]` = `80000`
- L86: **`reference_materials`**: `List[ReferenceMaterial]` = `Field(default_factory=list, max_length=MAX_REFERENCE_MATERIALS)`
- L87: **`learning_context`**: `LearningContext`
- L88: **`agent_persona`**: `AgentPersona`
- L89: **`agent_behavior`**: `AgentBehavior`
- L90: **`ide_restrictions`**: `IdeRestrictions` = `Field(default_factory=IdeRestrictions)`
- L91: **`checkpoints`**: `List[Checkpoint]` = `[]`
- L92: **`pre_lab`**: `PreLabConfig` = `Field(default_factory=PreLabConfig)`
- L93: **`require_file_context`**: `bool` = `False`
- L94: **`pinned_identifiers`**: `List[str]` = `[]`
- L95: **`hints`**: `List[str]` = `[]`
- L96: **`hint_ladder`**: `List[HintStep]` = `Field(default_factory=list)`
- L97: **`max_hints`**: `int` = `3`
- L98: **`frustration_threshold`**: `int` = `2`
- L99: **`focus_mode_seconds`**: `int` = `180`
- L100: **`auto_debug_on_errors`**: `bool` = `True`
- L101: **`solution_pack`**: `List[str]` = `Field(default_factory=list, max_length=20)`

#### Methods

- L105: @field_validator('max_tokens_per_session', mode='before') @classmethod `def default_token_budget(cls, v: Any) -> int`
  - Coerces null max_tokens_per_session to 80_000.
- L111: @model_validator(mode='after') `def validate_checkpoints(self) -> 'SenseiConfig'`
  - Ensures checkpoints reference existing goals; syncs IDE flags.
- L124: `def resolved_hint_texts(self) -> List[str]`
  - Hint texts from hint_ladder or legacy hints list.
- L129: `def resolved_hint_levels(self) -> List[str]`
  - Levels aligned with resolved_hint_texts.

### Class `CodeContext(DomainModel)`

- **Line:** 134
- **Description:** IDE snapshot sent with a student question.

#### Fields / class variables

- L135: **`current_file_name`**: `Optional[str]` = `None`
- L136: **`current_code`**: `Optional[str]` = `Field(default=None, max_length=MAX_CODE_CONTEXT_CHARS)`
- L137: **`error_logs`**: `Optional[str]` = `Field(default=None, max_length=MAX_CODE_CONTEXT_CHARS)`
- L138: **`selection`**: `Optional[str]` = `Field(default=None, max_length=MAX_CODE_CONTEXT_CHARS)`
- L139: **`diagnostics`**: `List[str]` = `Field(default_factory=list, max_length=MAX_DIAGNOSTICS)`
- L140: **`open_files`**: `List[str]` = `Field(default_factory=list, max_length=MAX_OPEN_FILES)`

---

# app/application

Use cases / services: orchestrate domain logic via ports. Framework-agnostic.

## `app/application/access.py`

**Purpose:** Professor role check and conversation ownership (JWT sub) enforcement.

**Layer / role:** Use cases / services: orchestrate domain logic via ports. Framework-agnostic.

- **Lines:** 36
- **Imports:** 6 · **Classes:** 0 · **Functions:** 2 · **Module vars:** 0

### Imports

- L1: `from typing import Any` — stdlib
- L1: `from typing import Dict` — stdlib
- L1: `from typing import Optional` — stdlib
- L3: `from app.core.config import settings` — settings
- L4: `from app.domain.conversation import Conversation` — domain types/ports/exceptions
- L5: `from app.domain.exceptions import UnknownConversation` — domain types/ports/exceptions

### Functions

- L8: `def require_professor(claims: Optional[Dict[str, Any]]) -> bool`
  - True if JWT claims include a configured professor/admin role.
- L25: `def ensure_conversation_access(conv: Conversation, claims: Optional[Dict[str, Any]]) -> None`
  - Raises/blocks if JWT sub does not own the conversation (when auth on).

---

## `app/application/cache_keys.py`

**Purpose:** Stable hash key for LLM cache entries.

**Layer / role:** Use cases / services: orchestrate domain logic via ports. Framework-agnostic.

- **Lines:** 17
- **Imports:** 4 · **Classes:** 0 · **Functions:** 1 · **Module vars:** 0

### Imports

- L1: `import hashlib` — stdlib
- L2: `import json` — stdlib
- L3: `from typing import Dict` — stdlib
- L3: `from typing import List` — stdlib

### Functions

- L6: `def build_cache_key(system_prompt: str, messages: List[Dict[str, str]], model: str) -> str`
  - SHA-based cache key from system prompt + messages + model.

---

## `app/application/chat_service.py`

**Purpose:** Core chat use case: security + pedagogy gates, RAG, cache, LLM, checkpoints, hints, feedback, streaming.

**Layer / role:** Use cases / services: orchestrate domain logic via ports. Framework-agnostic.

- **Lines:** 661
- **Imports:** 39 · **Classes:** 1 · **Functions:** 0 · **Module vars:** 1

### Imports

- L1: `import json` — stdlib
- L2: `import re` — stdlib
- L3: `import time` — stdlib
- L4: `import uuid` — stdlib
- L5: `from typing import Dict` — stdlib
- L5: `from typing import List` — stdlib
- L5: `from typing import Optional` — stdlib
- L5: `from typing import Any` — stdlib
- L5: `from typing import Iterator` — stdlib
- L5: `from typing import Tuple` — stdlib
- L6: `from app.domain.conversation import Conversation` — domain types/ports/exceptions
- L6: `from app.domain.conversation import ChatMessage` — domain types/ports/exceptions
- L6: `from app.domain.conversation import MessageFeedback` — domain types/ports/exceptions
- L7: `from app.domain.ports import ConversationRepository` — domain types/ports/exceptions
- L7: `from app.domain.ports import LlmPort` — domain types/ports/exceptions
- L7: `from app.domain.ports import LlmResult` — domain types/ports/exceptions
- L7: `from app.domain.ports import RagPort` — domain types/ports/exceptions
- L7: `from app.domain.ports import CachePort` — domain types/ports/exceptions
- L7: `from app.domain.ports import WebhookPort` — domain types/ports/exceptions
- L14: `from app.domain.exceptions import UnknownMessage` — domain types/ports/exceptions
- L14: `from app.domain.exceptions import TokenBudgetExceeded` — domain types/ports/exceptions
- L14: `from app.domain.exceptions import HintRevealForbidden` — domain types/ports/exceptions
- L15: `from app.application.session_service import SessionService` — application services/DTOs
- L16: `from app.application.prompts import build_system_prompt` — application services/DTOs
- L16: `from app.application.prompts import build_user_prompt` — application services/DTOs
- L17: `from app.application.response_pipeline import ResponsePipeline` — application services/DTOs
- L17: `from app.application.response_pipeline import GIVEAWAY_REQUEST_RE` — application services/DTOs
- L18: `from app.application.security import SecurityGuard` — application services/DTOs
- L19: `from app.application.pedagogy_gates import PedagogyGates` — application services/DTOs
- L20: `from app.application.cache_keys import build_cache_key` — application services/DTOs
- L21: `from app.core.config import settings` — settings
- L22: `from app.application.dto import MessageRequest` — application services/DTOs
- L22: `from app.application.dto import MessageResponse` — application services/DTOs
- L22: `from app.application.dto import GoalProgressEntryDTO` — application services/DTOs
- L22: `from app.application.dto import FeedbackRequest` — application services/DTOs
- L22: `from app.application.dto import FeedbackResponse` — application services/DTOs
- L22: `from app.application.dto import HintRevealResponse` — application services/DTOs
- L30: `from app.application.metrics import metrics` — application services/DTOs
- L31: `from app.application.grade_payload import build_grade_sync_payload` — application services/DTOs

### Module-level variables / constants

- L33: **`_CONCEPT_Q_RE`** — Regex detecting conceptual questions about a symbol/identifier.

### Class `ChatService`

- **Line:** 38
- **Description:** Primary chat orchestration use case.

#### Methods

- L39: `def __init__(self, repo: ConversationRepository, session_svc: SessionService, llm: LlmPort, pipeline: Optional[ResponsePipeline], security_guard: Optional[SecurityGuard], pedagogy_gates: Optional[PedagogyGates], rag: Optional[RagPort], cache: Optional[CachePort], webhooks: Optional[WebhookPort])`
  - Wires repo, session, LLM, pipeline, security, pedagogy, RAG, cache, webhooks.
- L61: `def list_messages(self, conv_id: str) -> List[Dict[str, Any]]`
  - Returns serialized message history for a conversation.
- L65: `def _emit_message_webhook(self, conv: Conversation, response_obj: MessageResponse) -> None`
  - Fires `message` webhook with scores/tokens metadata.
- L80: `def _build_gate_response(self, conv: Conversation, req: MessageRequest, gate_message_id: str, answer: str, feedback: str, next_step: str, penalty: bool, debug_info: Dict[str, Any]) -> MessageResponse`
  - Persists a synthetic assistant reply when a gate blocks the LLM.
- L141: `def _prepare_turn(self, conv_id: str, req: MessageRequest) -> Tuple[Conversation, Optional[MessageResponse], str, List[Dict[str, str]], List[str]]`
  - Loads session, idempotency, token budget, prompts, RAG sources, history.
- L246: `def _finalize_response(self, conv: Conversation, req: MessageRequest, system_prompt: str, history_messages: List[Dict[str, str]], llm_result: LlmResult, sources: Optional[List[str]]) -> MessageResponse`
  - Parses LLM output, updates goals/checkpoints/tokens, saves, webhooks.
- L438: `def send_message(self, conv_id: str, req: MessageRequest) -> MessageResponse`
  - Full chat turn: gates → cache/LLM → pipeline → MessageResponse.
- L461: `def stream_message(self, conv_id: str, req: MessageRequest) -> Iterator[str]`
  - Same as send_message but yields streamed tokens then final JSON.
- L514: `def reveal_hint(self, conv_id: str) -> HintRevealResponse`
  - Student hint reveal gated by frustration streak and max_hints.
- L579: `def force_reveal_hint(self, conv_id: str, reason: Optional[str], custom_hint: Optional[str], hint_level: Optional[str]) -> HintRevealResponse`
  - Professor override to reveal/custom inject a hint.
- L654: `def add_feedback(self, conv_id: str, message_id: str, req: FeedbackRequest) -> FeedbackResponse`
  - Attaches 1–5 rating (+ optional comment) to an assistant message.

---

## `app/application/config_dry_run.py`

**Purpose:** Validates a SenseiConfig and reports dry-run diagnostics without starting a session.

**Layer / role:** Use cases / services: orchestrate domain logic via ports. Framework-agnostic.

- **Lines:** 128
- **Imports:** 11 · **Classes:** 0 · **Functions:** 1 · **Module vars:** 0

### Imports

- L1: `from __future__ import annotations`
- L3: `from typing import Any` — stdlib
- L3: `from typing import Dict` — stdlib
- L3: `from typing import List` — stdlib
- L5: `from app.application.pedagogy_gates import PedagogyGates` — application services/DTOs
- L6: `from app.application.prelab_service import _keyword_hit` — application services/DTOs
- L7: `from app.application.security import SecurityGuard` — application services/DTOs
- L8: `from app.domain.exceptions import SsrfBlockedError` — domain types/ports/exceptions
- L9: `from app.domain.sensei import CodeContext` — domain types/ports/exceptions
- L9: `from app.domain.sensei import SenseiConfig` — domain types/ports/exceptions
- L10: `from app.infrastructure.rag_chroma import validate_safe_url` — infrastructure adapters

### Functions

- L13: `def run_config_dry_run(config: SenseiConfig) -> Dict[str, Any]`
  - Validates SenseiConfig and returns warnings/stats without persisting.

---

## `app/application/dto.py`

**Purpose:** API request/response Pydantic DTOs (camelCase aliases in, snake_case out).

**Layer / role:** Use cases / services: orchestrate domain logic via ports. Framework-agnostic.

- **Lines:** 216
- **Imports:** 15 · **Classes:** 20 · **Functions:** 0 · **Module vars:** 0

### Imports

- L1: `from typing import Optional` — stdlib
- L1: `from typing import List` — stdlib
- L1: `from typing import Dict` — stdlib
- L1: `from typing import Any` — stdlib
- L2: `from pydantic import BaseModel` — validation models
- L2: `from pydantic import Field` — validation models
- L2: `from pydantic import ConfigDict` — validation models
- L2: `from pydantic import field_validator` — validation models
- L2: `from pydantic import model_validator` — validation models
- L4: `from app.domain.sensei import CodeContext` — domain types/ports/exceptions
- L4: `from app.domain.sensei import SenseiConfig` — domain types/ports/exceptions
- L4: `from app.domain.sensei import MAX_CODE_CONTEXT_CHARS` — domain types/ports/exceptions
- L4: `from app.domain.sensei import MAX_DIAGNOSTICS` — domain types/ports/exceptions
- L4: `from app.domain.sensei import MAX_OPEN_FILES` — domain types/ports/exceptions
- L4: `from app.domain.sensei import MAX_QUESTION_CHARS` — domain types/ports/exceptions

### Class `ApiModel(BaseModel)`

- **Line:** 14
- **Description:** Base API DTO (populate_by_name, ignore extras).

#### Fields / class variables

- L15: **`model_config`** = `ConfigDict(populate_by_name=True, extra='ignore', ser_json_by_alias=False)`

### Class `CodeContextDTO(ApiModel)`

- **Line:** 23
- **Description:** API code-context with camelCase aliases; normalizes legacy fields.

#### Fields / class variables

- L24: **`current_code`**: `Optional[str]` = `Field(default=None, alias='currentCode', max_length=MAX_CODE_CONTEXT_CHARS)`
- L27: **`code_snippet`**: `Optional[str]` = `Field(default=None, alias='codeSnippet', max_length=MAX_CODE_CONTEXT_CHARS)`
- L30: **`current_file_name`**: `Optional[str]` = `Field(default=None, alias='currentFileName', max_length=500)`
- L31: **`file_path`**: `Optional[str]` = `Field(default=None, alias='filePath', max_length=500)`
- L32: **`selection`**: `Optional[str]` = `Field(default=None, max_length=MAX_CODE_CONTEXT_CHARS)`
- L33: **`selected_text`**: `Optional[str]` = `Field(default=None, alias='selectedText', max_length=MAX_CODE_CONTEXT_CHARS)`
- L36: **`error_logs`**: `Optional[str]` = `Field(default=None, alias='errorLogs', max_length=MAX_CODE_CONTEXT_CHARS)`
- L39: **`diagnostics`**: `List[str]` = `Field(default_factory=list, max_length=MAX_DIAGNOSTICS)`
- L40: **`open_files`**: `List[str]` = `Field(default_factory=list, alias='openFiles', max_length=MAX_OPEN_FILES)`

#### Methods

- L45: @model_validator(mode='after') `def normalize(self) -> 'CodeContextDTO'`
  - Defined at line 45. Returns `'CodeContextDTO'`.
- L51: `def to_domain(self) -> CodeContext`
  - Defined at line 51. Returns `CodeContext`.

### Class `PrelabQuestionDTO(ApiModel)`

- **Line:** 62
- **Description:** Pydantic model (ApiModel) representing structured data.

#### Fields / class variables

- L63: **`id`**: `str`
- L64: **`question`**: `str`
- L65: **`hint`**: `Optional[str]` = `None`

### Class `PrelabStatusResponse(ApiModel)`

- **Line:** 68
- **Description:** Pydantic model (ApiModel) representing structured data.

#### Fields / class variables

- L69: **`enabled`**: `bool` = `False`
- L70: **`passed`**: `bool` = `False`
- L71: **`completed`**: `bool` = `False`
- L72: **`questions`**: `List[PrelabQuestionDTO]` = `Field(default_factory=list)`
- L73: **`attempts`**: `int` = `0`
- L74: **`max_attempts`**: `Optional[int]` = `None`
- L75: **`remaining_attempts`**: `Optional[int]` = `None`
- L76: **`hint_after_fail`**: `Optional[str]` = `None`

### Class `PrelabSubmitResponse(ApiModel)`

- **Line:** 79
- **Description:** Pydantic model (ApiModel) representing structured data.

#### Fields / class variables

- L80: **`passed`**: `bool`
- L81: **`unlocked`**: `bool` = `False`
- L82: **`failed_ids`**: `List[str]` = `Field(default_factory=list)`
- L83: **`feedback`**: `Optional[str]` = `None`
- L84: **`attempts`**: `int` = `0`
- L85: **`remaining_attempts`**: `Optional[int]` = `None`
- L86: **`prelab_completed`**: `bool` = `False`

### Class `PrelabAnswerItem(ApiModel)`

- **Line:** 89
- **Description:** Pydantic model (ApiModel) representing structured data.

#### Fields / class variables

- L90: **`id`**: `str` = `'q1'`
- L91: **`answer`**: `str` = `Field(max_length=MAX_QUESTION_CHARS)`

#### Methods

- L95: @field_validator('answer', mode='before') @classmethod `def validate_answer_text(cls, v: Any) -> str`
  - Defined at line 95. Returns `str`.

### Class `PrelabSubmitRequest(ApiModel)`

- **Line:** 101
- **Description:** Pydantic model (ApiModel) representing structured data.

#### Fields / class variables

- L102: **`answers`**: `List[PrelabAnswerItem]`

#### Methods

- L106: @model_validator(mode='before') @classmethod `def normalize_answers(cls, data: Any) -> Any`
  - Defined at line 106. Returns `Any`.

### Class `ConfigValidationRequest(ApiModel)`

- **Line:** 117
- **Description:** Pydantic model (ApiModel) representing structured data.

#### Fields / class variables

- L118: **`config`**: `Dict[str, Any]`

### Class `ConversationStartRequest(ApiModel)`

- **Line:** 121
- **Description:** Pydantic model (ApiModel) representing structured data.

#### Fields / class variables

- L122: **`config`**: `SenseiConfig`

### Class `MessageRequest(ApiModel)`

- **Line:** 125
- **Description:** Pydantic model (ApiModel) representing structured data.

#### Fields / class variables

- L126: **`question`**: `str` = `Field(max_length=MAX_QUESTION_CHARS)`
- L127: **`code_context`**: `Optional[CodeContextDTO]` = `Field(default=None, alias='codeContext')`
- L128: **`client_message_id`**: `Optional[str]` = `Field(default=None, alias='clientMessageId', max_length=200)`

#### Methods

- L132: @field_validator('question', mode='before') @classmethod `def validate_non_empty_question(cls, v: Any) -> str`
  - Defined at line 132. Returns `str`.

### Class `GoalProgressEntryDTO(ApiModel)`

- **Line:** 138
- **Description:** Pydantic model (ApiModel) representing structured data.

#### Fields / class variables

- L139: **`goal`**: `str`
- L140: **`status`**: `str`

### Class `NextCheckpointDTO(ApiModel)`

- **Line:** 143
- **Description:** Pydantic model (ApiModel) representing structured data.

#### Fields / class variables

- L144: **`id`**: `str`
- L145: **`hint`**: `Optional[str]` = `None`
- L146: **`after_goal`**: `Optional[str]` = `Field(default=None, alias='afterGoal')`
- L147: **`unlocked`**: `bool` = `False`

### Class `MessageResponse(ApiModel)`

- **Line:** 150
- **Description:** Pydantic model (ApiModel) representing structured data.

#### Fields / class variables

- L151: **`message_id`**: `str`
- L152: **`answer`**: `str`
- L153: **`prompt_score`**: `int`
- L154: **`prompt_feedback`**: `str`
- L155: **`tokens_used`**: `int`
- L156: **`penalty_applied`**: `bool`
- L157: **`sources`**: `List[str]` = `Field(default_factory=list)`
- L158: **`suggested_next_step`**: `Optional[str]` = `None`
- L159: **`goal_progress`**: `List[GoalProgressEntryDTO]` = `Field(default_factory=list)`
- L160: **`lab_score`**: `int` = `0`
- L161: **`next_checkpoint`**: `Optional[NextCheckpointDTO]` = `None`
- L162: **`model`**: `str` = `'default'`
- L163: **`debug_info`**: `Optional[Dict[str, Any]]` = `None`
- L164: **`tutoring_mode`**: `Optional[str]` = `None`
- L165: **`checkpoint_celebration`**: `Optional[str]` = `None`
- L166: **`concept_card`**: `Optional[Dict[str, Any]]` = `None`
- L167: **`in_focus_mode`**: `bool` = `False`

### Class `EventRequest(ApiModel)`

- **Line:** 170
- **Description:** Pydantic model (ApiModel) representing structured data.

#### Fields / class variables

- L171: **`type`**: `str` = `Field(max_length=100)`
- L172: **`meta`**: `Optional[Dict[str, Any]]` = `None`

### Class `HintRevealResponse(ApiModel)`

- **Line:** 175
- **Description:** Pydantic model (ApiModel) representing structured data.

#### Fields / class variables

- L176: **`hint`**: `str`
- L177: **`hints_used`**: `int`
- L178: **`max_hints`**: `int`
- L179: **`hints_remaining`**: `int`
- L180: **`frustration_streak_reset`**: `bool` = `True`
- L181: **`forced`**: `bool` = `False`
- L182: **`hint_level`**: `Optional[str]` = `None`

### Class `FeedbackRequest(ApiModel)`

- **Line:** 185
- **Description:** Pydantic model (ApiModel) representing structured data.

#### Fields / class variables

- L186: **`rating`**: `int` = `Field(..., ge=1, le=5)`
- L187: **`comment`**: `Optional[str]` = `Field(default=None, max_length=2000)`

### Class `FeedbackResponse(ApiModel)`

- **Line:** 190
- **Description:** Pydantic model (ApiModel) representing structured data.

#### Fields / class variables

- L191: **`status`**: `str`
- L192: **`message_id`**: `str`
- L193: **`rating`**: `int`

### Class `SessionSummaryResponse(ApiModel)`

- **Line:** 196
- **Description:** Pydantic model (ApiModel) representing structured data.

#### Fields / class variables

- L197: **`conversation_id`**: `str`
- L198: **`summary`**: `str`
- L199: **`lab_score`**: `int`
- L200: **`goal_progress`**: `List[GoalProgressEntryDTO]`
- L201: **`tokens_used`**: `int`
- L202: **`messages_count`**: `int`
- L203: **`hints_used`**: `int`
- L204: **`events_count`**: `int`
- L205: **`completed`**: `bool`

### Class `RagMaterialPreviewDTO(ApiModel)`

- **Line:** 208
- **Description:** Pydantic model (ApiModel) representing structured data.

#### Fields / class variables

- L209: **`title`**: `str`
- L210: **`link`**: `str`

### Class `RagPreviewDTO(ApiModel)`

- **Line:** 213
- **Description:** Pydantic model (ApiModel) representing structured data.

#### Fields / class variables

- L214: **`chunks_ingested`**: `int` = `0`
- L215: **`materials`**: `List[RagMaterialPreviewDTO]` = `Field(default_factory=list)`

---

## `app/application/grade_payload.py`

**Purpose:** Builds grade-sync payload for Spring when lab completes.

**Layer / role:** Use cases / services: orchestrate domain logic via ports. Framework-agnostic.

- **Lines:** 43
- **Imports:** 6 · **Classes:** 0 · **Functions:** 1 · **Module vars:** 1

### Imports

- L1: `from __future__ import annotations`
- L3: `import time` — stdlib
- L4: `from typing import Any` — stdlib
- L4: `from typing import Dict` — stdlib
- L4: `from typing import Optional` — stdlib
- L6: `from app.domain.conversation import Conversation` — domain types/ports/exceptions

### Module-level variables / constants

- L8: **`GRADE_SCHEMA_VERSION`** — Module/class constant or field. Default/value: `'1.0'`.

### Functions

- L11: `def build_grade_sync_payload(conv: Conversation) -> Dict[str, Any]`
  - Payload for Spring grade sync (scores, goals, hints, tokens).

---

## `app/application/metrics.py`

**Purpose:** In-process counters for requests/errors/LLM/webhooks.

**Layer / role:** Use cases / services: orchestrate domain logic via ports. Framework-agnostic.

- **Lines:** 51
- **Imports:** 2 · **Classes:** 1 · **Functions:** 0 · **Module vars:** 1

### Imports

- L1: `from threading import Lock` — stdlib
- L2: `from typing import Dict` — stdlib

### Module-level variables / constants

- L50: **`metrics`** — Process-wide MetricsRegistry singleton for counters exposed on ops endpoints.

### Class `MetricsRegistry`

- **Line:** 5
- **Description:** In-process metric counters.

#### Methods

- L6: `def __init__(self) -> None`
  - Defined at line 6. Returns `None`.
- L15: `def inc_requests(self) -> None`
  - Increment HTTP request counter.
- L19: `def inc_errors(self) -> None`
  - Increment error counter.
- L23: `def inc_llm_rate_limited(self) -> None`
  - Increment LLM 429 counter.
- L27: `def inc_messages(self) -> None`
  - Increment chat message counter.
- L31: `def inc_webhook(self, ok: bool) -> None`
  - Increment webhook success/fail counters.
- L38: `def snapshot(self) -> Dict[str, int]`
  - Dict snapshot of all counters.

---

## `app/application/pedagogy_gates.py`

**Purpose:** IDE file allow/block/require-context and pinned-identifier gates before LLM.

**Layer / role:** Use cases / services: orchestrate domain logic via ports. Framework-agnostic.

- **Lines:** 206
- **Imports:** 7 · **Classes:** 2 · **Functions:** 2 · **Module vars:** 1

### Imports

- L1: `import re` — stdlib
- L2: `from pathlib import PurePosixPath` — stdlib
- L3: `from typing import Optional` — stdlib
- L3: `from typing import List` — stdlib
- L5: `from pydantic import BaseModel` — validation models
- L6: `from app.domain.sensei import SenseiConfig` — domain types/ports/exceptions
- L6: `from app.domain.sensei import CodeContext` — domain types/ports/exceptions

### Module-level variables / constants

- L8: **`GIVEAWAY_PATTERNS`** — Module/class constant or field. Default/value: `[re.compile('napisz\\s+(za\\s+mnie|mi)\\s+(?:cały\\s+)?(?:kompletny\\s+|gotowy\\s+)?kod', re.IGNORECASE), re.compile(...`.

### Class `PedagogyGateResult(BaseModel)`

- **Line:** 37
- **Description:** Allow/block + message from PedagogyGates.

#### Fields / class variables

- L38: **`rejected`**: `bool`
- L39: **`reason_code`**: `Optional[str]` = `None`
- L40: **`answer`**: `Optional[str]` = `None`
- L41: **`prompt_feedback`**: `Optional[str]` = `None`
- L42: **`suggested_next_step`**: `Optional[str]` = `None`
- L43: **`penalty_applied`**: `bool` = `False`

### Class `PedagogyGates`

- **Line:** 46
- **Description:** IDE and pinned-identifier enforcement before LLM.

#### Methods

- L47: `def evaluate(self, config: SenseiConfig, question: str, code_context: Optional[CodeContext]) -> PedagogyGateResult`
  - Enforces IDE file/context/pinned-identifier rules; may block turn.

### Functions

- L17: `def _basename(path: Optional[str]) -> str`
  - File basename helper for restriction matching.
- L23: `def _collect_file_names(code_context: Optional[CodeContext]) -> List[str]`
  - Collects file names from CodeContext for gate checks.

---

## `app/application/prelab_service.py`

**Purpose:** Pre-lab quiz status and keyword-based submit grading.

**Layer / role:** Use cases / services: orchestrate domain logic via ports. Framework-agnostic.

- **Lines:** 157
- **Imports:** 10 · **Classes:** 1 · **Functions:** 2 · **Module vars:** 0

### Imports

- L1: `import re` — stdlib
- L2: `from typing import List` — stdlib
- L2: `from typing import Dict` — stdlib
- L2: `from typing import Any` — stdlib
- L4: `from app.application.dto import PrelabStatusResponse` — application services/DTOs
- L4: `from app.application.dto import PrelabSubmitRequest` — application services/DTOs
- L4: `from app.application.dto import PrelabQuestionDTO` — application services/DTOs
- L4: `from app.application.dto import PrelabSubmitResponse` — application services/DTOs
- L10: `from app.domain.conversation import Conversation` — domain types/ports/exceptions
- L11: `from app.domain.ports import ConversationRepository` — domain types/ports/exceptions

### Class `PrelabService`

- **Line:** 25
- **Description:** Pre-lab quiz use case.

#### Methods

- L26: `def __init__(self, repo: ConversationRepository)`
  - Defined at line 26.
- L29: `def get_status(self, conv: Conversation) -> PrelabStatusResponse`
  - Builds PrelabStatusResponse (questions without expected keywords).
- L63: `def submit(self, conv: Conversation, req: PrelabSubmitRequest) -> Dict[str, Any]`
  - Grades answers vs expected_keywords; unlocks chat when passed.

### Functions

- L14: `def _msg(language: str, pl: str, en: str) -> str`
  - Picks PL/EN user-facing string by language.
- L18: `def _keyword_hit(keyword: str, answer: str) -> bool`
  - Case-insensitive keyword presence check in an answer.

---

## `app/application/prompts.py`

**Purpose:** Builds system/user prompts from SenseiConfig, progress, and RAG chunks.

**Layer / role:** Use cases / services: orchestrate domain logic via ports. Framework-agnostic.

- **Lines:** 133
- **Imports:** 8 · **Classes:** 0 · **Functions:** 2 · **Module vars:** 2

### Imports

- L1: `import json` — stdlib
- L2: `from typing import Optional` — stdlib
- L2: `from typing import List` — stdlib
- L4: `from app.domain.ports import RagChunk` — domain types/ports/exceptions
- L5: `from app.domain.sensei import SenseiConfig` — domain types/ports/exceptions
- L5: `from app.domain.sensei import CodeContext` — domain types/ports/exceptions
- L6: `from app.domain.conversation import GoalStatus` — domain types/ports/exceptions
- L7: `from typing import Dict` — stdlib

### Module-level variables / constants

- L9: **`MODE_INSTRUCTIONS_PL`** — Module/class constant or field. Default/value: `{'theory': 'Skup się na wyjaśnieniu pojęć, architektury i koncepcji poprzez pytania naprowadzające.', 'debug': 'Pomóż...`.
- L15: **`MODE_INSTRUCTIONS_EN`** — Module/class constant or field. Default/value: `{'theory': 'Focus on explaining concepts and architecture using guiding Socratic questions.', 'debug': 'Help the stud...`.

### Functions

- L21: `def build_system_prompt(config: SenseiConfig, current_progress: Dict[str, GoalStatus], rag_chunks: Optional[List[RagChunk]], mode_override: Optional[str]) -> str`
  - Composes socratic system prompt from config, progress, RAG, mode.
- L115: `def build_user_prompt(question: str, code_context: Optional[CodeContext]) -> str`
  - Formats student question + code context for the user message.

---

## `app/application/response_pipeline.py`

**Purpose:** Parse/normalize LLM JSON, language drift, code-giveaway penalty, goals/checkpoints.

**Layer / role:** Use cases / services: orchestrate domain logic via ports. Framework-agnostic.

- **Lines:** 209
- **Imports:** 11 · **Classes:** 1 · **Functions:** 0 · **Module vars:** 6

### Imports

- L1: `import json` — stdlib
- L2: `import re` — stdlib
- L3: `from typing import Dict` — stdlib
- L3: `from typing import Any` — stdlib
- L3: `from typing import List` — stdlib
- L3: `from typing import Optional` — stdlib
- L3: `from typing import Tuple` — stdlib
- L4: `from app.domain.conversation import Conversation` — domain types/ports/exceptions
- L4: `from app.domain.conversation import GoalStatus` — domain types/ports/exceptions
- L5: `from app.application.dto import GoalProgressEntryDTO` — application services/DTOs
- L5: `from app.application.dto import NextCheckpointDTO` — application services/DTOs

### Module-level variables / constants

- L7: **`STATUS_RANK`** — Module/class constant or field. Type: `Dict[GoalStatus, int]`. Default/value: `{'not_started': 0, 'in_progress': 1, 'done': 2}`.
- L13: **`PL_DIACRITICS_RE`** — Module/class constant or field. Default/value: `re.compile('[ąćęłńóśźżĄĆĘŁŃÓŚŹŻ]')`.
- L15: **`PL_WORDS_RE`** — Module/class constant or field. Default/value: `re.compile('\\b(jest|nie|się|oraz|czy|jak|kod|że|aby|przez|tylko|funkcj\\w*|klas\\w*)\\b', re.IGNORECASE)`.
- L21: **`EN_WORDS_RE`** — Module/class constant or field. Default/value: `re.compile('\\b(the|and|you|should|this|that|your|with|from|have|what|where|because|please|check|code|is|are|a|an|for...`.
- L26: **`GIVEAWAY_REQUEST_RE`** — Regex detecting student requests for full solutions (anti-bypass).
- L30: **`CODE_BLOCK_RE`** — Module/class constant or field. Default/value: `re.compile('```(?:[a-zA-Z0-9_+-]+)?\\s*\\n(.*?)```', re.DOTALL)`.

### Class `ResponsePipeline`

- **Line:** 33
- **Description:** Post-LLM parsing, penalties, goals, checkpoints.

#### Methods

- L35: `def extract_json(self, raw_text: str) -> Tuple[Optional[Dict[str, Any]], bool]`
  - Extracts JSON object from raw LLM text (fences/brace scan).
- L63: `def build_fallback_payload(self, raw_text: str, conv: Conversation) -> Dict[str, Any]`
  - Safe fallback structure when LLM JSON is invalid.
- L96: `def has_language_drift(self, answer: str, expected_language: str) -> bool`
  - Detects answer language mismatch vs config.language.
- L117: `def apply_code_penalty(self, answer: str, question: str, prompt_score: int, penalty_applied: bool) -> Tuple[int, bool]`
  - Penalizes answers that look like full solutions / giveaways.
- L141: `def normalize_goals(self, conv: Conversation, raw_goals: Any) -> List[GoalProgressEntryDTO]`
  - Merges LLM goal updates into conversation.goal_progress.
- L179: `def evaluate_checkpoints(self, conv: Conversation) -> Optional[NextCheckpointDTO]`
  - Unlocks checkpoints after completed goals; returns next hint.

---

## `app/application/security.py`

**Purpose:** Jailbreak/injection guard (rules + optional SECURITY_MODEL LLM classify).

**Layer / role:** Use cases / services: orchestrate domain logic via ports. Framework-agnostic.

- **Lines:** 190
- **Imports:** 6 · **Classes:** 2 · **Functions:** 1 · **Module vars:** 5

### Imports

- L1: `import json` — stdlib
- L2: `import re` — stdlib
- L3: `from typing import Optional` — stdlib
- L4: `from pydantic import BaseModel` — validation models
- L5: `from app.domain.ports import LlmPort` — domain types/ports/exceptions
- L6: `from app.core.config import settings` — settings

### Module-level variables / constants

- L9: **`JAILBREAK_REGEXES`** — Module/class constant or field. Default/value: `[re.compile('ignore\\s+(all\\s+)?(previous|prior|above|system)\\s+instructions', re.IGNORECASE), re.compile('disregar...`.
- L21: **`ROLE_SPOOFING_RE`** — Module/class constant or field. Default/value: `re.compile('(<\\|im_start\\|>|<\\|im_end\\|>|<\\|system\\|>|\\[INST\\]|\\[/INST\\]|###\\s*System:|SYSTEM\\s+OVERRIDE)...`.
- L27: **`SUSPICIOUS_BYPASS_RE`** — Module/class constant or field. Default/value: `re.compile('(udawaj\\s+że\\s+nie\\s+jesteś|pretend\\s+you\\s+are\\s+not|act\\s+as\\s+an\\s+unrestricted|hipotetycznie...`.
- L33: **`SOLUTION_GIVEAWAY_REGEXES`** — Module/class constant or field. Default/value: `[re.compile('(napisz|podaj|wklej)\\s+(mi\\s+)?(całe|pełne|gotowe)\\s+(rozwiązanie|zadanie|kod)', re.IGNORECASE), re.c...`.
- L48: **`BASE64_BLOB_RE`** — Module/class constant or field. Default/value: `re.compile('\\b[A-Za-z0-9+/]{64,}={0,2}\\b')`.

### Class `SecurityVerdict(BaseModel)`

- **Line:** 55
- **Description:** Allow/block + reason from SecurityGuard.

#### Fields / class variables

- L56: **`blocked`**: `bool`
- L57: **`stage`**: `Optional[str]` = `None`
- L58: **`reason`**: `Optional[str]` = `None`

### Class `SecurityGuard`

- **Line:** 60
- **Description:** Prompt-injection / jailbreak guard.

#### Methods

- L61: `def __init__(self, llm: Optional[LlmPort])`
  - Defined at line 61.
- L64: `def check(self, question: str, language: str) -> SecurityVerdict`
  - Rule + optional LLM security classify; returns SecurityVerdict.
- L137: `def _verify_with_llm(self, text: str, language: str) -> SecurityVerdict`
  - Calls SECURITY_MODEL to classify prompt injection risk.

### Functions

- L51: `def _sec_msg(language: str, pl: str, en: str) -> str`
  - Defined at line 51. Returns `str`.

---

## `app/application/session_service.py`

**Purpose:** Session lifecycle: start/list/delete/export/summary/events/dashboard/purge/ownership fields.

**Layer / role:** Use cases / services: orchestrate domain logic via ports. Framework-agnostic.

- **Lines:** 293
- **Imports:** 22 · **Classes:** 1 · **Functions:** 0 · **Module vars:** 0

### Imports

- L1: `import uuid` — stdlib
- L2: `import time` — stdlib
- L3: `from typing import Optional` — stdlib
- L3: `from typing import List` — stdlib
- L3: `from typing import Dict` — stdlib
- L3: `from typing import Any` — stdlib
- L3: `from typing import Union` — stdlib
- L3: `from typing import Tuple` — stdlib
- L5: `from app.application.dto import GoalProgressEntryDTO` — application services/DTOs
- L5: `from app.application.dto import SessionSummaryResponse` — application services/DTOs
- L5: `from app.application.dto import RagPreviewDTO` — application services/DTOs
- L5: `from app.application.dto import RagMaterialPreviewDTO` — application services/DTOs
- L6: `from app.application.grade_payload import build_grade_sync_payload` — application services/DTOs
- L7: `from app.domain.conversation import Conversation` — domain types/ports/exceptions
- L7: `from app.domain.conversation import GoalStatus` — domain types/ports/exceptions
- L8: `from app.domain.ports import ConversationRepository` — domain types/ports/exceptions
- L8: `from app.domain.ports import RagPort` — domain types/ports/exceptions
- L8: `from app.domain.ports import WebhookPort` — domain types/ports/exceptions
- L9: `from app.domain.sensei import SenseiConfig` — domain types/ports/exceptions
- L10: `from app.domain.exceptions import UnknownConversation` — domain types/ports/exceptions
- L10: `from app.domain.exceptions import PrelabRequired` — domain types/ports/exceptions
- L11: `from app.core.config import settings` — settings

### Class `SessionService`

- **Line:** 14
- **Description:** Conversation lifecycle and professor dashboard use case.

#### Methods

- L15: `def __init__(self, repo: ConversationRepository, rag: Optional[RagPort], webhooks: Optional[WebhookPort])`
  - Conversation repo + optional RAG ingest and webhooks.
- L20: `def start_conversation(self, config: Union[SenseiConfig, Dict[str, Any]]) -> Tuple[Conversation, RagPreviewDTO]`
  - Creates Conversation, optional RAG ingest, returns rag preview.
- L56: `def list_conversations(self) -> List[Dict[str, Any]]`
  - Compact active-session list for dashboards.
- L73: `def count_active(self) -> int`
  - Count of non-deleted conversations in repo.
- L76: `def get_or_404(self, conv_id: str) -> Conversation`
  - Load conversation or raise UnknownConversation; touches last_activity.
- L84: `def delete(self, conv_id: str) -> Dict[str, Any]`
  - Soft-delete, RAG cleanup, build summary, optional summary webhook.
- L106: `def export(self, conv_id: str) -> dict`
  - Full conversation dump for professor export.
- L110: `def record_event(self, conv_id: str, event_type: str, meta: Optional[Dict[str, Any]]) -> Dict[str, Any]`
  - Appends telemetry event; may forward to webhook.
- L157: `def purge_old_sessions(self) -> int`
  - Deletes sessions idle longer than CONVERSATION_TTL_SECONDS.
- L160: `def ensure_prelab_passed(self, conv_id: str) -> Conversation`
  - Raises PrelabRequired if pre-lab enabled and not completed.
- L166: `def _build_and_store_summary(self, conv: Conversation) -> Dict[str, Any]`
  - Computes and stores session summary dict on the conversation.
- L222: `def generate_summary(self, conv_id: str) -> Dict[str, Any]`
  - Returns (and caches) end-of-lab summary.
- L226: `def add_intervention_note(self, conv_id: str, text: str, author_sub: Optional[str]) -> Dict[str, Any]`
  - Professor note attached to conversation for observe UI.
- L239: `def observe(self, conv_id: str) -> Dict[str, Any]`
  - Read-only professor observation payload for a session.
- L259: `def lab_dashboard(self, lab_id: Optional[str]) -> Dict[str, Any]`
  - Aggregated stats for all sessions with a given lab_id.

---

## `app/application/similarity.py`

**Purpose:** Token Jaccard similarity vs solution_pack for plagiarism-ish checks.

**Layer / role:** Use cases / services: orchestrate domain logic via ports. Framework-agnostic.

- **Lines:** 40
- **Imports:** 5 · **Classes:** 0 · **Functions:** 3 · **Module vars:** 0

### Imports

- L1: `from __future__ import annotations`
- L3: `import re` — stdlib
- L4: `from typing import Dict` — stdlib
- L4: `from typing import List` — stdlib
- L4: `from typing import Optional` — stdlib

### Functions

- L7: `def _tokens(text: str) -> set`
  - Simple alphanumeric tokenizer for similarity.
- L11: `def jaccard_similarity(a: str, b: str) -> float`
  - Jaccard index between two token sets.
- L18: `def best_solution_match(student_code: str, solution_pack: List[str]) -> Dict[str, Optional[float]]`
  - Best Jaccard match of student code against solution_pack entries.

---

# app/api

HTTP edge: routers, DI, auth helpers, middleware, error mapping to HTTP.

## `app/api/auth.py`

**Purpose:** Bearer extraction, JWT verify, client IP (optional X-Forwarded-For).

**Layer / role:** HTTP edge: routers, DI, auth helpers, middleware, error mapping to HTTP.

- **Lines:** 59
- **Imports:** 7 · **Classes:** 0 · **Functions:** 3 · **Module vars:** 1

### Imports

- L1: `from typing import Any` — stdlib
- L1: `from typing import Dict` — stdlib
- L1: `from typing import Optional` — stdlib
- L1: `from typing import Tuple` — stdlib
- L3: `import jwt` — JWT verification
- L5: `from app.application.access import require_professor` — application services/DTOs
- L6: `from app.core.config import settings` — settings

### Module-level variables / constants

- L8: **`__all__`** — Public export list.

### Functions

- L16: `def extract_bearer_token(authorization_header: Optional[str]) -> Optional[str]`
  - Parses `Authorization: Bearer <token>`; returns token or None.
- L26: `def verify_access_token(token: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]`
  - Validates JWT signature/aud/iss; returns (ok, claims, error).
- L53: `def client_ip_from_request(client_host: Optional[str], x_forwarded_for: Optional[str]) -> str`
  - Resolves client IP; optionally trusts first X-Forwarded-For hop.

---

## `app/api/deps.py`

**Purpose:** Composition root: constructs adapters and FastAPI Depends providers.

**Layer / role:** HTTP edge: routers, DI, auth helpers, middleware, error mapping to HTTP.

- **Lines:** 57
- **Imports:** 14 · **Classes:** 0 · **Functions:** 7 · **Module vars:** 5

### Imports

- L1: `from fastapi import Depends` — HTTP framework
- L3: `from app.application.chat_service import ChatService` — application services/DTOs
- L4: `from app.application.prelab_service import PrelabService` — application services/DTOs
- L5: `from app.application.session_service import SessionService` — application services/DTOs
- L6: `from app.core.config import settings` — settings
- L7: `from app.domain.ports import CachePort` — domain types/ports/exceptions
- L7: `from app.domain.ports import LlmPort` — domain types/ports/exceptions
- L7: `from app.domain.ports import RagPort` — domain types/ports/exceptions
- L7: `from app.domain.ports import WebhookPort` — domain types/ports/exceptions
- L8: `from app.infrastructure.cache_memory import InMemoryLruCache` — infrastructure adapters
- L9: `from app.infrastructure.conversations_memory import InMemoryConversationRepository` — infrastructure adapters
- L10: `from app.infrastructure.llm_openai import OpenAiCompatibleLlmAdapter` — infrastructure adapters
- L11: `from app.infrastructure.rag_chroma import ChromaRagAdapter` — infrastructure adapters
- L12: `from app.infrastructure.webhooks import HttpWebhookAdapter` — infrastructure adapters

### Module-level variables / constants

- L14: **`rag_adapter`** — Shared ChromaRagAdapter instance (composition root).
- L15: **`llm_cache`** — Shared InMemoryLruCache for LLM responses.
- L16: **`llm_adapter`** — Shared OpenAiCompatibleLlmAdapter instance.
- L18: **`repo`** — Shared InMemoryConversationRepository instance.
- L19: **`webhook_adapter`** — Shared HttpWebhookAdapter instance.

### Functions

- L22: `def get_prelab_service() -> PrelabService`
  - DI: PrelabService bound to shared repo.
- L26: `def get_webhook_port() -> WebhookPort`
  - DI: shared webhook adapter.
- L30: `def get_llm_port() -> LlmPort`
  - DI: shared LLM adapter.
- L34: `def get_rag_port() -> RagPort`
  - DI: shared RAG adapter.
- L38: `def get_cache_port() -> CachePort`
  - DI: shared LLM cache.
- L42: `def get_session_service(rag: RagPort, webhooks: WebhookPort) -> SessionService`
  - DI: SessionService with rag+webhooks.
- L49: `def get_chat_service(svc: SessionService, llm: LlmPort, rag: RagPort, cache: CachePort, webhooks: WebhookPort) -> ChatService`
  - DI: ChatService with full port graph.

---

## `app/api/errors.py`

**Purpose:** Exception handlers → JSON with stable message_id codes.

**Layer / role:** HTTP edge: routers, DI, auth helpers, middleware, error mapping to HTTP.

- **Lines:** 102
- **Imports:** 8 · **Classes:** 0 · **Functions:** 8 · **Module vars:** 1

### Imports

- L1: `from fastapi import Request` — HTTP framework
- L2: `from fastapi.responses import JSONResponse` — HTTP framework
- L3: `from app.domain.exceptions import PrelabRequired` — domain types/ports/exceptions
- L3: `from app.domain.exceptions import TokenBudgetExceeded` — domain types/ports/exceptions
- L3: `from app.domain.exceptions import UnknownConversation` — domain types/ports/exceptions
- L3: `from app.domain.exceptions import UnknownMessage` — domain types/ports/exceptions
- L3: `from app.domain.exceptions import HintRevealForbidden` — domain types/ports/exceptions
- L3: `from app.domain.exceptions import SsrfBlockedError` — domain types/ports/exceptions

### Module-level variables / constants

- L7: **`_LLM_RATE_LIMIT_RETRY_AFTER`** — Module/class constant or field. Default/value: `'5'`.

### Functions

- L10: `async def llm_rate_limited_handler(request: Request, exc: Exception)`
  - HTTP 429 for LLM rate limits.
- L24: `async def llm_unavailable_handler(request: Request, exc: Exception)`
  - HTTP 503 when LLM is down/unreachable after retries.
- L35: `async def prelab_required_handler(request: Request, exc: PrelabRequired)`
  - HTTP 403 until pre-lab is passed.
- L45: `async def token_budget_exceeded_handler(request: Request, exc: TokenBudgetExceeded)`
  - HTTP 403 when session token budget exhausted.
- L61: `async def unknown_conversation_handler(request: Request, exc: UnknownConversation)`
  - HTTP 404 for missing conversation.
- L67: `async def unknown_message_handler(request: Request, exc: UnknownMessage)`
  - HTTP 404 for missing message.
- L72: `async def hint_reveal_forbidden_handler(request: Request, exc: HintRevealForbidden)`
  - HTTP 403 when hint streak/quota not met.
- L98: `async def ssrf_blocked_handler(request: Request, exc: SsrfBlockedError)`
  - HTTP 400 when RAG URL fails SSRF checks.

---

## `app/api/middleware.py`

**Purpose:** Request-Id, JWT auth, per-IP rate limit middleware.

**Layer / role:** HTTP edge: routers, DI, auth helpers, middleware, error mapping to HTTP.

- **Lines:** 127
- **Imports:** 15 · **Classes:** 3 · **Functions:** 3 · **Module vars:** 5

### Imports

- L1: `import time` — stdlib
- L2: `import uuid` — stdlib
- L3: `from collections import defaultdict` — stdlib
- L3: `from collections import deque` — stdlib
- L4: `from typing import Deque` — stdlib
- L4: `from typing import Dict` — stdlib
- L6: `from starlette.middleware.base import BaseHTTPMiddleware` — ASGI primitives
- L7: `from starlette.requests import Request` — ASGI primitives
- L8: `from starlette.responses import JSONResponse` — ASGI primitives
- L8: `from starlette.responses import Response` — ASGI primitives
- L10: `from app.api.auth import client_ip_from_request` — API helpers/routers
- L10: `from app.api.auth import extract_bearer_token` — API helpers/routers
- L10: `from app.api.auth import verify_access_token` — API helpers/routers
- L11: `from app.application.metrics import metrics` — application services/DTOs
- L12: `from app.core.config import settings` — settings

### Module-level variables / constants

- L14: **`_AUTH_OPEN_PREFIXES`** — Module/class constant or field. Default/value: `('/health', '/health_check')`.
- L19: **`_AUTH_OPEN_EXACT`** — Module/class constant or field. Default/value: `{'/favicon.ico'}`.
- L21: **`_RATE_LIMITED_PREFIXES`** — Module/class constant or field. Default/value: `('/conversations', '/config', '/validate-config')`.
- L87: **`_rate_limit_hits`** — Module/class constant or field. Type: `Dict[str, Deque[float]]`. Default/value: `defaultdict(deque)`.
- L88: **`_RATE_LIMIT_WINDOW_SECONDS`** — Module/class constant or field. Default/value: `60.0`.

### Class `RequestIdMiddleware(BaseHTTPMiddleware)`

- **Line:** 40
- **Description:** Propagates/creates X-Request-Id.

#### Methods

- L42: `async def dispatch(self, request: Request, call_next) -> Response`
  - Ensures X-Request-Id on request/response.

### Class `JwtAuthMiddleware(BaseHTTPMiddleware)`

- **Line:** 55
- **Description:** Enforces/parses JWT when auth enabled.

#### Methods

- L56: `async def dispatch(self, request: Request, call_next) -> Response`
  - Verifies Bearer JWT when AI_AUTH_ENABLED; stores claims on request.state.

### Class `RateLimitMiddleware(BaseHTTPMiddleware)`

- **Line:** 95
- **Description:** Per-IP request rate limiting.

#### Methods

- L97: `def _prune(self, bucket: Deque[float], now: float) -> None`
  - Drops old timestamps from a rate-limit bucket.
- L102: `async def dispatch(self, request: Request, call_next) -> Response`
  - Sliding-window per-IP limiter; 429 when exceeded.

### Functions

- L24: `def _is_auth_open_path(path: str) -> bool`
  - Paths that skip JWT (health, docs/ui when exposed).
- L36: `def _is_rate_limited_path(path: str) -> bool`
  - Paths subject to per-IP rate limiting.
- L91: `def reset_rate_limit_buckets() -> None`
  - Clears in-memory rate-limit state (tests).

---

## `app/api/routers/config.py`

**Purpose:** Schema, presets, validate, dry-run for SenseiConfig.

**Layer / role:** HTTP edge: routers, DI, auth helpers, middleware, error mapping to HTTP.

- **Lines:** 111
- **Imports:** 12 · **Classes:** 0 · **Functions:** 4 · **Module vars:** 2

### Imports

- L1: `import json` — stdlib
- L2: `from pathlib import Path` — stdlib
- L3: `from typing import Dict` — stdlib
- L3: `from typing import Any` — stdlib
- L5: `from jsonschema import validate`
- L5: `from jsonschema import ValidationError as JsonSchemaError`
- L6: `from pydantic import ValidationError as PydanticError` — validation models
- L7: `from fastapi import APIRouter` — HTTP framework
- L8: `from app.application.config_dry_run import run_config_dry_run` — application services/DTOs
- L9: `from app.application.dto import ConfigValidationRequest` — application services/DTOs
- L9: `from app.application.dto import ConversationStartRequest` — application services/DTOs
- L10: `from app.domain.sensei import SenseiConfig` — domain types/ports/exceptions

### Module-level variables / constants

- L12: **`router`** — FastAPI APIRouter for this module's endpoints.
- L14: **`_SCHEMA_PATH`** — Module/class constant or field. Default/value: `Path(__file__).resolve().parents[3] / 'schemas' / 'sensei-config.schema.json'`.

### Functions

- L17: @router.get('/config/schema') `def get_config_schema() -> Dict[str, Any]`
  - Returns JSON Schema for SenseiConfig.
- L21: @router.get('/config/presets') `def get_config_presets() -> Dict[str, Any]`
  - Returns built-in config presets.
- L76: @router.post('/validate-config') @router.post('/config/validate-config') @router.post('/config/validate') `def validate_config(req: ConfigValidationRequest)`
  - Validates config payload via Pydantic.
- L106: @router.post('/config/dry-run') `def config_dry_run(req: ConversationStartRequest)`
  - Feature 8: simulate student path (prelab/gates/security/hints) without LLM. Body: { "config": SenseiConfig } — same shape as conversation start.

---

## `app/api/routers/conversations.py`

**Purpose:** REST API for conversations, messages, prelab, hints, feedback, professor tools.

**Layer / role:** HTTP edge: routers, DI, auth helpers, middleware, error mapping to HTTP.

- **Lines:** 434
- **Imports:** 31 · **Classes:** 3 · **Functions:** 25 · **Module vars:** 6

### Imports

- L1: `from fastapi import APIRouter` — HTTP framework
- L1: `from fastapi import Depends` — HTTP framework
- L1: `from fastapi import HTTPException` — HTTP framework
- L1: `from fastapi import Request` — HTTP framework
- L1: `from fastapi import status` — HTTP framework
- L2: `from starlette.responses import StreamingResponse` — ASGI primitives
- L4: `from app.application.access import ensure_conversation_access` — application services/DTOs
- L4: `from app.application.access import require_professor` — application services/DTOs
- L5: `from app.application.chat_service import ChatService` — application services/DTOs
- L6: `from app.application.dto import ConversationStartRequest` — application services/DTOs
- L6: `from app.application.dto import EventRequest` — application services/DTOs
- L6: `from app.application.dto import MessageRequest` — application services/DTOs
- L6: `from app.application.dto import MessageResponse` — application services/DTOs
- L6: `from app.application.dto import FeedbackRequest` — application services/DTOs
- L6: `from app.application.dto import HintRevealResponse` — application services/DTOs
- L8: `from app.application.session_service import SessionService` — application services/DTOs
- L9: `from app.core.config import settings` — settings
- L10: `from app.domain.conversation import Conversation` — domain types/ports/exceptions
- L11: `from app.domain.exceptions import UnknownConversation` — domain types/ports/exceptions
- L13: `from app.application.prelab_service import PrelabService` — application services/DTOs
- L14: `from app.application.dto import PrelabSubmitRequest` — application services/DTOs
- L15: `from pydantic import BaseModel` — validation models
- L15: `from pydantic import ConfigDict` — validation models
- L15: `from pydantic import Field` — validation models
- L16: `from typing import Any` — stdlib
- L16: `from typing import Dict` — stdlib
- L16: `from typing import Optional` — stdlib
- L52: `from app.api import deps` — API helpers/routers
- L53: `from app.api.deps import get_chat_service` — API helpers/routers
- L53: `from app.api.deps import get_prelab_service` — API helpers/routers
- L53: `from app.api.deps import get_session_service` — API helpers/routers

### Module-level variables / constants

- L59: **`rag_adapter`** — Shared ChromaRagAdapter instance (composition root).
- L60: **`llm_cache`** — Shared InMemoryLruCache for LLM responses.
- L61: **`llm_adapter`** — Shared OpenAiCompatibleLlmAdapter instance.
- L62: **`repo`** — Shared InMemoryConversationRepository instance.
- L63: **`webhook_adapter`** — Shared HttpWebhookAdapter instance.
- L65: **`router`** — FastAPI APIRouter for this module's endpoints.

### Class `ForceHintRequest(BaseModel)`

- **Line:** 68
- **Description:** Body for professor force-hint endpoint.

#### Fields / class variables

- L69: **`model_config`** = `ConfigDict(populate_by_name=True)`
- L70: **`reason`**: `Optional[str]` = `Field(default='professor_override')`
- L71: **`custom_hint`**: `Optional[str]` = `Field(default=None, alias='customHint')`
- L72: **`hint_level`**: `Optional[str]` = `Field(default=None, alias='hintLevel')`

### Class `InterventionNoteRequest(BaseModel)`

- **Line:** 75
- **Description:** Body for professor intervention note.

#### Fields / class variables

- L76: **`text`**: `str` = `Field(min_length=1, max_length=4000)`

### Class `SimilarityRequest(BaseModel)`

- **Line:** 79
- **Description:** Body for solution_pack similarity check.

#### Fields / class variables

- L80: **`code`**: `Optional[str]` = `None`

### Functions

- L83: `def _claims(request: Request) -> Optional[Dict[str, Any]]`
  - JWT claims from request.state (set by middleware).
- L87: `def _load_owned(conv_id: str, request: Request, svc: SessionService) -> Conversation`
  - get_or_404 + ensure_conversation_access.
- L97: `def _require_professor_when_auth(request: Request) -> None`
  - 403 unless professor when AI_AUTH_ENABLED.
- L111: @router.post('') `def start_conversation(req: ConversationStartRequest, request: Request, svc: SessionService, prelab_svc: PrelabService)`
  - POST /conversations — create session (+ optional owner_sub/lab_id).
- L148: @router.get('') `def list_conversations(request: Request, svc: SessionService)`
  - GET list of active conversations (professor when auth on).
- L157: @router.post('/purge') `def purge_conversations(request: Request, svc: SessionService)`
  - POST purge expired sessions now.
- L167: @router.get('/professor/dashboard') `def professor_dashboard(request: Request, lab_id: Optional[str], svc: SessionService)`
  - Feature 7: live lab dashboard aggregates for professors. Registered before /{conv_id} so 'professor' is not parsed as an id.
- L180: @router.get('/{conv_id}') `def get_conversation(conv_id: str, request: Request, svc: SessionService)`
  - GET single conversation metadata/state.
- L201: @router.delete('/{conv_id}') `def delete_conversation(conv_id: str, request: Request, svc: SessionService)`
  - DELETE soft-delete + summary.
- L213: @router.get('/{conv_id}/restrictions') `def get_restrictions(conv_id: str, request: Request, svc: SessionService)`
  - GET effective IDE restrictions for the session.
- L224: @router.get('/{conv_id}/export') `def export_conversation(conv_id: str, request: Request, svc: SessionService)`
  - GET full export payload.
- L236: @router.get('/{conv_id}/checkpoints') `def get_checkpoints(conv_id: str, request: Request, svc: SessionService)`
  - GET checkpoint unlock state.
- L247: @router.post('/{conv_id}/events') `def record_event(conv_id: str, req: EventRequest, request: Request, svc: SessionService)`
  - POST client telemetry event.
- L261: @router.get('/{conv_id}/prelab') `def get_prelab_status(conv_id: str, request: Request, svc: SessionService, prelab_svc: PrelabService)`
  - GET pre-lab status/questions.
- L271: @router.post('/{conv_id}/summary') `def summarize_conversation(conv_id: str, request: Request, svc: SessionService)`
  - POST/GET generate session summary.
- L284: @router.post('/{conv_id}/prelab') `def submit_prelab(conv_id: str, req: PrelabSubmitRequest, request: Request, svc: SessionService, prelab_svc: PrelabService)`
  - POST pre-lab answers.
- L296: @router.post('/{conv_id}/messages', response_model=MessageResponse) `def send_message(conv_id: str, req: MessageRequest, request: Request, svc: SessionService, chat_svc: ChatService)`
  - POST chat message (non-streaming).
- L307: @router.get('/{conv_id}/messages') `def get_messages(conv_id: str, request: Request, svc: SessionService, chat_svc: ChatService)`
  - GET message history.
- L317: @router.post('/{conv_id}/messages/{message_id}/feedback') `def submit_feedback(conv_id: str, message_id: str, req: FeedbackRequest, request: Request, svc: SessionService, chat_svc: ChatService)`
  - POST feedback on an assistant message.
- L329: @router.post('/{conv_id}/messages/stream') `def stream_message(conv_id: str, req: MessageRequest, request: Request, svc: SessionService, chat_svc: ChatService)`
  - POST SSE/stream chat response.
- L341: @router.post('/{conv_id}/hints/reveal', response_model=HintRevealResponse) `def reveal_hint(conv_id: str, request: Request, svc: SessionService, chat_svc: ChatService)`
  - POST student hint reveal.
- L352: @router.post('/{conv_id}/hints/force', response_model=HintRevealResponse) `def force_hint(conv_id: str, request: Request, req: Optional[ForceHintRequest], svc: SessionService, chat_svc: ChatService)`
  - POST professor force hint.
- L377: @router.post('/{conv_id}/notes') `def add_intervention_note(conv_id: str, body: InterventionNoteRequest, request: Request, svc: SessionService)`
  - POST professor intervention note.
- L390: @router.get('/{conv_id}/observe') `def observe_conversation(conv_id: str, request: Request, svc: SessionService)`
  - GET professor observe view.
- L403: @router.post('/{conv_id}/similarity') `def similarity_check(conv_id: str, request: Request, body: Optional[SimilarityRequest], svc: SessionService)`
  - POST compare code to solution_pack.

---

## `app/api/routers/health.py`

**Purpose:** Liveness/readiness, metrics, recent webhooks (ops-gated).

**Layer / role:** HTTP edge: routers, DI, auth helpers, middleware, error mapping to HTTP.

- **Lines:** 81
- **Imports:** 10 · **Classes:** 0 · **Functions:** 6 · **Module vars:** 1

### Imports

- L1: `from fastapi import APIRouter` — HTTP framework
- L1: `from fastapi import HTTPException` — HTTP framework
- L1: `from fastapi import Request` — HTTP framework
- L1: `from fastapi import Response` — HTTP framework
- L1: `from fastapi import status` — HTTP framework
- L3: `from app.api import deps` — API helpers/routers
- L4: `from app.application.access import require_professor` — application services/DTOs
- L5: `from app.api.routers import conversations` — API helpers/routers
- L6: `from app.application.metrics import metrics` — application services/DTOs
- L7: `from app.core.config import settings` — settings

### Module-level variables / constants

- L9: **`router`** — FastAPI APIRouter for this module's endpoints.

### Functions

- L12: @router.get('/health_check') `def health_check()`
  - Simple liveness endpoint.
- L17: @router.get('/health') `def health(response: Response)`
  - Readiness: LLM/RAG/cache status flags.
- L35: `def _require_ops_access(request: Request) -> None`
  - Metrics / webhook buffer: JWT already required by middleware when auth on; additionally restrict to professor roles.
- L50: @router.get('/metrics') `def metrics_json(request: Request)`
  - JSON metrics snapshot.
- L57: @router.get('/metrics/prometheus') `def prometheus_metrics(request: Request)`
  - Prometheus text exposition of counters.
- L77: @router.get('/webhooks/recent') `def recent_webhooks(request: Request, limit: int)`
  - Recent webhook delivery attempts.

---

## `app/api/routers/ui.py`

**Purpose:** Serves static lab UI HTML when AI_EXPOSE_UI is enabled.

**Layer / role:** HTTP edge: routers, DI, auth helpers, middleware, error mapping to HTTP.

- **Lines:** 21
- **Imports:** 3 · **Classes:** 0 · **Functions:** 2 · **Module vars:** 3

### Imports

- L1: `from pathlib import Path` — stdlib
- L2: `from fastapi import APIRouter` — HTTP framework
- L3: `from fastapi.responses import HTMLResponse` — HTTP framework

### Module-level variables / constants

- L5: **`router`** — FastAPI APIRouter for this module's endpoints.
- L6: **`STATIC_DIR`** — Module/class constant or field. Default/value: `Path(__file__).resolve().parent.parent.parent / 'static'`.
- L8: **`_NO_STORE`** — Module/class constant or field. Default/value: `{'Cache-Control': 'no-store, max-age=0'}`.

### Functions

- L12: @router.get('/', response_class=HTMLResponse) `def serve_index() -> HTMLResponse`
  - Defined at line 12. Returns `HTMLResponse`.
- L18: @router.get('/scenarios', response_class=HTMLResponse) `def serve_scenarios() -> HTMLResponse`
  - Defined at line 18. Returns `HTMLResponse`.

---

# app/infrastructure

Adapters implementing domain ports (LLM, RAG/Chroma, cache, webhooks, in-memory repo).

## `app/infrastructure/cache_memory.py`

**Purpose:** TTL LRU cache for LlmResult.

**Layer / role:** Adapters implementing domain ports (LLM, RAG/Chroma, cache, webhooks, in-memory repo).

- **Lines:** 54
- **Imports:** 7 · **Classes:** 1 · **Functions:** 0 · **Module vars:** 0

### Imports

- L1: `import time` — stdlib
- L2: `from collections import OrderedDict` — stdlib
- L3: `from typing import Optional` — stdlib
- L3: `from typing import Tuple` — stdlib
- L4: `from app.domain.ports import CachePort` — domain types/ports/exceptions
- L4: `from app.domain.ports import LlmResult` — domain types/ports/exceptions
- L9: `from app.application.cache_keys import build_cache_key` — application services/DTOs

### Class `InMemoryLruCache(CachePort)`

- **Line:** 11
- **Description:** Process-local TTL LRU implementing CachePort.

#### Methods

- L12: `def __init__(self, max_size: int, ttl_seconds: int)`
  - Defined at line 12.
- L17: `def _purge_expired(self) -> None`
  - Drop TTL-expired entries.
- L25: `def get(self, key: str) -> Optional[LlmResult]`
  - Return cached LlmResult if present and not expired.
- L41: `def set(self, key: str, value: LlmResult) -> None`
  - Insert/update cache entry with LRU eviction.
- L50: `def size(self) -> int`
  - Defined at line 50. Returns `int`.
- L53: `def clear(self) -> None`
  - Defined at line 53. Returns `None`.

---

## `app/infrastructure/conversations_memory.py`

**Purpose:** In-memory ConversationRepository.

**Layer / role:** Adapters implementing domain ports (LLM, RAG/Chroma, cache, webhooks, in-memory repo).

- **Lines:** 40
- **Imports:** 7 · **Classes:** 1 · **Functions:** 0 · **Module vars:** 0

### Imports

- L1: `from typing import Dict` — stdlib
- L1: `from typing import List` — stdlib
- L1: `from typing import Optional` — stdlib
- L2: `from datetime import datetime` — stdlib
- L2: `from datetime import timezone` — stdlib
- L3: `from app.domain.conversation import Conversation` — domain types/ports/exceptions
- L4: `from app.domain.ports import ConversationRepository` — domain types/ports/exceptions

### Class `InMemoryConversationRepository(ConversationRepository)`

- **Line:** 6
- **Description:** Process-local dict-backed ConversationRepository.

#### Methods

- L7: `def __init__(self)`
  - Defined at line 7.
- L10: `def save(self, conversation: Conversation) -> None`
  - Upsert conversation by id.
- L13: `def get(self, conversation_id: str) -> Optional[Conversation]`
  - Fetch by id or None.
- L19: `def delete(self, conversation_id: str) -> bool`
  - Hard-delete by id.
- L25: `def purge_expired(self, ttl_seconds: int) -> int`
  - Remove idle sessions older than ttl; return count.
- L35: `def list_active(self) -> List[Conversation]`
  - All non-deleted conversations.
- L38: `def count_active(self) -> int`
  - Len of active conversations.

---

## `app/infrastructure/llm_errors.py`

**Purpose:** LLM error types + retry/fallback executor helpers.

**Layer / role:** Adapters implementing domain ports (LLM, RAG/Chroma, cache, webhooks, in-memory repo).

- **Lines:** 64
- **Imports:** 8 · **Classes:** 4 · **Functions:** 3 · **Module vars:** 1

### Imports

- L1: `import time` — stdlib
- L2: `from typing import Callable` — stdlib
- L2: `from typing import TypeVar` — stdlib
- L2: `from typing import Optional` — stdlib
- L3: `from openai import RateLimitError` — OpenAI-compatible LLM client
- L3: `from openai import APIConnectionError` — OpenAI-compatible LLM client
- L3: `from openai import APITimeoutError` — OpenAI-compatible LLM client
- L3: `from openai import InternalServerError` — OpenAI-compatible LLM client

### Module-level variables / constants

- L5: **`T`** — Module/class constant or field. Default/value: `TypeVar('T')`.

### Class `LlmError(Exception)`

- **Line:** 7
- **Description:** Base LLM infrastructure error.

### Class `LlmRateLimitError(LlmError)`

- **Line:** 10
- **Description:** Provider rate limit after handling.

### Class `LlmTransientError(LlmError)`

- **Line:** 13
- **Description:** Transient LLM failure (connection/timeout).

### Class `LlmUnavailableError(LlmError)`

- **Line:** 16
- **Description:** LLM still unavailable after retries/fallback.

### Functions

- L20: `def is_rate_limit_exception(exc: Exception) -> bool`
  - Detects provider rate-limit exceptions.
- L28: `def is_transient_exception(exc: Exception) -> bool`
  - Detects connection/timeout-style transient failures.
- L34: `def execute_with_retry_and_fallback(fn: Callable[[Optional[str]], T], primary_model: str, fallback_model: Optional[str], max_retries: int, backoff_seconds: float) -> T`
  - Retry transient LLM errors; optionally switch to fallback model.

---

## `app/infrastructure/llm_openai.py`

**Purpose:** OpenAI-compatible chat completions adapter (Ollama/etc.) with retry/fallback.

**Layer / role:** Adapters implementing domain ports (LLM, RAG/Chroma, cache, webhooks, in-memory repo).

- **Lines:** 93
- **Imports:** 9 · **Classes:** 1 · **Functions:** 0 · **Module vars:** 0

### Imports

- L1: `from typing import List` — stdlib
- L1: `from typing import Dict` — stdlib
- L1: `from typing import Optional` — stdlib
- L1: `from typing import Iterator` — stdlib
- L2: `from openai import OpenAI` — OpenAI-compatible LLM client
- L4: `from app.infrastructure.llm_errors import execute_with_retry_and_fallback` — infrastructure adapters
- L5: `from app.domain.ports import LlmPort` — domain types/ports/exceptions
- L5: `from app.domain.ports import LlmResult` — domain types/ports/exceptions
- L6: `from app.core.config import settings` — settings

### Class `OpenAiCompatibleLlmAdapter(LlmPort)`

- **Line:** 8
- **Description:** LLM adapter for OpenAI-compatible HTTP APIs (e.g. Ollama).

#### Methods

- L9: `def __init__(self)`
  - Defined at line 9.
- L23: `def is_configured(self) -> bool`
  - True when base URL / key / model settings present.
- L26: `def generate_json(self, system_prompt: str, messages: List[Dict[str, str]], model_override: Optional[str]) -> LlmResult`
  - Chat completion with retries/fallback; returns LlmResult.
- L62: `def stream_json(self, system_prompt: str, messages: List[Dict[str, str]], model_override: Optional[str]) -> Iterator[str]`
  - Streams completion chunks as text.

---

## `app/infrastructure/rag_chroma.py`

**Purpose:** Chroma-backed RAG with SSRF-safe URL fetch, chunking, retrieve.

**Layer / role:** Adapters implementing domain ports (LLM, RAG/Chroma, cache, webhooks, in-memory repo).

- **Lines:** 309
- **Imports:** 19 · **Classes:** 1 · **Functions:** 8 · **Module vars:** 2

### Imports

- L1: `import hashlib` — stdlib
- L2: `import ipaddress` — stdlib
- L3: `import logging` — stdlib
- L4: `import math` — stdlib
- L5: `import re` — stdlib
- L6: `import socket` — stdlib
- L7: `from typing import List` — stdlib
- L7: `from typing import Dict` — stdlib
- L7: `from typing import Optional` — stdlib
- L7: `from typing import Callable` — stdlib
- L7: `from typing import Any` — stdlib
- L7: `from typing import Tuple` — stdlib
- L8: `from urllib.parse import urlparse` — stdlib
- L10: `import httpx` — HTTP client
- L12: `from app.domain.ports import RagPort` — domain types/ports/exceptions
- L12: `from app.domain.ports import RagChunk` — domain types/ports/exceptions
- L13: `from app.domain.sensei import ReferenceMaterial` — domain types/ports/exceptions
- L14: `from app.domain.exceptions import SsrfBlockedError` — domain types/ports/exceptions
- L15: `from app.core.config import settings` — settings

### Module-level variables / constants

- L17: **`logger`** — Module logger.
- L25: **`FORBIDDEN_HOSTNAMES`** — Module/class constant or field. Default/value: `{'localhost', 'localhost.localdomain', 'metadata.google.internal', '169.254.169.254'}`.

### Class `ChromaRagAdapter(RagPort)`

- **Line:** 159
- **Description:** RAG adapter using Chroma + safe URL fetch.

#### Methods

- L160: `def __init__(self, fetcher: Optional[Callable[[str], str]])`
  - Defined at line 160.
- L177: `def is_healthy(self) -> bool`
  - Basic Chroma connectivity/health check.
- L185: `def _fetch_material_text(self, material: ReferenceMaterial)`
  - Safe-fetch material link or use inline content.
- L223: `def ingest(self, conversation_id: str, materials: List[ReferenceMaterial]) -> int`
  - Fetch/chunk/embed materials into per-conversation collection.
- L260: `def retrieve(self, conversation_id: str, query: str, top_k: int) -> List[RagChunk]`
  - Top-k similar chunks for a query.
- L302: `def delete_conversation(self, conversation_id: str) -> None`
  - Drop RAG data for a conversation id.

### Functions

- L32: `def _is_ip_forbidden(ip_str: str) -> bool`
  - True for private/loopback/link-local/etc. IPs.
- L45: `def validate_safe_url(url: str) -> str`
  - SSRF guard: scheme/host/IP checks before fetching material URLs.
- L85: `def _strip_html(raw_html: str) -> str`
  - HTML→text for RAG ingest.
- L99: `def _extract_pdf_text(raw_bytes: bytes) -> str`
  - Best-effort PDF text extraction for RAG.
- L113: `def _decode_fetched_content(url: str, raw_bytes: bytes, content_type: str) -> str`
  - Chooses text decode path from content-type/URL.
- L128: `def _chunk_text(text: str, chunk_size: int, overlap: int) -> List[str]`
  - Overlapping character chunks for embeddings.
- L144: `def _embed_text(text: str, dim: int) -> List[float]`
  - Deterministic hashing embed (local, no external embed API).
- L157: `def _cosine_similarity(a: List[float], b: List[float]) -> float`
  - Cosine similarity of two embedding vectors.

---

## `app/infrastructure/webhooks.py`

**Purpose:** HTTP webhook sender with recent buffer and event URL routing.

**Layer / role:** Adapters implementing domain ports (LLM, RAG/Chroma, cache, webhooks, in-memory repo).

- **Lines:** 67
- **Imports:** 13 · **Classes:** 1 · **Functions:** 0 · **Module vars:** 1

### Imports

- L1: `import logging` — stdlib
- L2: `import time` — stdlib
- L3: `from collections import deque` — stdlib
- L4: `from typing import Dict` — stdlib
- L4: `from typing import Any` — stdlib
- L4: `from typing import Optional` — stdlib
- L4: `from typing import Callable` — stdlib
- L4: `from typing import List` — stdlib
- L4: `from typing import Deque` — stdlib
- L5: `import httpx` — HTTP client
- L6: `from app.domain.ports import WebhookPort` — domain types/ports/exceptions
- L7: `from app.core.config import settings` — settings
- L8: `from app.application.metrics import metrics` — application services/DTOs

### Module-level variables / constants

- L10: **`logger`** — Module logger.

### Class `HttpWebhookAdapter(WebhookPort)`

- **Line:** 13
- **Description:** HTTP POST webhook adapter with recent buffer.

#### Methods

- L14: `def __init__(self, sender: Optional[Callable[[str, Dict[str, Any]], None]])`
  - Defined at line 14.
- L20: `def _resolve_target_url(self, event_type: str) -> str`
  - Maps event_type to TELEMETRY/SUMMARY/WEBHOOK URL.
- L30: `def recent(self, limit: int) -> List[Dict[str, Any]]`
  - Last N webhook attempt records for ops UI.
- L36: `def send_event(self, event_type: str, payload: Dict[str, Any]) -> bool`
  - POST event JSON to configured URL; buffer recent attempts.

---

# tests

Pytest suite covering milestones M1–M7, auth/rate-limit, abuse hardening, UI/API features.

## `tests/conftest.py`

**Layer / role:** Pytest suite covering milestones M1–M7, auth/rate-limit, abuse hardening, UI/API features.

- **Lines:** 19
- **Imports:** 3 · **Classes:** 0 · **Functions:** 1 · **Module vars:** 0

### Imports

- L1: `import pytest` — testing
- L3: `from app.api.middleware import reset_rate_limit_buckets` — API helpers/routers
- L4: `from app.core.config import settings` — settings

### Functions

- L8: @pytest.fixture(autouse=True) `def _isolate_rate_limits()`
  - Keep inbound rate-limit state from leaking across the whole suite.

---

## `tests/test_abuse_hardening.py`

**Module docstring:** Abuse / reliability hardening from university audit.

**Layer / role:** Pytest suite covering milestones M1–M7, auth/rate-limit, abuse hardening, UI/API features.

- **Lines:** 183
- **Imports:** 15 · **Classes:** 1 · **Functions:** 8 · **Module vars:** 2

### Imports

- L2: `from typing import Dict` — stdlib
- L2: `from typing import List` — stdlib
- L2: `from typing import Optional` — stdlib
- L4: `import pytest` — testing
- L5: `from fastapi.testclient import TestClient` — HTTP framework
- L6: `from openai import APIConnectionError` — OpenAI-compatible LLM client
- L8: `from app.api.middleware import reset_rate_limit_buckets` — API helpers/routers
- L9: `from app.api.deps import get_llm_port` — API helpers/routers
- L10: `from app.core.config import settings` — settings
- L11: `from app.domain.ports import LlmPort` — domain types/ports/exceptions
- L11: `from app.domain.ports import LlmResult` — domain types/ports/exceptions
- L12: `from app.domain.sensei import SenseiConfig` — domain types/ports/exceptions
- L13: `from app.infrastructure.llm_errors import LlmUnavailableError` — infrastructure adapters
- L13: `from app.infrastructure.llm_errors import execute_with_retry_and_fallback` — infrastructure adapters
- L14: `from app.main import app`

### Module-level variables / constants

- L16: **`client`** — Module/class constant or field. Default/value: `TestClient(app, raise_server_exceptions=False)`.
- L18: **`MINIMAL`** — Module/class constant or field. Default/value: `{'language': 'pl', 'evaluationCriteria': 'strict', 'learningContext': {'goals': [{'id': 'g1', 'description': 'Cel 1'}...`.

### Class `BoomLlm(LlmPort)`

- **Line:** 39
- **Description:** Class inheriting from LlmPort.

#### Methods

- L40: `def is_configured(self) -> bool`
  - Defined at line 40. Returns `bool`.
- L43: `def generate_json(self, system_prompt: str, messages: List[Dict[str, str]], model_override: Optional[str]) -> LlmResult`
  - Defined at line 43. Returns `LlmResult`.

### Functions

- L29: @pytest.fixture(autouse=True) `def _auth_off()`
  - Defined at line 29.
- L52: `def test_llm_connection_maps_to_503_unavailable()`
  - Pytest case: llm connection maps to 503 unavailable.
- L68: `def test_execute_wraps_transient_as_unavailable()`
  - Pytest case: execute wraps transient as unavailable.
- L82: `def test_frustration_cooldown_blocks_hint_farming()`
  - Pytest case: frustration cooldown blocks hint farming.
- L116: `def test_enabled_prelab_rejects_empty_keywords()`
  - Pytest case: enabled prelab rejects empty keywords.
- L144: `def test_oversized_question_rejected()`
  - Pytest case: oversized question rejected.
- L154: `def test_default_token_budget_not_unlimited()`
  - Pytest case: default token budget not unlimited.
- L173: `def test_schema_validate_finds_file_off_cwd(tmp_path, monkeypatch)`
  - Pytest case: schema validate finds file off cwd.

---

## `tests/test_advanced_features.py`

**Module docstring:** Features 2,3,4,6,7,8,9,11,12,18,19 smoke tests.

**Layer / role:** Pytest suite covering milestones M1–M7, auth/rate-limit, abuse hardening, UI/API features.

- **Lines:** 151
- **Imports:** 7 · **Classes:** 0 · **Functions:** 8 · **Module vars:** 2

### Imports

- L2: `from fastapi.testclient import TestClient` — HTTP framework
- L4: `from app.core.config import settings` — settings
- L5: `from app.main import app`
- L6: `from app.api.middleware import reset_rate_limit_buckets` — API helpers/routers
- L7: `from app.domain.sensei import SenseiConfig` — domain types/ports/exceptions
- L8: `from app.application.similarity import best_solution_match` — application services/DTOs
- L9: `from app.application.config_dry_run import run_config_dry_run` — application services/DTOs

### Module-level variables / constants

- L11: **`client`** — Module/class constant or field. Default/value: `TestClient(app)`.
- L13: **`BASE`** — Module/class constant or field. Default/value: `{'language': 'en', 'evaluationCriteria': 'REST', 'learningContext': {'goals': [{'id': 'g1', 'description': 'Goal 1'}]...`.

### Functions

- L23: `def setup_function()`
  - Defined at line 23.
- L29: `def test_dry_run_and_hint_ladder_in_config()`
  - Pytest case: dry run and hint ladder in config.
- L52: `def test_focus_mode_set_on_compile_error()`
  - Pytest case: focus mode set on compile error.
- L65: `def test_hint_ladder_reveal_returns_level()`
  - Pytest case: hint ladder reveal returns level.
- L83: `def test_force_custom_hint_and_note_and_observe()`
  - Pytest case: force custom hint and note and observe.
- L104: `def test_dashboard_and_similarity_and_grade_payload()`
  - Pytest case: dashboard and similarity and grade payload.
- L139: `def test_similarity_helper_flags_high_overlap()`
  - Pytest case: similarity helper flags high overlap.
- L147: `def test_dry_run_helper_direct()`
  - Pytest case: dry run helper direct.

---

## `tests/test_auth_rate_limit.py`

**Module docstring:** JWT auth, inbound IP rate limit, and LLM rate-limit → 503 mapping.

**Layer / role:** Pytest suite covering milestones M1–M7, auth/rate-limit, abuse hardening, UI/API features.

- **Lines:** 230
- **Imports:** 14 · **Classes:** 1 · **Functions:** 13 · **Module vars:** 2

### Imports

- L2: `import time` — stdlib
- L3: `from typing import Dict` — stdlib
- L3: `from typing import List` — stdlib
- L3: `from typing import Optional` — stdlib
- L5: `import jwt` — JWT verification
- L6: `import pytest` — testing
- L7: `from fastapi.testclient import TestClient` — HTTP framework
- L9: `from app.api.middleware import reset_rate_limit_buckets` — API helpers/routers
- L10: `from app.api.deps import get_llm_port` — API helpers/routers
- L11: `from app.core.config import settings` — settings
- L12: `from app.domain.ports import LlmPort` — domain types/ports/exceptions
- L12: `from app.domain.ports import LlmResult` — domain types/ports/exceptions
- L13: `from app.infrastructure.llm_errors import LlmRateLimitError` — infrastructure adapters
- L14: `from app.main import app`

### Module-level variables / constants

- L16: **`client`** — Module/class constant or field. Default/value: `TestClient(app)`.
- L18: **`MINIMAL_CONFIG`** — Module/class constant or field. Default/value: `{'language': 'pl', 'evaluationCriteria': 'strict', 'learningContext': {'goals': [{'id': 'g1', 'description': 'Cel 1'}...`.

### Class `AlwaysRateLimitedLlm(LlmPort)`

- **Line:** 201
- **Description:** Class inheriting from LlmPort.

#### Methods

- L202: `def is_configured(self) -> bool`
  - Defined at line 202. Returns `bool`.
- L205: `def generate_json(self, system_prompt: str, messages: List[Dict[str, str]], model_override: Optional[str]) -> LlmResult`
  - Defined at line 205. Returns `LlmResult`.

### Functions

- L28: `def _make_token() -> str`
  - Defined at line 28. Returns `str`.
- L54: @pytest.fixture(autouse=True) `def _reset_security_knobs()`
  - Defined at line 54.
- L64: `def test_auth_disabled_allows_conversations_without_token()`
  - Pytest case: auth disabled allows conversations without token.
- L72: `def test_auth_enabled_health_stays_open_without_token()`
  - Pytest case: auth enabled health stays open without token.
- L80: `def test_auth_enabled_rejects_missing_token()`
  - Pytest case: auth enabled rejects missing token.
- L88: `def test_auth_enabled_rejects_bad_token()`
  - Pytest case: auth enabled rejects bad token.
- L99: `def test_auth_enabled_accepts_valid_token()`
  - Pytest case: auth enabled accepts valid token.
- L111: `def test_auth_enabled_rejects_expired_token()`
  - Pytest case: auth enabled rejects expired token.
- L122: `def test_force_hint_requires_professor_role_when_auth_on()`
  - Pytest case: force hint requires professor role when auth on.
- L151: `def test_student_cannot_access_another_students_conversation()`
  - Pytest case: student cannot access another students conversation.
- L169: `def test_metrics_require_auth_when_enabled()`
  - Pytest case: metrics require auth when enabled.
- L184: `def test_ip_rate_limit_returns_429_with_retry_after()`
  - Pytest case: ip rate limit returns 429 with retry after.
- L214: `def test_exhausted_llm_rate_limit_maps_to_503()`
  - Pytest case: exhausted llm rate limit maps to 503.

---

## `tests/test_features_ui_api.py`

**Module docstring:** API contracts for config builder / session inspector features.

**Layer / role:** Pytest suite covering milestones M1–M7, auth/rate-limit, abuse hardening, UI/API features.

- **Lines:** 50
- **Imports:** 2 · **Classes:** 0 · **Functions:** 2 · **Module vars:** 2

### Imports

- L2: `from fastapi.testclient import TestClient` — HTTP framework
- L4: `from app.main import app`

### Module-level variables / constants

- L6: **`client`** — Module/class constant or field. Default/value: `TestClient(app)`.
- L8: **`BASE`** — Module/class constant or field. Default/value: `{'language': 'pl', 'evaluationCriteria': 'REST', 'learningContext': {'goals': [{'id': 'g1', 'description': 'Cel 1'}]}...`.

### Functions

- L18: `def test_list_conversations_and_count_active_in_health()`
  - Pytest case: list conversations and count active in health.
- L40: `def test_ui_index_and_scenarios_still_served()`
  - Pytest case: ui index and scenarios still served.

---

## `tests/test_m1.py`

**Layer / role:** Pytest suite covering milestones M1–M7, auth/rate-limit, abuse hardening, UI/API features.

- **Lines:** 50
- **Imports:** 3 · **Classes:** 0 · **Functions:** 3 · **Module vars:** 2

### Imports

- L1: `import pytest` — testing
- L2: `from fastapi.testclient import TestClient` — HTTP framework
- L3: `from app.main import app`

### Module-level variables / constants

- L5: **`client`** — Module/class constant or field. Default/value: `TestClient(app)`.
- L7: **`VALID_CONFIG`** — Module/class constant or field. Default/value: `{'language': 'pl', 'evaluationCriteria': 'strict', 'learningContext': {'goals': [{'id': 'g1', 'description': 'Cel 1'}...`.

### Functions

- L15: `def test_validate_config_valid()`
  - Pytest case: validate config valid.
- L20: `def test_validate_config_invalid_checkpoint()`
  - Pytest case: validate config invalid checkpoint.
- L28: `def test_conversation_lifecycle()`
  - Pytest case: conversation lifecycle.

---

## `tests/test_m2.py`

**Layer / role:** Pytest suite covering milestones M1–M7, auth/rate-limit, abuse hardening, UI/API features.

- **Lines:** 79
- **Imports:** 2 · **Classes:** 0 · **Functions:** 3 · **Module vars:** 2

### Imports

- L1: `from fastapi.testclient import TestClient` — HTTP framework
- L2: `from app.main import app`

### Module-level variables / constants

- L4: **`client`** — Module/class constant or field. Default/value: `TestClient(app)`.
- L6: **`CONFIG_WITH_PRELAB`** — Module/class constant or field. Default/value: `{'language': 'pl', 'evaluationCriteria': 'strict', 'learningContext': {'goals': [{'id': 'g1', 'description': 'Cel 1'}...`.

### Functions

- L28: `def test_prelab_gate_blocks_messages()`
  - Pytest case: prelab gate blocks messages.
- L40: `def test_prelab_submit_fail_and_limits()`
  - Pytest case: prelab submit fail and limits.
- L64: `def test_prelab_submit_success_unlocks_chat()`
  - Pytest case: prelab submit success unlocks chat.

---

## `tests/test_m3.py`

**Layer / role:** Pytest suite covering milestones M1–M7, auth/rate-limit, abuse hardening, UI/API features.

- **Lines:** 170
- **Imports:** 9 · **Classes:** 1 · **Functions:** 1 · **Module vars:** 2

### Imports

- L1: `import json` — stdlib
- L2: `from typing import List` — stdlib
- L2: `from typing import Dict` — stdlib
- L2: `from typing import Optional` — stdlib
- L3: `from fastapi.testclient import TestClient` — HTTP framework
- L4: `from app.main import app`
- L5: `from app.domain.ports import LlmPort` — domain types/ports/exceptions
- L5: `from app.domain.ports import LlmResult` — domain types/ports/exceptions
- L6: `from app.api.deps import get_llm_port` — API helpers/routers

### Module-level variables / constants

- L8: **`client`** — Module/class constant or field. Default/value: `TestClient(app)`.
- L55: **`LAB_CONFIG`** — Module/class constant or field. Default/value: `{'language': 'pl', 'evaluationCriteria': 'Poprawny kontroler Spring REST', 'maxTokensPerSession': 300, 'learningConte...`.

### Class `ScriptedMockLlm(LlmPort)`

- **Line:** 10
- **Description:** Symuluje kolejne tury rozmowy sokratycznej prowadzące studenta do 10/10.

#### Methods

- L12: `def __init__(self)`
  - Defined at line 12.
- L15: `def is_configured(self) -> bool`
  - Defined at line 15. Returns `bool`.
- L18: `def generate_json(self, system_prompt: str, messages: List[Dict[str, str]], model_override: Optional[str]) -> LlmResult`
  - Defined at line 18. Returns `LlmResult`.

### Functions

- L79: `def test_m3_full_happy_path_to_10_out_of_10()`
  - Pytest case: m3 full happy path to 10 out of 10.

---

## `tests/test_m4.py`

**Layer / role:** Pytest suite covering milestones M1–M7, auth/rate-limit, abuse hardening, UI/API features.

- **Lines:** 185
- **Imports:** 12 · **Classes:** 3 · **Functions:** 4 · **Module vars:** 2

### Imports

- L1: `import json` — stdlib
- L2: `from typing import List` — stdlib
- L2: `from typing import Dict` — stdlib
- L2: `from typing import Optional` — stdlib
- L2: `from typing import Iterator` — stdlib
- L3: `from fastapi.testclient import TestClient` — HTTP framework
- L4: `from app.main import app`
- L5: `from app.domain.ports import LlmPort` — domain types/ports/exceptions
- L5: `from app.domain.ports import LlmResult` — domain types/ports/exceptions
- L6: `from app.api.deps import get_llm_port` — API helpers/routers
- L7: `from app.infrastructure.llm_errors import LlmRateLimitError` — infrastructure adapters
- L7: `from app.infrastructure.llm_errors import execute_with_retry_and_fallback` — infrastructure adapters

### Module-level variables / constants

- L9: **`client`** — Module/class constant or field. Default/value: `TestClient(app)`.
- L11: **`BASE_CONFIG`** — Module/class constant or field. Default/value: `{'language': 'pl', 'evaluationCriteria': 'Poprawny serwis', 'learningContext': {'goals': [{'id': 'g1', 'description':...`.

### Class `BadJsonMockLlm(LlmPort)`

- **Line:** 26
- **Description:** Class inheriting from LlmPort.

#### Methods

- L27: `def is_configured(self) -> bool`
  - Defined at line 27. Returns `bool`.
- L30: `def generate_json(self, system_prompt: str, messages: List[Dict[str, str]], model_override: Optional[str]) -> LlmResult`
  - Defined at line 30. Returns `LlmResult`.

### Class `LanguageDriftMockLlm(LlmPort)`

- **Line:** 38
- **Description:** Class inheriting from LlmPort.

#### Methods

- L39: `def __init__(self)`
  - Defined at line 39.
- L42: `def is_configured(self) -> bool`
  - Defined at line 42. Returns `bool`.
- L45: `def generate_json(self, system_prompt: str, messages: List[Dict[str, str]], model_override: Optional[str]) -> LlmResult`
  - Defined at line 45. Returns `LlmResult`.

### Class `DeterministicStreamAndSyncLlm(LlmPort)`

- **Line:** 68
- **Description:** Class inheriting from LlmPort.

#### Methods

- L69: `def __init__(self)`
  - Defined at line 69.
- L83: `def is_configured(self) -> bool`
  - Defined at line 83. Returns `bool`.
- L86: `def generate_json(self, system_prompt: str, messages: List[Dict[str, str]], model_override: Optional[str]) -> LlmResult`
  - Defined at line 86. Returns `LlmResult`.
- L93: `def stream_json(self, system_prompt: str, messages: List[Dict[str, str]], model_override: Optional[str]) -> Iterator[str]`
  - Defined at line 93. Returns `Iterator[str]`.

### Functions

- L100: `def test_bad_json_does_not_return_500()`
  - Pytest case: bad json does not return 500.
- L113: `def test_language_drift_triggers_retry_and_fixes_language()`
  - Pytest case: language drift triggers retry and fixes language.
- L128: `def test_llm_errors_429_switches_to_fallback_model()`
  - Pytest case: llm errors 429 switches to fallback model.
- L147: `def test_stream_ndjson_and_sync_equivalence()`
  - Pytest case: stream ndjson and sync equivalence.

---

## `tests/test_m5.py`

**Layer / role:** Pytest suite covering milestones M1–M7, auth/rate-limit, abuse hardening, UI/API features.

- **Lines:** 167
- **Imports:** 9 · **Classes:** 1 · **Functions:** 2 · **Module vars:** 2

### Imports

- L1: `import json` — stdlib
- L2: `from typing import List` — stdlib
- L2: `from typing import Dict` — stdlib
- L2: `from typing import Optional` — stdlib
- L3: `from fastapi.testclient import TestClient` — HTTP framework
- L4: `from app.main import app`
- L5: `from app.domain.ports import LlmPort` — domain types/ports/exceptions
- L5: `from app.domain.ports import LlmResult` — domain types/ports/exceptions
- L6: `from app.api.deps import get_llm_port` — API helpers/routers

### Module-level variables / constants

- L8: **`client`** — Module/class constant or field. Default/value: `TestClient(app)`.
- L40: **`M5_CONFIG`** — Module/class constant or field. Default/value: `{'language': 'pl', 'evaluationCriteria': 'Poprawna metoda calculateTotal', 'requireFileContext': True, 'pinnedIdentif...`.

### Class `SpyMockLlm(LlmPort)`

- **Line:** 11
- **Description:** Class inheriting from LlmPort.

#### Methods

- L12: `def __init__(self)`
  - Defined at line 12.
- L15: `def is_configured(self) -> bool`
  - Defined at line 15. Returns `bool`.
- L18: `def generate_json(self, system_prompt: str, messages: List[Dict[str, str]], model_override: Optional[str]) -> LlmResult`
  - Defined at line 18. Returns `LlmResult`.

### Functions

- L60: `def test_m5_cheat_security_blocked_and_pedagogy_rejected()`
  - Pytest case: m5 cheat security blocked and pedagogy rejected.
- L117: `def test_m5_struggle_and_hints_reveal_lifecycle()`
  - Pytest case: m5 struggle and hints reveal lifecycle.

---

## `tests/test_m6.py`

**Layer / role:** Pytest suite covering milestones M1–M7, auth/rate-limit, abuse hardening, UI/API features.

- **Lines:** 209
- **Imports:** 19 · **Classes:** 1 · **Functions:** 4 · **Module vars:** 1

### Imports

- L1: `import json` — stdlib
- L2: `import pytest` — testing
- L3: `from typing import List` — stdlib
- L3: `from typing import Dict` — stdlib
- L3: `from typing import Optional` — stdlib
- L4: `from fastapi.testclient import TestClient` — HTTP framework
- L5: `from app.main import app`
- L6: `from app.domain.ports import LlmPort` — domain types/ports/exceptions
- L6: `from app.domain.ports import LlmResult` — domain types/ports/exceptions
- L7: `from app.domain.exceptions import SsrfBlockedError` — domain types/ports/exceptions
- L8: `from unittest.mock import patch` — stdlib
- L9: `import socket` — stdlib
- L11: `from app.infrastructure.rag_chroma import validate_safe_url` — infrastructure adapters
- L11: `from app.infrastructure.rag_chroma import _strip_html` — infrastructure adapters
- L11: `from app.infrastructure.rag_chroma import _decode_fetched_content` — infrastructure adapters
- L11: `from app.infrastructure.rag_chroma import _extract_pdf_text` — infrastructure adapters
- L17: `from app.api.deps import get_llm_port` — API helpers/routers
- L17: `from app.api.deps import get_cache_port` — API helpers/routers
- L17: `from app.api.deps import get_rag_port` — API helpers/routers

### Module-level variables / constants

- L19: **`client`** — Module/class constant or field. Default/value: `TestClient(app)`.

### Class `CountingRagMockLlm(LlmPort)`

- **Line:** 22
- **Description:** Class inheriting from LlmPort.

#### Methods

- L23: `def __init__(self)`
  - Defined at line 23.
- L27: `def is_configured(self) -> bool`
  - Defined at line 27. Returns `bool`.
- L30: `def generate_json(self, system_prompt: str, messages: List[Dict[str, str]], model_override: Optional[str]) -> LlmResult`
  - Defined at line 30. Returns `LlmResult`.

### Functions

- L58: `def test_m6_ssrf_protection_blocks_unsafe_urls()`
  - Pytest case: m6 ssrf protection blocks unsafe urls.
- L87: `def test_m6_ssrf_dns_failure_is_fail_closed()`
  - Pytest case: m6 ssrf dns failure is fail closed.
- L97: `def test_m6_html_and_pdf_material_extraction()`
  - Pytest case: m6 html and pdf material extraction.
- L140: `def test_m6_rag_sources_cache_hit_and_checkpoint_unlock()`
  - Pytest case: m6 rag sources cache hit and checkpoint unlock.

---

## `tests/test_m7.py`

**Layer / role:** Pytest suite covering milestones M1–M7, auth/rate-limit, abuse hardening, UI/API features.

- **Lines:** 160
- **Imports:** 14 · **Classes:** 1 · **Functions:** 3 · **Module vars:** 1

### Imports

- L1: `import json` — stdlib
- L2: `from typing import List` — stdlib
- L2: `from typing import Dict` — stdlib
- L2: `from typing import Optional` — stdlib
- L2: `from typing import Any` — stdlib
- L3: `from fastapi.testclient import TestClient` — HTTP framework
- L4: `from app.main import app`
- L5: `from app.domain.ports import LlmPort` — domain types/ports/exceptions
- L5: `from app.domain.ports import LlmResult` — domain types/ports/exceptions
- L6: `from app.infrastructure.webhooks import HttpWebhookAdapter` — infrastructure adapters
- L7: `from app.api.deps import get_llm_port` — API helpers/routers
- L7: `from app.api.deps import get_webhook_port` — API helpers/routers
- L7: `from app.api.deps import get_rag_port` — API helpers/routers
- L7: `from app.api.deps import repo` — API helpers/routers

### Module-level variables / constants

- L14: **`client`** — Module/class constant or field. Default/value: `TestClient(app)`.

### Class `M7MockLlm(LlmPort)`

- **Line:** 17
- **Description:** Class inheriting from LlmPort.

#### Methods

- L18: `def is_configured(self) -> bool`
  - Defined at line 18. Returns `bool`.
- L21: `def generate_json(self, system_prompt: str, messages: List[Dict[str, str]], model_override: Optional[str]) -> LlmResult`
  - Defined at line 21. Returns `LlmResult`.

### Functions

- L45: `def _sample_config() -> Dict[str, Any]`
  - Defined at line 45. Returns `Dict[str, Any]`.
- L72: `def test_m7_request_id_middleware_and_ui_endpoints()`
  - Pytest case: m7 request id middleware and ui endpoints.
- L94: `def test_m7_summary_soft_delete_and_webhooks_fire_and_forget()`
  - Pytest case: m7 summary soft delete and webhooks fire and forget.

---

## `tests/test_new_features.py`

**Module docstring:** File gates, RAG preview, force-hint, metrics, webhook buffer.

**Layer / role:** Pytest suite covering milestones M1–M7, auth/rate-limit, abuse hardening, UI/API features.

- **Lines:** 168
- **Imports:** 11 · **Classes:** 1 · **Functions:** 5 · **Module vars:** 1

### Imports

- L2: `import json` — stdlib
- L3: `from typing import Dict` — stdlib
- L3: `from typing import List` — stdlib
- L3: `from typing import Optional` — stdlib
- L5: `from fastapi.testclient import TestClient` — HTTP framework
- L7: `from app.main import app`
- L8: `from app.api.deps import get_llm_port` — API helpers/routers
- L9: `from app.domain.ports import LlmPort` — domain types/ports/exceptions
- L9: `from app.domain.ports import LlmResult` — domain types/ports/exceptions
- L10: `from app.infrastructure.webhooks import HttpWebhookAdapter` — infrastructure adapters
- L11: `from app.api.deps import get_webhook_port` — API helpers/routers

### Module-level variables / constants

- L13: **`client`** — Module/class constant or field. Default/value: `TestClient(app)`.

### Class `QuietLlm(LlmPort)`

- **Line:** 16
- **Description:** Class inheriting from LlmPort.

#### Methods

- L17: `def is_configured(self) -> bool`
  - Defined at line 17. Returns `bool`.
- L20: `def generate_json(self, system_prompt: str, messages: List[Dict[str, str]], model_override: Optional[str]) -> LlmResult`
  - Defined at line 20. Returns `LlmResult`.

### Functions

- L37: `def _cfg()`
  - Defined at line 37.
- L53: `def test_allowed_and_blocked_files_enforced()`
  - Pytest case: allowed and blocked files enforced.
- L107: `def test_rag_preview_on_start_with_inline_content()`
  - Pytest case: rag preview on start with inline content.
- L124: `def test_force_hint_bypasses_streak_and_audits()`
  - Pytest case: force hint bypasses streak and audits.
- L142: `def test_metrics_and_webhook_recent_buffer()`
  - Pytest case: metrics and webhook recent buffer.

---

# Non-Python assets

## `.env.example`

Example environment variables for Settings (LLM URLs, JWT, CORS, cache, RAG, webhooks). Copy to `.env`.

## `.env`

Local secrets/config (not for commit). Same keys as Settings / `.env.example`.

## `.gitignore`

Git ignore rules for venv, caches, `.env`, chroma data, IDE files.

## `AGENTS.md`

Architectural rules for hexagonal layers (domain/application/infrastructure/api).

## `README.md`

Project overview and quick-start.

## `requirements.txt`

Python dependencies for install.

## `schemas/sensei-config.schema.json`

JSON Schema for SenseiConfig payload validation / Spring contract.

## `app/static/index.html`

Lab chat UI (served when `AI_EXPOSE_UI=true`).

## `app/static/scenarios.html`

Scenarios / demo UI page.

## `Docs/FEATURES_ADVANCED.md`

Documentation of advanced product features.

## `Docs/UNIVERSITY_HARDENING_REVIEW.md`

Security/hardening review notes for university deployment.

## `Docs/milestones/M0_Foundation.md`

Milestone M0: foundation.

## `Docs/milestones/M1_Sessions_And_Config.md`

Milestone M1: sessions and config.

## `Docs/milestones/M3_LLM.md`

Milestone M3: LLM integration.

## `Docs/milestones/M4_Restrictions.md`

Milestone M4: IDE/file restrictions.

## `Docs/milestones/M5_Anti_Bypass.md`

Milestone M5: anti-bypass / pedagogy gates.

## `Docs/milestones/M6_RAG_and_cache.md`

Milestone M6: RAG + response cache.

## `Docs/PROJECT_REFERENCE.md`

This file — full symbol-level project reference.

### `sensei-config.schema.json` top-level properties

- **Title:** SenseiConfig
- **`language`**: `string`
- **`learningContext`**: `object`
- **`checkpoints`**: `array`

## `requirements.txt` packages

- `fastapi>=0.109.0`
- `uvicorn[standard]>=0.27.0`
- `pydantic>=2.5.0`
- `pydantic-settings>=2.1.0`
- `python-dotenv>=1.0.1`
- `openai>=1.12.0`
- `httpx>=0.27.0`
- `PyJWT>=2.8.0`
- `chromadb>=0.4.22`
- `beautifulsoup4>=4.12.3`
- `pypdf>=4.0.0`
- `jsonschema>=4.21.1`
- `pytest>=8.0.0`
- `starlette`

## `.env.example` keys


*# LLM Configuration*
- **`LLM_BASE_URL`** = `http://127.0.0.1:11434/v1`
- **`LLM_API_KEY`** = `ollama`
- **`MAIN_MODEL`** = `qwen2.5-coder:7b`
- **`SECURITY_MODEL`** = `qwen2.5-coder:7b`

*# Security and Rate limitation*

*# Production/staging: keep AI_AUTH_ENABLED=true. Spring signs HS256 JWT with:*

*#   exp, sub (studentId), aud, iss; optional role / roles, labId*

*# Local playground only may set AI_AUTH_ENABLED=false*
- **`AI_AUTH_ENABLED`** = `true`
- **`AI_JWT_SECRET`** = `CHANGE_ME_shared_with_spring_min_32_chars`
- **`AI_JWT_AUDIENCE`** = `pja-sensei-ai`
- **`AI_JWT_ISSUER`** = `pja-spring`
- **`AI_PROFESSOR_ROLES`** = `["professor","admin"]`
- **`AI_EXPOSE_DOCS`** = `false`
- **`AI_EXPOSE_UI`** = `false`
- **`RATE_LIMIT_PER_MINUTE`** = `60`
- **`CONVERSATION_TTL_SECONDS`** = `7200`

*# Cache*
- **`CACHE_SIZE`** = `1000`

*# OLD: CACHE_TTL=3600  # ignored by Settings (wrong key name)*
- **`CACHE_TTL_SECONDS`** = `3600`

*# Integration*
- **`TELEMETRY_URL`** = ``
- **`SUMMARY_WEBHOOK_URL`** = ``
- **`WEBHOOK_EVENT_BUFFER_SIZE`** = `50`

*# Network*

*# OLD: CORS_ORIGINS=["*"]  TRUST_X_FORWARDED_FOR=true*
- **`CORS_ORIGINS`** = `["https://labs.pja.edu.pl"]`
- **`TRUST_X_FORWARDED_FOR`** = `false`
- **`SECURITY_FAIL_CLOSED`** = `true`
- **`SECURITY_ALWAYS_CLASSIFY`** = `false`

### `app/static/index.html` details

- **HTML title:** PJA-Sensei – Laboratorium AI
- **Approx. size:** 29240 chars, 850 lines
- **`<script>` blocks:** 1

### `app/static/scenarios.html` details

- **HTML title:** PJA-Sensei — Scenariusze Testowe E2E
- **Approx. size:** 16014 chars, 423 lines
- **`<script>` blocks:** 1
