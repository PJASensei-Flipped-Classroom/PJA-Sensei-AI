# app/ — api

Opisy linia-po-linii (język: polski). Puste linie pominięte w wypunktowaniu, ale nie zmieniają numeracji `L`.

<a id="app-api-init-py"></a>
## `app/api/__init__.py`
Pakiet warstwy HTTP.

Liczba linii: **1**.

### Opis linia-po-linii

- **L1:** Docstring: HTTP layer: routers, schemas, deps, middleware.

<a id="app-api-deps-py"></a>
## `app/api/deps.py`
Zależności FastAPI: kontener, rate limit, walidacja requestu wiadomości.

Liczba linii: **84**.

### Opis linia-po-linii

- **L1:** Docstring: FastAPI dependencies.
- **L3–L3:** Importy — L3: `from __future__ import annotations`.
- **L5–L6:** Importy — L5: `from fastapi import BackgroundTasks, Request`; L6: `from fastapi.responses import JSONResponse`.
- **L8–L19:** Importy — L8: `from app.api.errors import blocked_payload`; L9: `from app.api.guards import (`; L10: `ensure_prompt_safe,`; L11: `missing_file_context_response,`; L12: `require_conversation,`; L13: `requires_file_context,`; L14: `)`; L15: `from app.api.schemas.requests import MessageRequest`; L16: `from app.application.container import AppContainer`; L17: `from app.core.metrics import metrics`; L18: `from app.core.rate_limit import client_key, rate_limiter`; L19: `from app.domain.exceptions import PrelabRequired, TokenBudgetExceeded`.
- **L21:** Przypisanie `_container: AppContainer | None` ← `None`.
- **L24:** Definicja funkcji/metody `init_container`, zwraca `AppContainer`.
- **L25:** (w `init_container`) Deklaracja zasięgu: `global _container`.
- **L26:** (w `init_container`) Przypisanie `_container` ← `container or AppContainer()`.
- **L27:** (w `init_container`) Zwraca: `_container`.
- **L30:** Definicja funkcji/metody `get_container`, zwraca `AppContainer`.
- **L31:** (w `get_container`) Deklaracja zasięgu: `global _container`.
- **L32:** (w `get_container`) Warunek `if` — gdy `_container is None`.
- **L33:** (w `get_container`) Przypisanie `_container` ← `AppContainer()`.
- **L34:** (w `get_container`) Zwraca: `_container`.
- **L37:** Definicja funkcji/metody `enforce_rate_limit`, zwraca `None`.
- **L38:** (w `enforce_rate_limit`) Przypisanie `conv_id` ← `request.path_params.get("conversation_id")`.
- **L39:** (w `enforce_rate_limit`) Wykonuje: `rate_limiter.check(client_key(request, conv_id))`.
- **L42–L48:** (w `validate_message_request`) Wyrażenie wieloliniowe — L42: Definicja funkcji/metody `?`. | L43: Element listy/argumentów: `conversation_id: str,`. | L44: Element listy/argumentów: `request: MessageRequest,`. | L45: Element listy/argumentów: `http_request: Request,`. | L46: Przypisanie `background_tasks: BackgroundTasks | None` ← `None,`. | L47: Przypisanie `container: AppContainer | None` ← `None,`. | L48: Wykonuje: `) -> tuple[object, JSONResponse | None]:`.
- **L49:** (w `validate_message_request`) Przypisanie `container` ← `container or get_container()`.
- **L50:** (w `validate_message_request`) Wykonuje: `metrics.inc("requests_total")`.
- **L51:** (w `validate_message_request`) Przypisanie `conversation` ← `require_conversation(container, conversation_id)`.
- **L52:** (w `validate_message_request`) Przypisanie `language` ← `conversation.config.language`.
- **L54:** (w `validate_message_request`) Blok `try` — chroniony kod, potem except/finally.
- **L55:** (w `validate_message_request`) Wykonuje: `container.sessions.ensure_prelab_passed(conversation)`.
- **L56:** (w `validate_message_request`) Wykonuje: `container.sessions.ensure_token_budget(conversation)`.
- **L57:** (w `validate_message_request`) Przechwytuje wyjątek `PrelabRequired`.
- **L58–L60:** (w `validate_message_request`) Wyrażenie wieloliniowe — L58: Zwraca: `conversation, JSONResponse(`. | L59: Przypisanie `blocked_payload(language, "prelab"), status_code` ← `403`. | L60: Zamknięcie wyrażenia (`)`).
- **L61:** (w `validate_message_request`) Przechwytuje wyjątek `TokenBudgetExceeded`.
- **L62:** (w `validate_message_request`) Warunek `if` — gdy `background_tasks is not None and not conversation.summary_generated`.
- **L63:** (w `validate_message_request`) Przypisanie `conversation.summary_generated` ← `True`.
- **L64–L66:** (w `validate_message_request`) Wyrażenie wieloliniowe — L64: Wykonuje: `background_tasks.add_task(`. | L65: Wykonuje: `container.summary.generate_summary, conversation_id`. | L66: Zamknięcie wyrażenia (`)`).
- **L67–L69:** (w `validate_message_request`) Wyrażenie wieloliniowe — L67: Zwraca: `conversation, JSONResponse(`. | L68: Przypisanie `blocked_payload(language, "budget"), status_code` ← `403`. | L69: Zamknięcie wyrażenia (`)`).
- **L71:** (w `validate_message_request`) Warunek `if` — gdy `requires_file_context(conversation, request)`.
- **L72:** (w `validate_message_request`) Przypisanie `payload` ← `missing_file_context_response(language).model_dump()`.
- **L73:** (w `validate_message_request`) Przypisanie `payload["message_id"]` ← `"rejected"`.
- **L74:** (w `validate_message_request`) Zwraca: `conversation, JSONResponse(payload)`.
- **L76–L78:** (w `validate_message_request`) Wyrażenie wieloliniowe — L76: Przypisanie `blocked` ← `await ensure_prompt_safe(`. | L77: Wykonuje: `container.security, request.question, language`. | L78: Zamknięcie wyrażenia (`)`).
- **L79:** (w `validate_message_request`) Warunek `if` — gdy `blocked`.
- **L80:** (w `validate_message_request`) Przypisanie `payload` ← `blocked.model_dump()`.
- **L81:** (w `validate_message_request`) Przypisanie `payload["message_id"]` ← `"blocked"`.
- **L82:** (w `validate_message_request`) Zwraca: `conversation, JSONResponse(payload)`.
- **L84:** (w `validate_message_request`) Zwraca: `conversation, None`.

<a id="app-api-errors-py"></a>
## `app/api/errors.py`
Handlery wyjątków domenowych oraz payloady blokad prelab/budget.

Liczba linii: **79**.

### Opis linia-po-linii

- **L1:** Docstring: Map domain exceptions to HTTP responses.
- **L3–L3:** Importy — L3: `from __future__ import annotations`.
- **L5–L6:** Importy — L5: `from fastapi import FastAPI, Request`; L6: `from fastapi.responses import JSONResponse`.
- **L8–L13:** Importy — L8: `from app.domain.exceptions import (`; L9: `PrelabRequired,`; L10: `RevealNotAllowed,`; L11: `TokenBudgetExceeded,`; L12: `UnknownConversation,`; L13: `)`.
- **L16:** Definicja funkcji/metody `blocked_payload`, zwraca `dict`.
- **L17:** (w `blocked_payload`) Warunek `if` — gdy `kind == "prelab"`.
- **L18–L22:** (w `blocked_payload`) Wyrażenie wieloliniowe — L18: Przypisanie `answer` ← `(`. | L19: Wykonuje: `"Complete the pre-lab quiz before chatting about the assignment."`. | L20: Warunek `if` — gdy `language == "en"`. | L21: Wykonuje: `else "Ukończ quiz pre-lab, zanim zaczniesz czat o zadaniu."`. | L22: Zamknięcie wyrażenia (`)`).
- **L23:** (w `blocked_payload`) Przypisanie `feedback` ← `"Pre-lab not passed." if language == "en" else "Pre-lab niezaliczony."`.
- **L24:** (w `blocked_payload`) Przypisanie `message_id` ← `"prelab_required"`.
- **L25:** (w `blocked_payload`) Gałąź `else` (pozostałe przypadki).
- **L26–L30:** (w `blocked_payload`) Wyrażenie wieloliniowe — L26: Przypisanie `answer` ← `(`. | L27: Wykonuje: `"Token budget for this session has been exhausted."`. | L28: Warunek `if` — gdy `language == "en"`. | L29: Wykonuje: `else "Budżet tokenów dla tej sesji został wyczerpany."`. | L30: Zamknięcie wyrażenia (`)`).
- **L31:** (w `blocked_payload`) Przypisanie `feedback` ← `"maxTokensPerSession exceeded"`.
- **L32:** (w `blocked_payload`) Przypisanie `message_id` ← `"token_budget_exceeded"`.
- **L33–L43:** (w `blocked_payload`) Wyrażenie wieloliniowe — L33: Zwraca: `{`. | L34: Element listy/argumentów: `"message_id": message_id,`. | L35: Element listy/argumentów: `"answer": answer,`. | L36: Element listy/argumentów: `"prompt_score": 1,`. | L37: Element listy/argumentów: `"prompt_feedback": feedback,`. | L38: Element listy/argumentów: `"tokens_used": 0,`. | L39: Element listy/argumentów: `"penalty_applied": False,`. | L40: Element listy/argumentów: `"sources": [],`. | L41: Element listy/argumentów: `"suggested_next_step": None,`. | L42: Element listy/argumentów: `"goal_progress": [],`. | L43: Zamknięcie wyrażenia (`}`).
- **L46:** Definicja funkcji/metody `_language_from_request`, zwraca `str`.
- **L47:** (w `_language_from_request`) Przypisanie `container` ← `getattr(request.app.state, "container", None)`.
- **L48:** (w `_language_from_request`) Przypisanie `conv_id` ← `request.path_params.get("conversation_id")`.
- **L49:** (w `_language_from_request`) Warunek `if` — gdy `container and conv_id`.
- **L50:** (w `_language_from_request`) Przypisanie `conv` ← `container.conversations.get(conv_id)`.
- **L51:** (w `_language_from_request`) Warunek `if` — gdy `conv is not None`.
- **L52:** (w `_language_from_request`) Zwraca: `conv.config.language`.
- **L53:** (w `_language_from_request`) Zwraca: `"pl"`.
- **L56:** Definicja funkcji/metody `register_exception_handlers`, zwraca `None`.
- **L57:** (w `register_exception_handlers`) Dekorator `@app.exception_handler(UnknownConversation)` (np. route FastAPI, fixture, dataclass).
- **L58:** Definicja asynchronicznej funkcji/metody `_unknown_conversation`.
- **L59–L61:** (w `register_exception_handlers`) Wyrażenie wieloliniowe — L59: Zwraca: `JSONResponse(`. | L60: Przypisanie `status_code` ← `404, content={"detail": "Conversation not found"}`. | L61: Zamknięcie wyrażenia (`)`).
- **L63:** (w `register_exception_handlers`) Dekorator `@app.exception_handler(PrelabRequired)` (np. route FastAPI, fixture, dataclass).
- **L64:** Definicja asynchronicznej funkcji/metody `_prelab_required`.
- **L65–L68:** (w `register_exception_handlers`) Wyrażenie wieloliniowe — L65: Zwraca: `JSONResponse(`. | L66: Przypisanie `status_code` ← `403,`. | L67: Przypisanie `content` ← `blocked_payload(_language_from_request(request), "prelab"),`. | L68: Zamknięcie wyrażenia (`)`).
- **L70:** (w `register_exception_handlers`) Dekorator `@app.exception_handler(TokenBudgetExceeded)` (np. route FastAPI, fixture, dataclass).
- **L71:** Definicja asynchronicznej funkcji/metody `_token_budget`.
- **L72–L75:** (w `register_exception_handlers`) Wyrażenie wieloliniowe — L72: Zwraca: `JSONResponse(`. | L73: Przypisanie `status_code` ← `403,`. | L74: Przypisanie `content` ← `blocked_payload(_language_from_request(request), "budget"),`. | L75: Zamknięcie wyrażenia (`)`).
- **L77:** (w `register_exception_handlers`) Dekorator `@app.exception_handler(RevealNotAllowed)` (np. route FastAPI, fixture, dataclass).
- **L78:** Definicja asynchronicznej funkcji/metody `_reveal_not_allowed`.
- **L79:** (w `register_exception_handlers`) Zwraca: `JSONResponse(status_code=403, content={"detail": exc.detail})`.

<a id="app-api-guards-py"></a>
## `app/api/guards.py`
Guardy: istnienie konwersacji, file-context, safety promptu.

Liczba linii: **74**.

### Opis linia-po-linii

- **L1:** Docstring: HTTP guards for conversation access and prompt safety.
- **L3–L3:** Importy — L3: `from __future__ import annotations`.
- **L5–L5:** Importy — L5: `from fastapi import HTTPException`.
- **L7–L12:** Importy — L7: `from app.adapters.security import SecurityService`; L8: `from app.api.schemas.requests import MessageRequest`; L9: `from app.api.schemas.responses import MessageResponse`; L10: `from app.application.container import AppContainer`; L11: `from app.domain.conversation import Conversation`; L12: `from app.domain.exceptions import UnknownConversation`.
- **L15–L17:** (w `require_conversation`) Wyrażenie wieloliniowe — L15: Definicja funkcji/metody `?`. | L16: Wykonuje: `container: AppContainer, conversation_id: str`. | L17: Wykonuje: `) -> Conversation:`.
- **L18:** (w `require_conversation`) Przypisanie `conversation` ← `container.conversations.get(conversation_id)`.
- **L19:** (w `require_conversation`) Warunek `if` — gdy `not conversation`.
- **L20–L23:** (w `require_conversation`) Wyrażenie wieloliniowe — L20: Rzuca wyjątek: `HTTPException(`. | L21: Przypisanie `status_code` ← `404,`. | L22: Przypisanie `detail` ← `"Conversation not found",`. | L23: Zamknięcie wyrażenia (`)`).
- **L24:** (w `require_conversation`) Zwraca: `conversation`.
- **L27:** Definicja funkcji/metody `get_conversation`, zwraca `Conversation`.
- **L28:** Docstring: Raise domain UnknownConversation (mapped by exception handlers).
- **L29:** (w `get_conversation`) Przypisanie `conversation` ← `container.conversations.get(conversation_id)`.
- **L30:** (w `get_conversation`) Warunek `if` — gdy `not conversation`.
- **L31:** (w `get_conversation`) Rzuca wyjątek: `UnknownConversation(conversation_id)`.
- **L32:** (w `get_conversation`) Zwraca: `conversation`.
- **L35:** Definicja funkcji/metody `missing_file_context_response`, zwraca `MessageResponse`.
- **L36–L53:** (w `missing_file_context_response`) Wyrażenie wieloliniowe — L36: Zwraca: `MessageResponse(`. | L37: Przypisanie `answer` ← `(`. | L38: Wykonuje: `"To zadanie wymaga analizy kodu. Otwórz odpowiedni plik w edytorze VS Code zanim zadasz pytanie."`. | L39: Warunek `if` — gdy `language == "pl"`. | L40: Wykonuje: `else "This task requires code analysis. Please open the relevant file in your VS Code editor before asking."`. | L41: Element listy/argumentów: `),`. | L42: Przypisanie `prompt_score` ← `1,`. | L43: Przypisanie `prompt_feedback` ← `(`. | L44: Wykonuje: `"Brak przesłanego kontekstu pliku (Naruszenie ideRestrictions)."`. | L45: Warunek `if` — gdy `language == "pl"`. | L46: Wykonuje: `else "Missing file context (ideRestrictions violation)."`. | L47: Element listy/argumentów: `),`. | L48: Przypisanie `tokens_used` ← `0,`. | L49: Przypisanie `penalty_applied` ← `False,`. | L50: Przypisanie `sources` ← `[],`. | L51: Przypisanie `suggested_next_step` ← `None,`. | L52: Przypisanie `goal_progress` ← `[],`. | L53: Zamknięcie wyrażenia (`)`).
- **L56–L58:** (w `requires_file_context`) Wyrażenie wieloliniowe — L56: Definicja funkcji/metody `?`. | L57: Wykonuje: `conversation: Conversation, request: MessageRequest`. | L58: Wykonuje: `) -> bool:`.
- **L59:** (w `requires_file_context`) Przypisanie `restrictions` ← `conversation.config.ideRestrictions`.
- **L60:** (w `requires_file_context`) Warunek `if` — gdy `not restrictions or not restrictions.requireFileContextForChat`.
- **L61:** (w `requires_file_context`) Zwraca: `False`.
- **L62:** (w `requires_file_context`) Zwraca: `not request.code_context.current_code.strip()`.
- **L65–L69:** (w `ensure_prompt_safe`) Wyrażenie wieloliniowe — L65: Definicja funkcji/metody `?`. | L66: Element listy/argumentów: `security_service: SecurityService,`. | L67: Element listy/argumentów: `question: str,`. | L68: Element listy/argumentów: `language: str,`. | L69: Wykonuje: `) -> MessageResponse | None:`.
- **L70:** (w `ensure_prompt_safe`) Przypisanie `is_safe` ← `await security_service.is_prompt_safe(question)`.
- **L71:** (w `ensure_prompt_safe`) Warunek `if` — gdy `is_safe`.
- **L72:** (w `ensure_prompt_safe`) Zwraca: `None`.
- **L73:** (w `ensure_prompt_safe`) Przypisanie `blocked` ← `security_service.get_blocked_response(language)`.
- **L74:** (w `ensure_prompt_safe`) Zwraca: `MessageResponse(**blocked)`.

<a id="app-api-middleware-py"></a>
## `app/api/middleware.py`
Middleware X-Request-Id + ContextVar.

Liczba linii: **21**.

### Opis linia-po-linii

- **L1:** Docstring: Request-id middleware and context.
- **L3–L3:** Importy — L3: `from __future__ import annotations`.
- **L5–L6:** Importy — L5: `import uuid`; L6: `from contextvars import ContextVar`.
- **L8–L9:** Importy — L8: `from fastapi import Request, Response`; L9: `from starlette.middleware.base import BaseHTTPMiddleware`.
- **L11:** Przypisanie `request_id_var: ContextVar[str]` ← `ContextVar("request_id", default="-")`.
- **L14:** Definicja klasy `RequestIdMiddleware` dziedziczy/parametryzuje: `(BaseHTTPMiddleware)`.
- **L15:** Definicja asynchronicznej funkcji/metody `dispatch`.
- **L16:** (w `RequestIdMiddleware`) Przypisanie `rid` ← `request.headers.get("x-request-id") or str(uuid.uuid4())`.
- **L17:** (w `RequestIdMiddleware`) Wykonuje: `request_id_var.set(rid)`.
- **L18:** (w `RequestIdMiddleware`) Przypisanie `request.state.request_id` ← `rid`.
- **L19:** (w `RequestIdMiddleware`) Przypisanie `response: Response` ← `await call_next(request)`.
- **L20:** (w `RequestIdMiddleware`) Przypisanie `response.headers["X-Request-Id"]` ← `rid`.
- **L21:** (w `RequestIdMiddleware`) Zwraca: `response`.

<a id="app-api-schemas-init-py"></a>
## `app/api/schemas/__init__.py`
Re-eksport modeli request/response.

Liczba linii: **33**.

### Opis linia-po-linii

- **L1–L17:** Importy — L1: `from app.api.schemas.requests import (`; L2: `FeedbackRequest,`; L3: `IdeEventRequest,`; L4: `MessageRequest,`; L5: `PreLabAnswerItem,`; L6: `PreLabSubmitRequest,`; L7: `RevealHintRequest,`; L8: `ReviewRequest,`; L9: `StartRequest,`; L10: `ValidateConfigRequest,`; L11: `)`; L12: `from app.api.schemas.responses import (`; L13: `DebugInfo,`; L14: `GoalProgressItem,`; L15: `MessageResponse,`; L16: `SourceRef,`; L17: `)`.
- **L19–L33:** Wyrażenie wieloliniowe — L19: Przypisanie `__all__` ← `[`. | L20: Element listy/argumentów: `"DebugInfo",`. | L21: Element listy/argumentów: `"FeedbackRequest",`. | L22: Element listy/argumentów: `"GoalProgressItem",`. | L23: Element listy/argumentów: `"IdeEventRequest",`. | L24: Element listy/argumentów: `"MessageRequest",`. | L25: Element listy/argumentów: `"MessageResponse",`. | L26: Element listy/argumentów: `"PreLabAnswerItem",`. | L27: Element listy/argumentów: `"PreLabSubmitRequest",`. | L28: Element listy/argumentów: `"RevealHintRequest",`. | L29: Element listy/argumentów: `"ReviewRequest",`. | L30: Element listy/argumentów: `"SourceRef",`. | L31: Element listy/argumentów: `"StartRequest",`. | L32: Element listy/argumentów: `"ValidateConfigRequest",`. | L33: Zamknięcie wyrażenia (`]`).

<a id="app-api-schemas-requests-py"></a>
## `app/api/schemas/requests.py`
Modele ciał żądań HTTP (Pydantic).

Liczba linii: **53**.

### Opis linia-po-linii

- **L1:** Docstring: HTTP request bodies.
- **L3–L3:** Importy — L3: `from __future__ import annotations`.
- **L5–L5:** Importy — L5: `from typing import Any, Literal`.
- **L7–L7:** Importy — L7: `from pydantic import BaseModel, Field`.
- **L9–L9:** Importy — L9: `from app.domain.sensei import CodeContext, SenseiConfig`.
- **L12:** Definicja klasy `PreLabAnswerItem` dziedziczy/parametryzuje: `(BaseModel)`.
- **L13:** (w `PreLabAnswerItem`) Wykonuje: `id: str`.
- **L14:** (w `PreLabAnswerItem`) Wykonuje: `answer: str`.
- **L17:** Definicja klasy `PreLabSubmitRequest` dziedziczy/parametryzuje: `(BaseModel)`.
- **L18:** (w `PreLabSubmitRequest`) Wykonuje: `answers: list[PreLabAnswerItem]`.
- **L21:** Definicja klasy `FeedbackRequest` dziedziczy/parametryzuje: `(BaseModel)`.
- **L22:** (w `FeedbackRequest`) Wykonuje: `rating: int`.
- **L23:** (w `FeedbackRequest`) Przypisanie `comment: str | None` ← `None`.
- **L26:** Definicja klasy `StartRequest` dziedziczy/parametryzuje: `(BaseModel)`.
- **L27:** (w `StartRequest`) Wykonuje: `problem_description: str`.
- **L28:** (w `StartRequest`) Wykonuje: `config: SenseiConfig`.
- **L31:** Definicja klasy `MessageRequest` dziedziczy/parametryzuje: `(BaseModel)`.
- **L32:** (w `MessageRequest`) Wykonuje: `question: str`.
- **L33:** (w `MessageRequest`) Wykonuje: `code_context: CodeContext`.
- **L34:** (w `MessageRequest`) Przypisanie `client_message_id: str | None` ← `None`.
- **L37:** Definicja klasy `IdeEventRequest` dziedziczy/parametryzuje: `(BaseModel)`.
- **L38:** (w `IdeEventRequest`) Wykonuje: `type: Literal["copy_blocked", "file_opened", "paste_attempt"]`.
- **L39:** (w `IdeEventRequest`) Przypisanie `meta: dict[str, Any]` ← `Field(default_factory=dict)`.
- **L42:** Definicja klasy `ValidateConfigRequest` dziedziczy/parametryzuje: `(BaseModel)`.
- **L43:** (w `ValidateConfigRequest`) Wykonuje: `config: dict`.
- **L46:** Definicja klasy `RevealHintRequest` dziedziczy/parametryzuje: `(BaseModel)`.
- **L47:** (w `RevealHintRequest`) Przypisanie `code_context: CodeContext | None` ← `None`.
- **L48:** (w `RevealHintRequest`) Przypisanie `focus: str | None` ← `None`.
- **L51:** Definicja klasy `ReviewRequest` dziedziczy/parametryzuje: `(BaseModel)`.
- **L52:** (w `ReviewRequest`) Wykonuje: `code_context: CodeContext`.
- **L53:** (w `ReviewRequest`) Przypisanie `focus: str | None` ← `None`.

<a id="app-api-schemas-responses-py"></a>
## `app/api/schemas/responses.py`
Modele odpowiedzi HTTP (MessageResponse i powiązane).

Liczba linii: **41**.

### Opis linia-po-linii

- **L1:** Docstring: HTTP response models.
- **L3–L3:** Importy — L3: `from __future__ import annotations`.
- **L5–L6:** Importy — L5: `import uuid`; L6: `from typing import Literal`.
- **L8–L8:** Importy — L8: `from pydantic import BaseModel, Field`.
- **L11:** Definicja klasy `DebugInfo` dziedziczy/parametryzuje: `(BaseModel)`.
- **L12:** (w `DebugInfo`) Wykonuje: `is_frustrated: bool`.
- **L13:** (w `DebugInfo`) Wykonuje: `avg_score: float`.
- **L14:** (w `DebugInfo`) Wykonuje: `code_changed: bool`.
- **L17:** Definicja klasy `SourceRef` dziedziczy/parametryzuje: `(BaseModel)`.
- **L18:** (w `SourceRef`) Wykonuje: `title: str`.
- **L19:** (w `SourceRef`) Wykonuje: `url: str`.
- **L20:** (w `SourceRef`) Przypisanie `timestamp: str | None` ← `None`.
- **L21:** (w `SourceRef`) Przypisanie `page: int | None` ← `None`.
- **L24:** Definicja klasy `GoalProgressItem` dziedziczy/parametryzuje: `(BaseModel)`.
- **L25:** (w `GoalProgressItem`) Wykonuje: `goal: str`.
- **L26:** (w `GoalProgressItem`) Przypisanie `status: Literal["not_started", "in_progress", "done"]` ← `"not_started"`.
- **L29:** Definicja klasy `MessageResponse` dziedziczy/parametryzuje: `(BaseModel)`.
- **L30:** (w `MessageResponse`) Przypisanie `message_id: str` ← `Field(default_factory=lambda: str(uuid.uuid4()))`.
- **L31:** (w `MessageResponse`) Wykonuje: `answer: str`.
- **L32:** (w `MessageResponse`) Wykonuje: `prompt_score: int`.
- **L33:** (w `MessageResponse`) Wykonuje: `prompt_feedback: str`.
- **L34:** (w `MessageResponse`) Wykonuje: `tokens_used: int`.
- **L35:** (w `MessageResponse`) Przypisanie `is_cached: bool` ← `False`.
- **L36:** (w `MessageResponse`) Przypisanie `penalty_applied: bool` ← `False`.
- **L37:** (w `MessageResponse`) Przypisanie `sources: list[SourceRef]` ← `Field(default_factory=list)`.
- **L38:** (w `MessageResponse`) Przypisanie `suggested_next_step: str | None` ← `None`.
- **L39:** (w `MessageResponse`) Przypisanie `goal_progress: list[GoalProgressItem]` ← `Field(default_factory=list)`.
- **L40:** (w `MessageResponse`) Przypisanie `debug_info: DebugInfo | None` ← `None`.
- **L41:** (w `MessageResponse`) Przypisanie `client_message_id: str | None` ← `None`.

<a id="app-api-routers-init-py"></a>
## `app/api/routers/__init__.py`
Znacznik pakietu routerów (pusty).

Liczba linii: **0** (pusty plik).

### Opis linia-po-linii

- *(brak linii — plik pusty / znacznik pakietu)*

<a id="app-api-routers-health-py"></a>
## `app/api/routers/health.py`
Endpointy ops: UI `/`, `/health`, `/metrics`.

Liczba linii: **60**.

### Opis linia-po-linii

- **L1:** Docstring: Health, metrics, and tester UI.
- **L3–L3:** Importy — L3: `from __future__ import annotations`.
- **L5–L5:** Importy — L5: `from pathlib import Path`.
- **L7–L8:** Importy — L7: `from fastapi import APIRouter, Depends`; L8: `from fastapi.responses import FileResponse, PlainTextResponse`.
- **L10–L13:** Importy — L10: `from app.api.deps import get_container`; L11: `from app.application.container import AppContainer`; L12: `from app.core.config import OPENROUTER_API_KEY`; L13: `from app.core.metrics import metrics`.
- **L15:** Przypisanie `router` ← `APIRouter(tags=["ops"])`.
- **L17:** Przypisanie `INDEX_HTML` ← `Path(__file__).resolve().parents[3] / "static" / "index.html"`.
- **L20:** Dekorator `@router.get("/")` (np. route FastAPI, fixture, dataclass).
- **L21:** Definicja asynchronicznej funkcji/metody `serve_tester`.
- **L22:** (w `serve_tester`) Zwraca: `FileResponse(INDEX_HTML)`.
- **L25:** Dekorator `@router.get("/health")` (np. route FastAPI, fixture, dataclass).
- **L26:** Definicja asynchronicznej funkcji/metody `health`.
- **L27:** (w `health`) Wykonuje: `container.sessions.purge_stale_conversations()`.
- **L28–L34:** (w `health`) Wyrażenie wieloliniowe — L28: Zwraca: `{`. | L29: Element listy/argumentów: `"status": "ok",`. | L30: Element listy/argumentów: `"openrouter_key_configured": bool(OPENROUTER_API_KEY),`. | L31: Element listy/argumentów: `"conversations": len(container.conversations),`. | L32: Element listy/argumentów: `"cache_size": container.cache.size,`. | L33: Element listy/argumentów: `"chroma_ok": container.rag.chroma_ok(),`. | L34: Zamknięcie wyrażenia (`}`).
- **L37:** Dekorator `@router.get("/metrics")` (np. route FastAPI, fixture, dataclass).
- **L38–L41:** (w `get_metrics`) Wyrażenie wieloliniowe — L38: Definicja funkcji/metody `?`. | L39: Przypisanie `format: str | None` ← `None,`. | L40: Przypisanie `container: AppContainer` ← `Depends(get_container),`. | L41: Wykonuje: `):`.
- **L42–L45:** (w `get_metrics`) Wyrażenie wieloliniowe — L42: Przypisanie `extra` ← `{`. | L43: Element listy/argumentów: `"conversations": len(container.conversations),`. | L44: Element listy/argumentów: `"cache_size": container.cache.size,`. | L45: Zamknięcie wyrażenia (`}`).
- **L46:** (w `get_metrics`) Warunek `if` — gdy `format and format.lower() in ("prometheus", "prom", "text")`.
- **L47–L50:** (w `get_metrics`) Wyrażenie wieloliniowe — L47: Zwraca: `PlainTextResponse(`. | L48: Element listy/argumentów: `metrics.prometheus_text(extra),`. | L49: Przypisanie `media_type` ← `"text/plain; version=0.0.4; charset=utf-8",`. | L50: Zamknięcie wyrażenia (`)`).
- **L51:** (w `get_metrics`) Przypisanie `snap` ← `metrics.snapshot()`.
- **L52:** (w `get_metrics`) Wykonuje: `snap.update(extra)`.
- **L53:** (w `get_metrics`) Zwraca: `snap`.
- **L56:** Dekorator `@router.get("/metrics/prometheus")` (np. route FastAPI, fixture, dataclass).
- **L57–L59:** (w `get_metrics_prometheus`) Wyrażenie wieloliniowe — L57: Definicja funkcji/metody `?`. | L58: Przypisanie `container: AppContainer` ← `Depends(get_container),`. | L59: Wykonuje: `):`.
- **L60:** (w `get_metrics_prometheus`) Zwraca: `await get_metrics(format="prometheus", container=container)`.

<a id="app-api-routers-analytics-py"></a>
## `app/api/routers/analytics.py`
Endpoint eksperymentalny korelacji analitycznych.

Liczba linii: **17**.

### Opis linia-po-linii

- **L1:** Docstring: Cross-session analytics.
- **L3–L3:** Importy — L3: `from __future__ import annotations`.
- **L5–L5:** Importy — L5: `from fastapi import APIRouter, Depends`.
- **L7–L8:** Importy — L7: `from app.api.deps import get_container`; L8: `from app.application.container import AppContainer`.
- **L10:** Przypisanie `router` ← `APIRouter(tags=["analytics", "experimental"])`.
- **L13:** Dekorator `@router.get("/analytics/correlations")` (np. route FastAPI, fixture, dataclass).
- **L14–L16:** (w `analytics_correlations`) Wyrażenie wieloliniowe — L14: Definicja funkcji/metody `?`. | L15: Przypisanie `container: AppContainer` ← `Depends(get_container),`. | L16: Wykonuje: `):`.
- **L17:** (w `analytics_correlations`) Zwraca: `container.analytics.build_correlations()`.

<a id="app-api-routers-config-validate-py"></a>
## `app/api/routers/config_validate.py`
Walidacja SenseiConfig (Pydantic + JSON Schema).

Liczba linii: **53**.

### Opis linia-po-linii

- **L1:** Docstring: SenseiConfig validation endpoint.
- **L3–L3:** Importy — L3: `from __future__ import annotations`.
- **L5–L6:** Importy — L5: `import json`; L6: `from pathlib import Path`.
- **L8–L9:** Importy — L8: `from fastapi import APIRouter`; L9: `from pydantic import ValidationError`.
- **L11–L12:** Importy — L11: `from app.api.schemas.requests import ValidateConfigRequest`; L12: `from app.domain.sensei import SenseiConfig`.
- **L14:** Przypisanie `router` ← `APIRouter(tags=["config"])`.
- **L16–L18:** Wyrażenie wieloliniowe — L16: Przypisanie `SCHEMA_PATH` ← `(`. | L17: Wykonuje: `Path(__file__).resolve().parents[3] / "schemas" / "sensei-config.schema.json"`. | L18: Zamknięcie wyrażenia (`)`).
- **L21:** Dekorator `@router.post("/validate-config")` (np. route FastAPI, fixture, dataclass).
- **L22:** Definicja asynchronicznej funkcji/metody `validate_config`.
- **L23:** (w `validate_config`) Przypisanie `errors: list[str]` ← `[]`.
- **L24:** (w `validate_config`) Blok `try` — chroniony kod, potem except/finally.
- **L25:** (w `validate_config`) Wykonuje: `SenseiConfig.model_validate(payload.config)`.
- **L26:** (w `validate_config`) Przechwytuje wyjątek `ValidationError as exc`.
- **L27:** (w `validate_config`) Pętla `for` po `err in exc.errors()`.
- **L28:** (w `validate_config`) Przypisanie `loc` ← `".".join(str(x) for x in err.get("loc", []))`.
- **L29:** (w `validate_config`) Wykonuje: `errors.append(f"{loc}: {err.get('msg')}")`.
- **L31:** (w `validate_config`) Przypisanie `schema_errors: list[str]` ← `[]`.
- **L32:** (w `validate_config`) Warunek `if` — gdy `SCHEMA_PATH.exists()`.
- **L33:** (w `validate_config`) Blok `try` — chroniony kod, potem except/finally.
- **L34–L34:** Importy — L34: `import jsonschema`.
- **L36:** (w `validate_config`) Przypisanie `schema` ← `json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))`.
- **L37:** (w `validate_config`) Przypisanie `validator` ← `jsonschema.Draft202012Validator(schema)`.
- **L38:** (w `validate_config`) Pętla `for` po `err in sorted(validator.iter_errors(payload.config), key=str)`.
- **L39:** (w `validate_config`) Przypisanie `path` ← `".".join(str(p) for p in err.path) or "$"`.
- **L40:** (w `validate_config`) Wykonuje: `schema_errors.append(f"{path}: {err.message}")`.
- **L41:** (w `validate_config`) Przechwytuje wyjątek `ImportError`.
- **L42:** (w `validate_config`) Wykonuje: `schema_errors.append("jsonschema not installed; skipped schema check")`.
- **L43:** (w `validate_config`) Przechwytuje wyjątek `Exception as exc`.
- **L44:** (w `validate_config`) Wykonuje: `schema_errors.append(f"schema validation error: {exc}")`.
- **L46–L48:** (w `validate_config`) Wyrażenie wieloliniowe — L46: Przypisanie `valid` ← `not errors and not any(`. | L47: Wykonuje: `e for e in schema_errors if not e.startswith("jsonschema not installed")`. | L48: Zamknięcie wyrażenia (`)`).
- **L49–L53:** (w `validate_config`) Wyrażenie wieloliniowe — L49: Zwraca: `{`. | L50: Element listy/argumentów: `"valid": valid and not errors,`. | L51: Element listy/argumentów: `"pydantic_errors": errors,`. | L52: Element listy/argumentów: `"schema_errors": schema_errors,`. | L53: Zamknięcie wyrażenia (`}`).

<a id="app-api-routers-prelab-py"></a>
## `app/api/routers/prelab.py`
Endpointy GET/POST prelab oraz generate.

Liczba linii: **45**.

### Opis linia-po-linii

- **L1:** Docstring: Pre-lab quiz routes.
- **L3–L3:** Importy — L3: `from __future__ import annotations`.
- **L5–L5:** Importy — L5: `from fastapi import APIRouter, Depends, HTTPException`.
- **L7–L10:** Importy — L7: `from app.api.deps import get_container`; L8: `from app.api.schemas.requests import PreLabSubmitRequest`; L9: `from app.application.container import AppContainer`; L10: `from app.domain.exceptions import UnknownConversation`.
- **L12:** Przypisanie `router` ← `APIRouter(tags=["prelab"])`.
- **L15:** Dekorator `@router.get("/conversations/{conversation_id}/prelab")` (np. route FastAPI, fixture, dataclass).
- **L16–L19:** (w `get_prelab`) Wyrażenie wieloliniowe — L16: Definicja funkcji/metody `?`. | L17: Element listy/argumentów: `conversation_id: str,`. | L18: Przypisanie `container: AppContainer` ← `Depends(get_container),`. | L19: Wykonuje: `):`.
- **L20:** (w `get_prelab`) Zwraca: `container.prelab.get_prelab_public(conversation_id)`.
- **L23:** Dekorator `@router.post("/conversations/{conversation_id}/prelab")` (np. route FastAPI, fixture, dataclass).
- **L24–L28:** (w `submit_prelab`) Wyrażenie wieloliniowe — L24: Definicja funkcji/metody `?`. | L25: Element listy/argumentów: `conversation_id: str,`. | L26: Element listy/argumentów: `payload: PreLabSubmitRequest,`. | L27: Przypisanie `container: AppContainer` ← `Depends(get_container),`. | L28: Wykonuje: `):`.
- **L29:** (w `submit_prelab`) Zwraca: `container.prelab.submit_prelab(conversation_id, payload)`.
- **L32–L35:** Wyrażenie wieloliniowe — L32: Dekorator `@router.post(` (np. route FastAPI, fixture, dataclass). | L33: Element listy/argumentów: `"/conversations/{conversation_id}/prelab/generate",`. | L34: Przypisanie `tags` ← `["experimental"],`. | L35: Zamknięcie wyrażenia (`)`).
- **L36–L39:** (w `generate_prelab`) Wyrażenie wieloliniowe — L36: Definicja funkcji/metody `?`. | L37: Element listy/argumentów: `conversation_id: str,`. | L38: Przypisanie `container: AppContainer` ← `Depends(get_container),`. | L39: Wykonuje: `):`.
- **L40:** (w `generate_prelab`) Blok `try` — chroniony kod, potem except/finally.
- **L41:** (w `generate_prelab`) Zwraca: `await container.prelab.generate_prelab(conversation_id)`.
- **L42:** (w `generate_prelab`) Przechwytuje wyjątek `UnknownConversation`.
- **L43:** (w `generate_prelab`) Wykonuje: `raise`.
- **L44:** (w `generate_prelab`) Przechwytuje wyjątek `Exception as e`.
- **L45:** (w `generate_prelab`) Rzuca wyjątek: `HTTPException(status_code=500, detail=str(e)) from e`.

<a id="app-api-routers-messages-py"></a>
## `app/api/routers/messages.py`
Endpointy wiadomości: lista, send, stream, regenerate, feedback.

Liczba linii: **145**.

### Opis linia-po-linii

- **L1:** Docstring: Chat message routes (sync, stream, regenerate, feedback).
- **L3–L3:** Importy — L3: `from __future__ import annotations`.
- **L5–L5:** Importy — L5: `import uuid`.
- **L7–L8:** Importy — L7: `from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request`; L8: `from fastapi.responses import StreamingResponse`.
- **L10–L21:** Importy — L10: `from app.adapters.webhooks import send_telemetry_webhook`; L11: `from app.api.deps import get_container, validate_message_request`; L12: `from app.api.guards import require_conversation`; L13: `from app.api.middleware import request_id_var`; L14: `from app.api.schemas.requests import FeedbackRequest, MessageRequest`; L15: `from app.api.schemas.responses import MessageResponse`; L16: `from app.application.container import AppContainer`; L17: `from app.domain.exceptions import (`; L18: `PrelabRequired,`; L19: `TokenBudgetExceeded,`; L20: `UnknownConversation,`; L21: `)`.
- **L23:** Przypisanie `router` ← `APIRouter(tags=["messages"])`.
- **L26:** Definicja asynchronicznej funkcji/metody `_webhook`, zwraca `None`.
- **L27–L29:** (w `_webhook`) Wyrażenie wieloliniowe — L27: Oczekuje na coroutine: `send_telemetry_webhook(`. | L28: Przypisanie `payload, url, request_id` ← `request_id_var.get("-")`. | L29: Zamknięcie wyrażenia (`)`).
- **L32:** Dekorator `@router.get("/conversations/{conversation_id}/messages")` (np. route FastAPI, fixture, dataclass).
- **L33–L36:** (w `list_messages`) Wyrażenie wieloliniowe — L33: Definicja funkcji/metody `?`. | L34: Element listy/argumentów: `conversation_id: str,`. | L35: Przypisanie `container: AppContainer` ← `Depends(get_container),`. | L36: Wykonuje: `):`.
- **L37:** (w `list_messages`) Zwraca: `container.sessions.get_message_history(conversation_id)`.
- **L40–L43:** Wyrażenie wieloliniowe — L40: Dekorator `@router.post(` (np. route FastAPI, fixture, dataclass). | L41: Element listy/argumentów: `"/conversations/{conversation_id}/messages",`. | L42: Przypisanie `response_model` ← `MessageResponse,`. | L43: Zamknięcie wyrażenia (`)`).
- **L44–L50:** (w `send_message`) Wyrażenie wieloliniowe — L44: Definicja funkcji/metody `?`. | L45: Element listy/argumentów: `conversation_id: str,`. | L46: Element listy/argumentów: `request: MessageRequest,`. | L47: Element listy/argumentów: `background_tasks: BackgroundTasks,`. | L48: Element listy/argumentów: `http_request: Request,`. | L49: Przypisanie `container: AppContainer` ← `Depends(get_container),`. | L50: Wykonuje: `):`.
- **L51–L53:** (w `send_message`) Wyrażenie wieloliniowe — L51: Przypisanie `_, error_response` ← `await validate_message_request(`. | L52: Wykonuje: `conversation_id, request, http_request, background_tasks, container`. | L53: Zamknięcie wyrażenia (`)`).
- **L54:** (w `send_message`) Warunek `if` — gdy `error_response`.
- **L55:** (w `send_message`) Zwraca: `error_response`.
- **L57:** (w `send_message`) Blok `try` — chroniony kod, potem except/finally.
- **L58:** (w `send_message`) Przypisanie `result` ← `await container.chat.send_message(conversation_id, request)`.
- **L59–L70:** (w `send_message`) Wyrażenie wieloliniowe — L59: Wykonuje: `background_tasks.add_task(`. | L60: Element listy/argumentów: `_webhook,`. | L61: Wykonuje: `{`. | L62: Element listy/argumentów: `"event": "message",`. | L63: Element listy/argumentów: `"conversation_id": conversation_id,`. | L64: Element listy/argumentów: `"message_id": result["message_id"],`. | L65: Element listy/argumentów: `"prompt_score": result["prompt_score"],`. | L66: Element listy/argumentów: `"tokens_used": result["tokens_used"],`. | L67: Element listy/argumentów: `"is_cached": result["is_cached"],`. | L68: Element listy/argumentów: `"penalty_applied": result.get("penalty_applied", False),`. | L69: Element listy/argumentów: `},`. | L70: Zamknięcie wyrażenia (`)`).
- **L71:** (w `send_message`) Zwraca: `MessageResponse(**result)`.
- **L72:** (w `send_message`) Przechwytuje wyjątek `(UnknownConversation, PrelabRequired, TokenBudgetExceeded)`.
- **L73:** (w `send_message`) Wykonuje: `raise`.
- **L74:** (w `send_message`) Przechwytuje wyjątek `Exception as e`.
- **L75:** (w `send_message`) Rzuca wyjątek: `HTTPException(status_code=500, detail=str(e)) from e`.
- **L78:** Dekorator `@router.post("/conversations/{conversation_id}/messages/stream")` (np. route FastAPI, fixture, dataclass).
- **L79–L85:** (w `send_message_stream`) Wyrażenie wieloliniowe — L79: Definicja funkcji/metody `?`. | L80: Element listy/argumentów: `conversation_id: str,`. | L81: Element listy/argumentów: `request: MessageRequest,`. | L82: Element listy/argumentów: `background_tasks: BackgroundTasks,`. | L83: Element listy/argumentów: `http_request: Request,`. | L84: Przypisanie `container: AppContainer` ← `Depends(get_container),`. | L85: Wykonuje: `):`.
- **L86–L88:** (w `send_message_stream`) Wyrażenie wieloliniowe — L86: Przypisanie `_, error_response` ← `await validate_message_request(`. | L87: Wykonuje: `conversation_id, request, http_request, background_tasks, container`. | L88: Zamknięcie wyrażenia (`)`).
- **L89:** (w `send_message_stream`) Warunek `if` — gdy `error_response`.
- **L90:** (w `send_message_stream`) Zwraca: `error_response`.
- **L92:** (w `send_message_stream`) Przypisanie `msg_id` ← `str(uuid.uuid4())`.
- **L93–L97:** (w `send_message_stream`) Wyrażenie wieloliniowe — L93: Zwraca: `StreamingResponse(`. | L94: Element listy/argumentów: `container.stream.stream_message(conversation_id, request, msg_id),`. | L95: Przypisanie `media_type` ← `"application/x-ndjson",`. | L96: Przypisanie `headers` ← `{"X-Message-Id": msg_id},`. | L97: Zamknięcie wyrażenia (`)`).
- **L100–L104:** Wyrażenie wieloliniowe — L100: Dekorator `@router.post(` (np. route FastAPI, fixture, dataclass). | L101: Element listy/argumentów: `"/conversations/{conversation_id}/messages/{message_id}/regenerate",`. | L102: Przypisanie `response_model` ← `MessageResponse,`. | L103: Przypisanie `tags` ← `["experimental"],`. | L104: Zamknięcie wyrażenia (`)`).
- **L105–L109:** (w `regenerate_message`) Wyrażenie wieloliniowe — L105: Definicja funkcji/metody `?`. | L106: Element listy/argumentów: `conversation_id: str,`. | L107: Element listy/argumentów: `message_id: str,`. | L108: Przypisanie `container: AppContainer` ← `Depends(get_container),`. | L109: Wykonuje: `):`.
- **L110:** (w `regenerate_message`) Blok `try` — chroniony kod, potem except/finally.
- **L111–L113:** (w `regenerate_message`) Wyrażenie wieloliniowe — L111: Przypisanie `result` ← `await container.chat.regenerate_message(`. | L112: Wykonuje: `conversation_id, message_id`. | L113: Zamknięcie wyrażenia (`)`).
- **L114:** (w `regenerate_message`) Zwraca: `MessageResponse(**result)`.
- **L115:** (w `regenerate_message`) Przechwytuje wyjątek `KeyError as e`.
- **L116:** (w `regenerate_message`) Rzuca wyjątek: `HTTPException(status_code=404, detail=str(e)) from e`.
- **L117:** (w `regenerate_message`) Przechwytuje wyjątek `(UnknownConversation, PrelabRequired, TokenBudgetExceeded)`.
- **L118:** (w `regenerate_message`) Wykonuje: `raise`.
- **L119:** (w `regenerate_message`) Przechwytuje wyjątek `Exception as e`.
- **L120:** (w `regenerate_message`) Rzuca wyjątek: `HTTPException(status_code=500, detail=str(e)) from e`.
- **L123–L125:** Wyrażenie wieloliniowe — L123: Dekorator `@router.post(` (np. route FastAPI, fixture, dataclass). | L124: Wykonuje: `"/conversations/{conversation_id}/messages/{message_id}/feedback"`. | L125: Zamknięcie wyrażenia (`)`).
- **L126–L131:** (w `rate_message`) Wyrażenie wieloliniowe — L126: Definicja funkcji/metody `?`. | L127: Element listy/argumentów: `conversation_id: str,`. | L128: Element listy/argumentów: `message_id: str,`. | L129: Element listy/argumentów: `feedback: FeedbackRequest,`. | L130: Przypisanie `container: AppContainer` ← `Depends(get_container),`. | L131: Wykonuje: `):`.
- **L132:** (w `rate_message`) Przypisanie `conversation` ← `require_conversation(container, conversation_id)`.
- **L133–L136:** (w `rate_message`) Wyrażenie wieloliniowe — L133: Przypisanie `target_msg` ← `next(`. | L134: Przypisanie `(m for m in conversation.messages if m.get("message_id")` ← `= message_id),`. | L135: Element listy/argumentów: `None,`. | L136: Zamknięcie wyrażenia (`)`).
- **L137:** (w `rate_message`) Warunek `if` — gdy `not target_msg`.
- **L138:** (w `rate_message`) Rzuca wyjątek: `HTTPException(status_code=404, detail="Message not found")`.
- **L140–L143:** (w `rate_message`) Wyrażenie wieloliniowe — L140: Przypisanie `target_msg["student_feedback"]` ← `{`. | L141: Element listy/argumentów: `"rating": feedback.rating,`. | L142: Element listy/argumentów: `"comment": feedback.comment,`. | L143: Zamknięcie wyrażenia (`}`).
- **L144:** (w `rate_message`) Wykonuje: `conversation.touch()`.
- **L145:** (w `rate_message`) Zwraca: `{"status": "success", "message_id": message_id}`.

<a id="app-api-routers-conversations-py"></a>
## `app/api/routers/conversations.py`
Lifecycle konwersacji: start, state, export, events, summary, reveal, review, goals.

Liczba linii: **214**.

### Opis linia-po-linii

- **L1:** Docstring: Conversation lifecycle and session contract routes.
- **L3–L3:** Importy — L3: `from __future__ import annotations`.
- **L5–L5:** Importy — L5: `from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException`.
- **L7–L23:** Importy — L7: `from app.adapters.webhooks import send_telemetry_webhook`; L8: `from app.api.deps import get_container`; L9: `from app.api.middleware import request_id_var`; L10: `from app.api.schemas.requests import (`; L11: `IdeEventRequest,`; L12: `RevealHintRequest,`; L13: `ReviewRequest,`; L14: `StartRequest,`; L15: `)`; L16: `from app.application.container import AppContainer`; L17: `from app.core.config import SUMMARY_WEBHOOK_URL`; L18: `from app.core.metrics import metrics`; L19: `from app.domain.exceptions import (`; L20: `PrelabRequired,`; L21: `RevealNotAllowed,`; L22: `UnknownConversation,`; L23: `)`.
- **L25:** Przypisanie `router` ← `APIRouter(tags=["conversations"])`.
- **L28:** Definicja asynchronicznej funkcji/metody `_webhook`, zwraca `None`.
- **L29–L31:** (w `_webhook`) Wyrażenie wieloliniowe — L29: Oczekuje na coroutine: `send_telemetry_webhook(`. | L30: Przypisanie `payload, url, request_id` ← `request_id_var.get("-")`. | L31: Zamknięcie wyrażenia (`)`).
- **L34:** Dekorator `@router.post("/conversations")` (np. route FastAPI, fixture, dataclass).
- **L35–L39:** (w `start_conversation`) Wyrażenie wieloliniowe — L35: Definicja funkcji/metody `?`. | L36: Element listy/argumentów: `request: StartRequest,`. | L37: Element listy/argumentów: `background_tasks: BackgroundTasks,`. | L38: Przypisanie `container: AppContainer` ← `Depends(get_container),`. | L39: Wykonuje: `):`.
- **L40:** (w `start_conversation`) Wykonuje: `metrics.inc("requests_total")`.
- **L41–L43:** (w `start_conversation`) Wyrażenie wieloliniowe — L41: Przypisanie `conv_id` ← `container.sessions.start_conversation(`. | L42: Wykonuje: `request.problem_description, request.config`. | L43: Zamknięcie wyrażenia (`)`).
- **L45:** (w `start_conversation`) Warunek `if` — gdy `request.config.learningContext.referenceMaterials`.
- **L46–L50:** (w `start_conversation`) Wyrażenie wieloliniowe — L46: Wykonuje: `background_tasks.add_task(`. | L47: Element listy/argumentów: `container.rag.load_materials,`. | L48: Element listy/argumentów: `conv_id,`. | L49: Element listy/argumentów: `request.config.learningContext.referenceMaterials,`. | L50: Zamknięcie wyrażenia (`)`).
- **L52–L62:** (w `start_conversation`) Wyrażenie wieloliniowe — L52: Zwraca: `{`. | L53: Element listy/argumentów: `"conversation_id": conv_id,`. | L54: Wykonuje: `"prelab_required": bool(`. | L55: Wykonuje: `request.config.preLab and request.config.preLab.enabled`. | L56: Element listy/argumentów: `),`. | L57: Wykonuje: `"ideRestrictions": (`. | L58: Wykonuje: `request.config.ideRestrictions.model_dump()`. | L59: Warunek `if` — gdy `request.config.ideRestrictions`. | L60: Wykonuje: `else None`. | L61: Element listy/argumentów: `),`. | L62: Zamknięcie wyrażenia (`}`).
- **L65:** Dekorator `@router.get("/conversations/{conversation_id}")` (np. route FastAPI, fixture, dataclass).
- **L66–L69:** (w `get_conversation`) Wyrażenie wieloliniowe — L66: Definicja funkcji/metody `?`. | L67: Element listy/argumentów: `conversation_id: str,`. | L68: Przypisanie `container: AppContainer` ← `Depends(get_container),`. | L69: Wykonuje: `):`.
- **L70:** (w `get_conversation`) Zwraca: `container.sessions.get_session_state(conversation_id)`.
- **L73:** Dekorator `@router.get("/conversations/{conversation_id}/restrictions")` (np. route FastAPI, fixture, dataclass).
- **L74–L77:** (w `get_restrictions`) Wyrażenie wieloliniowe — L74: Definicja funkcji/metody `?`. | L75: Element listy/argumentów: `conversation_id: str,`. | L76: Przypisanie `container: AppContainer` ← `Depends(get_container),`. | L77: Wykonuje: `):`.
- **L78:** (w `get_restrictions`) Zwraca: `container.sessions.get_restrictions(conversation_id)`.
- **L81:** Dekorator `@router.get("/conversations/{conversation_id}/export")` (np. route FastAPI, fixture, dataclass).
- **L82–L85:** (w `export_conversation`) Wyrażenie wieloliniowe — L82: Definicja funkcji/metody `?`. | L83: Element listy/argumentów: `conversation_id: str,`. | L84: Przypisanie `container: AppContainer` ← `Depends(get_container),`. | L85: Wykonuje: `):`.
- **L86:** (w `export_conversation`) Zwraca: `container.sessions.export_conversation(conversation_id)`.
- **L89:** Dekorator `@router.get("/conversations/{conversation_id}/checkpoints")` (np. route FastAPI, fixture, dataclass).
- **L90–L93:** (w `get_checkpoints`) Wyrażenie wieloliniowe — L90: Definicja funkcji/metody `?`. | L91: Element listy/argumentów: `conversation_id: str,`. | L92: Przypisanie `container: AppContainer` ← `Depends(get_container),`. | L93: Wykonuje: `):`.
- **L94:** (w `get_checkpoints`) Zwraca: `container.sessions.get_checkpoints(conversation_id)`.
- **L97–L100:** Wyrażenie wieloliniowe — L97: Dekorator `@router.post(` (np. route FastAPI, fixture, dataclass). | L98: Element listy/argumentów: `"/conversations/{conversation_id}/goals/assess",`. | L99: Przypisanie `tags` ← `["experimental"],`. | L100: Zamknięcie wyrażenia (`)`).
- **L101–L104:** (w `assess_goals`) Wyrażenie wieloliniowe — L101: Definicja funkcji/metody `?`. | L102: Element listy/argumentów: `conversation_id: str,`. | L103: Przypisanie `container: AppContainer` ← `Depends(get_container),`. | L104: Wykonuje: `):`.
- **L105:** (w `assess_goals`) Blok `try` — chroniony kod, potem except/finally.
- **L106:** (w `assess_goals`) Zwraca: `await container.goals.assess_goals(conversation_id)`.
- **L107:** (w `assess_goals`) Przechwytuje wyjątek `UnknownConversation`.
- **L108:** (w `assess_goals`) Wykonuje: `raise`.
- **L109:** (w `assess_goals`) Przechwytuje wyjątek `Exception as e`.
- **L110:** (w `assess_goals`) Rzuca wyjątek: `HTTPException(status_code=500, detail=str(e)) from e`.
- **L113–L116:** Wyrażenie wieloliniowe — L113: Dekorator `@router.post(` (np. route FastAPI, fixture, dataclass). | L114: Element listy/argumentów: `"/conversations/{conversation_id}/review",`. | L115: Przypisanie `tags` ← `["experimental"],`. | L116: Zamknięcie wyrażenia (`)`).
- **L117–L121:** (w `review_code`) Wyrażenie wieloliniowe — L117: Definicja funkcji/metody `?`. | L118: Element listy/argumentów: `conversation_id: str,`. | L119: Element listy/argumentów: `payload: ReviewRequest,`. | L120: Przypisanie `container: AppContainer` ← `Depends(get_container),`. | L121: Wykonuje: `):`.
- **L122:** (w `review_code`) Blok `try` — chroniony kod, potem except/finally.
- **L123:** (w `review_code`) Zwraca: `await container.review.review_code(conversation_id, payload)`.
- **L124:** (w `review_code`) Przechwytuje wyjątek `(UnknownConversation, PrelabRequired)`.
- **L125:** (w `review_code`) Wykonuje: `raise`.
- **L126:** (w `review_code`) Przechwytuje wyjątek `Exception as e`.
- **L127:** (w `review_code`) Rzuca wyjątek: `HTTPException(status_code=500, detail=str(e)) from e`.
- **L130:** Dekorator `@router.post("/conversations/{conversation_id}/events")` (np. route FastAPI, fixture, dataclass).
- **L131–L136:** (w `post_ide_event`) Wyrażenie wieloliniowe — L131: Definicja funkcji/metody `?`. | L132: Element listy/argumentów: `conversation_id: str,`. | L133: Element listy/argumentów: `payload: IdeEventRequest,`. | L134: Element listy/argumentów: `background_tasks: BackgroundTasks,`. | L135: Przypisanie `container: AppContainer` ← `Depends(get_container),`. | L136: Wykonuje: `):`.
- **L137:** (w `post_ide_event`) Przypisanie `result` ← `container.sessions.record_ide_event(conversation_id, payload)`.
- **L138–L145:** (w `post_ide_event`) Wyrażenie wieloliniowe — L138: Wykonuje: `background_tasks.add_task(`. | L139: Element listy/argumentów: `_webhook,`. | L140: Wykonuje: `{`. | L141: Element listy/argumentów: `"event": "ide_event",`. | L142: Element listy/argumentów: `"conversation_id": conversation_id,`. | L143: Element listy/argumentów: `**result["event"],`. | L144: Element listy/argumentów: `},`. | L145: Zamknięcie wyrażenia (`)`).
- **L146:** (w `post_ide_event`) Zwraca: `result`.
- **L149:** Dekorator `@router.delete("/conversations/{conversation_id}")` (np. route FastAPI, fixture, dataclass).
- **L150–L154:** (w `delete_conversation`) Wyrażenie wieloliniowe — L150: Definicja funkcji/metody `?`. | L151: Element listy/argumentów: `conversation_id: str,`. | L152: Element listy/argumentów: `background_tasks: BackgroundTasks,`. | L153: Przypisanie `container: AppContainer` ← `Depends(get_container),`. | L154: Wykonuje: `):`.
- **L155–L157:** (w `delete_conversation`) Wyrażenie wieloliniowe — L155: Przypisanie `result` ← `await container.sessions.delete_conversation(`. | L156: Przypisanie `conversation_id, soft_summary` ← `True`. | L157: Zamknięcie wyrażenia (`)`).
- **L158:** (w `delete_conversation`) Warunek `if` — gdy `result.get("summary")`.
- **L159–L168:** (w `delete_conversation`) Wyrażenie wieloliniowe — L159: Wykonuje: `background_tasks.add_task(`. | L160: Element listy/argumentów: `_webhook,`. | L161: Wykonuje: `{`. | L162: Element listy/argumentów: `"event": "session_summary",`. | L163: Element listy/argumentów: `"conversation_id": conversation_id,`. | L164: Element listy/argumentów: `"summary": result["summary"],`. | L165: Element listy/argumentów: `"soft_close": True,`. | L166: Element listy/argumentów: `},`. | L167: Element listy/argumentów: `SUMMARY_WEBHOOK_URL,`. | L168: Zamknięcie wyrażenia (`)`).
- **L169:** (w `delete_conversation`) Zwraca: `result`.
- **L172–L175:** Wyrażenie wieloliniowe — L172: Dekorator `@router.post(` (np. route FastAPI, fixture, dataclass). | L173: Element listy/argumentów: `"/conversations/{conversation_id}/hints/reveal",`. | L174: Przypisanie `tags` ← `["experimental"],`. | L175: Zamknięcie wyrażenia (`)`).
- **L176–L180:** (w `reveal_hint`) Wyrażenie wieloliniowe — L176: Definicja funkcji/metody `?`. | L177: Element listy/argumentów: `conversation_id: str,`. | L178: Element listy/argumentów: `payload: RevealHintRequest,`. | L179: Przypisanie `container: AppContainer` ← `Depends(get_container),`. | L180: Wykonuje: `):`.
- **L181:** (w `reveal_hint`) Blok `try` — chroniony kod, potem except/finally.
- **L182:** (w `reveal_hint`) Zwraca: `await container.chat.reveal_hint(conversation_id, payload)`.
- **L183:** (w `reveal_hint`) Przechwytuje wyjątek `(UnknownConversation, PrelabRequired, RevealNotAllowed)`.
- **L184:** (w `reveal_hint`) Wykonuje: `raise`.
- **L185:** (w `reveal_hint`) Przechwytuje wyjątek `Exception as e`.
- **L186:** (w `reveal_hint`) Rzuca wyjątek: `HTTPException(status_code=500, detail=str(e)) from e`.
- **L189:** Dekorator `@router.post("/conversations/{conversation_id}/summary")` (np. route FastAPI, fixture, dataclass).
- **L190–L194:** (w `get_summary`) Wyrażenie wieloliniowe — L190: Definicja funkcji/metody `?`. | L191: Element listy/argumentów: `conversation_id: str,`. | L192: Element listy/argumentów: `background_tasks: BackgroundTasks,`. | L193: Przypisanie `container: AppContainer` ← `Depends(get_container),`. | L194: Wykonuje: `):`.
- **L195:** (w `get_summary`) Przypisanie `summary` ← `await container.summary.generate_summary(conversation_id)`.
- **L196:** (w `get_summary`) Przypisanie `conversation` ← `container.conversations.get(conversation_id)`.
- **L197:** (w `get_summary`) Przypisanie `scores` ← `conversation.prompt_scores if conversation else []`.
- **L198–L202:** (w `get_summary`) Wyrażenie wieloliniowe — L198: Przypisanie `feedbacks` ← `[`. | L199: Wykonuje: `m["student_feedback"]`. | L200: Pętla `for` po `m in (conversation.messages if conversation else [])`. | L201: Warunek `if` — gdy `m.get("role") == "assistant" and "student_feedback" in m`. | L202: Zamknięcie wyrażenia (`]`).
- **L203–L213:** (w `get_summary`) Wyrażenie wieloliniowe — L203: Wykonuje: `background_tasks.add_task(`. | L204: Element listy/argumentów: `_webhook,`. | L205: Wykonuje: `{`. | L206: Element listy/argumentów: `"event": "session_summary",`. | L207: Element listy/argumentów: `"conversation_id": conversation_id,`. | L208: Element listy/argumentów: `"summary": summary,`. | L209: Element listy/argumentów: `"scores": scores,`. | L210: Element listy/argumentów: `"feedbacks": feedbacks,`. | L211: Element listy/argumentów: `},`. | L212: Element listy/argumentów: `SUMMARY_WEBHOOK_URL,`. | L213: Zamknięcie wyrażenia (`)`).
- **L214:** (w `get_summary`) Zwraca: `summary`.
