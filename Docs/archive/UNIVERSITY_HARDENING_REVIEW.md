# University Hardening Review

This document maps **where** campus-ready changes land, with **old** vs **new** snippets.

**Status:** Implemented in code (old paths left commented). Local `.env` stays auth-off + UI on for playground; `.env.example` shows production values.

**Topology assumed:** Student IDE → Spring → AI module (private network). Students never call AI directly.

---

## Priority legend

| P | Meaning |
|---|---|
| **P0** | Must fix before any student-facing pilot |
| **P1** | Fix before multi-lab / multi-instance |
| **P2** | Pedagogy / UX hardening (can follow pilot) |

---

## P0-1 — Turn auth on for deploy defaults

**Why:** With `AI_AUTH_ENABLED=false`, anyone who can reach the host can create sessions, chat, force hints, and delete labs.

**Files:** `app/core/config.py`, `.env.example`

### `app/core/config.py`

```diff
# OLD
AI_AUTH_ENABLED: bool = False
AI_JWT_SECRET: str = ""
CORS_ORIGINS: List[str] = ["*"]
TRUST_X_FORWARDED_FOR: bool = True

# NEW (safer defaults; local .env can still override for pure-dev)
AI_AUTH_ENABLED: bool = True
AI_JWT_SECRET: str = ""  # require non-empty when auth enabled (see auth.py)
CORS_ORIGINS: List[str] = []  # empty = deny browser origins; Spring is server-side
TRUST_X_FORWARDED_FOR: bool = False  # only True behind a trusted reverse proxy
AI_JWT_AUDIENCE: Optional[str] = "pja-sensei-ai"
AI_JWT_ISSUER: Optional[str] = "pja-spring"
AI_EXPOSE_DOCS: bool = False
AI_EXPOSE_UI: bool = False
AI_PROFESSOR_ROLES: List[str] = ["professor", "admin"]
```

### `.env.example`

```diff
# OLD
AI_AUTH_ENABLED=false
AI_JWT_SECRET=supersecret-dev-key-at-least-32b
CORS_ORIGINS=["*"]
TRUST_X_FORWARDED_FOR=true

# NEW
# Local playground only — production/staging must keep auth on.
AI_AUTH_ENABLED=true
AI_JWT_SECRET=CHANGE_ME_shared_with_spring_min_32_chars
AI_JWT_AUDIENCE=pja-sensei-ai
AI_JWT_ISSUER=pja-spring
CORS_ORIGINS=["https://labs.pja.edu.pl"]
TRUST_X_FORWARDED_FOR=false
AI_EXPOSE_DOCS=false
AI_EXPOSE_UI=false
```

**Verify:** Spring and AI share the same HS256 secret; Spring puts `exp`, `sub` (studentId), optional `role`, `labId` in the token.

---

## P0-2 — Tighten JWT verification (iss / aud / role claims)

**Why:** Today we only require `exp`. A stolen/forged token shape with the shared secret is enough; no audience binding to this service.

**File:** `app/api/auth.py` (~lines 19–41)

### OLD

```python
claims = jwt.decode(
    token,
    secret,
    algorithms=["HS256"],
    options={"require": ["exp"]},
)
```

### NEW (proposal)

```python
decode_kwargs = {
    "algorithms": ["HS256"],
    "options": {"require": ["exp", "sub"]},
}
if settings.AI_JWT_AUDIENCE:
    decode_kwargs["audience"] = settings.AI_JWT_AUDIENCE
if settings.AI_JWT_ISSUER:
    decode_kwargs["issuer"] = settings.AI_JWT_ISSUER

claims = jwt.decode(token, secret, **decode_kwargs)
```

Optional helper for professor routes:

```python
def require_professor(claims: Optional[Dict[str, Any]]) -> bool:
    if not claims:
        return False
    role = str(claims.get("role") or claims.get("roles") or "").lower()
    if role in {r.lower() for r in settings.AI_PROFESSOR_ROLES}:
        return True
    roles = claims.get("roles")
    if isinstance(roles, list):
        allowed = {r.lower() for r in settings.AI_PROFESSOR_ROLES}
        return any(str(r).lower() in allowed for r in roles)
    return False
```

---

## P0-3 — Role-guard `POST .../hints/force`

**Why:** Highest student exploit today. Endpoint is documented as professor override but has **no role check**. With auth off (or a normal student JWT), streak / pedagogy gates are bypassed.

**File:** `app/api/routers/conversations.py` (~lines 213–221)

### OLD

```python
@router.post("/{conv_id}/hints/force", response_model=HintRevealResponse)
def force_hint(
    conv_id: str,
    req: Optional[ForceHintRequest] = None,
    chat_svc: ChatService = Depends(get_chat_service),
):
    """Professor override: unlock next hint without frustration streak."""
    reason = req.reason if req is not None else "professor_override"
    return chat_svc.force_reveal_hint(conv_id, reason=reason)
```

### NEW (proposal)

```python
from fastapi import Request, HTTPException
from app.api.auth import require_professor  # proposed helper

@router.post("/{conv_id}/hints/force", response_model=HintRevealResponse)
def force_hint(
    conv_id: str,
    request: Request,
    req: Optional[ForceHintRequest] = None,
    chat_svc: ChatService = Depends(get_chat_service),
):
    """Professor override: unlock next hint without frustration streak."""
    claims = getattr(request.state, "jwt_claims", None)
    # When AI_AUTH_ENABLED=false (local only), skip; when true, require professor.
    if settings.AI_AUTH_ENABLED and not require_professor(claims):
        raise HTTPException(
            status_code=403,
            detail={
                "message_id": "forbidden",
                "detail": "Professor role required for force-hint.",
            },
        )
    reason = req.reason if req is not None else "professor_override"
    return chat_svc.force_reveal_hint(conv_id, reason=reason)
```

**Also consider the same guard for:** soft-delete / purge-style session admin if exposed, and any future “inject solution” APIs.

**Verify:** Student JWT → `403`; professor JWT (`role=professor|admin`) → `200`; webhook audit still emits `force_hint`.

---

## P0-4 — Shrink JWT auth bypass list

**Why:** Even with `AI_AUTH_ENABLED=true`, these stay public today:

```text
/health, /health_check, /metrics, /webhooks, /docs, /redoc, /openapi.json, /scenarios, /
```

Lab tester UI + metrics + recent webhook payloads must not be campus-Wi‑Fi reachable without auth.

**File:** `app/api/middleware.py` (~lines 15–27)

### OLD

```python
_AUTH_OPEN_PREFIXES = (
    "/health",
    "/health_check",
    "/metrics",
    "/webhooks",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/scenarios",
)

_AUTH_OPEN_EXACT = {"/", "/favicon.ico"}
```

### NEW (proposal)

```python
# Always public (load balancer / k8s probes only).
_AUTH_OPEN_PREFIXES = (
    "/health",
    "/health_check",
)

_AUTH_OPEN_EXACT = {"/favicon.ico"}

# Conditionally public when AI_EXPOSE_UI / AI_EXPOSE_DOCS (dev only).
# Build the tuples from settings at import or inside _is_auth_open_path.
```

Inside `_is_auth_open_path`:

```python
def _is_auth_open_path(path: str) -> bool:
    if path in _AUTH_OPEN_EXACT:
        return True
    if any(path == p or path.startswith(p + "/") for p in _AUTH_OPEN_PREFIXES):
        return True
    if settings.AI_EXPOSE_UI and (path == "/" or path.startswith("/scenarios")):
        return True
    if settings.AI_EXPOSE_DOCS and path in {
        "/docs", "/redoc", "/openapi.json",
    }:
        return True
    # /metrics and /webhooks/recent: require JWT (or separate admin token)
    return False
```

---

## P0-5 — Gate or disable UI + OpenAPI in production

**Why:** `static/index.html` and `static/scenarios.html` are full API clients. OpenAPI is a free attack map.

**File:** `app/main.py` (~lines 45–77)

### OLD

```python
def create_app() -> FastAPI:
    app = FastAPI(
        title="PJA-Sensei AI Module",
        version="0.1.0",
        lifespan=lifespan
    )
    # ...
    app.include_router(ui.router)
    app.include_router(health.router)
    app.include_router(config.router)
    app.include_router(conversations.router)
```

### NEW (proposal)

```python
def create_app() -> FastAPI:
    app = FastAPI(
        title="PJA-Sensei AI Module",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.AI_EXPOSE_DOCS else None,
        redoc_url="/redoc" if settings.AI_EXPOSE_DOCS else None,
        openapi_url="/openapi.json" if settings.AI_EXPOSE_DOCS else None,
    )
    # ...
    if settings.AI_EXPOSE_UI:
        app.include_router(ui.router)
    app.include_router(health.router)
    app.include_router(config.router)
    app.include_router(conversations.router)
```

**File:** `app/api/routers/health.py` — optionally protect metrics:

### OLD

```python
@router.get("/metrics")
def metrics_json():
    ...

@router.get("/webhooks/recent")
def recent_webhooks(limit: int = 20):
    ...
```

### NEW (proposal)

Same handlers, but require JWT (remove from open list) **or** check `require_professor(request.state.jwt_claims)` and return `403` otherwise. Prefer: Spring scrapes Prometheus; students never see `/webhooks/recent` (contains event payloads).

---

## P0-6 — CORS + forwarded-for (deploy hygiene)

**File:** `app/main.py` (~lines 57–63)

### OLD

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### NEW (proposal)

```python
# If Spring is the only caller (server-to-server), CORS is mostly irrelevant.
# If a browser ever talks to AI, pin origins and never use "*"+credentials.
origins = settings.CORS_ORIGINS or []
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=bool(origins) and origins != ["*"],
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-Id"],
)
```

**File:** `app/api/auth.py` (`client_ip_from_request`) — behavior stays the same; **change the default** of `TRUST_X_FORWARDED_FOR` to `False` (see P0-1). Behind nginx/Traefik set `true` and ensure only the proxy can set `X-Forwarded-For`.

---

## P1-1 — Session ownership binding

**Why:** Even with JWT, today any valid token can hit `/conversations/{any_id}/messages` if the id is known/guessed. No `sub` ↔ session owner check.

**Files:** `app/domain/conversation.py`, `app/application/session_service.py`, `app/api/routers/conversations.py`

### Domain (proposal)

```python
# Conversation fields to add
owner_sub: Optional[str] = None   # JWT "sub" (student id)
lab_id: Optional[str] = None
```

### On session create (proposal)

```python
claims = getattr(request.state, "jwt_claims", None) or {}
conv.owner_sub = claims.get("sub")
conv.lab_id = claims.get("labId") or claims.get("lab_id")
```

### On every mutating/read route (proposal)

```python
def assert_owns(conv: Conversation, request: Request) -> None:
    if not settings.AI_AUTH_ENABLED:
        return
    claims = getattr(request.state, "jwt_claims", None) or {}
    if require_professor(claims):
        return
    if not conv.owner_sub or conv.owner_sub != claims.get("sub"):
        raise HTTPException(status_code=404, detail={"message_id": "unknown_conversation"})
        # 404 not 403 — avoid session-id enumeration
```

---

## P1-2 — Persistence decision (document only; no SQLite yet)

**Why:** `InMemoryConversationRepository` loses all labs on restart; two AI replicas do not share state.

**File today:** `app/infrastructure/conversations_memory.py` (wired in `conversations.py`)

| Option | Who owns history | AI role |
|---|---|---|
| **A (recommended for first semester)** | Spring/Postgres | Stateless tutor: Spring sends history/context each call or short-lived session |
| **B** | Shared Redis/Postgres behind `ConversationRepository` | AI owns session TTL; Spring only holds grades |

No code change until the team picks A or B. Do **not** re-add local SQLite if Spring already has the student DB.

---

## P2-1 — Prelab keyword matching (substring gaming)

**Why:** `kw in user_answer` matches substrings (`Rest` inside `Forest`).

**File:** `app/application/prelab_service.py` (~line 123)

### OLD

```python
has_match = any(str(kw).strip().lower() in user_answer for kw in expected)
```

### NEW (proposal)

```python
import re

def _keyword_hit(keyword: str, answer: str) -> bool:
    kw = keyword.strip().lower()
    if not kw:
        return False
    # Word-boundary match; escape regex metacharacters in keywords.
    return re.search(rf"\b{re.escape(kw)}\b", answer, flags=re.IGNORECASE) is not None

has_match = any(_keyword_hit(str(kw), user_answer) for kw in expected)
```

---

## P2-2 — Stronger giveaway / jailbreak path (optional)

**Why:** Regex security + optional LLM classifier is good for a pilot, not a guarantee under determined prompt injection.

**Files:** `app/application/security.py`, `app/application/pedagogy_gates.py`

**Proposal (conceptual, not full diff):**
- Always run security LLM when `SECURITY_MODEL` is up (not only on regex miss), still honor `SECURITY_FAIL_CLOSED`.
- Add university-specific denylist phrases in Polish/English for “full solution / paste entire class”.
- Log `blocked` events to webhook with `student sub` (no full prompt body in long-term storage).

---

## Suggested verification order (when you approve implementation)

1. Set `AI_AUTH_ENABLED=true` + shared secret with a test JWT from Spring.
2. Confirm student JWT cannot call `/hints/force` (403) and cannot read another student’s `conv_id` (404).
3. Confirm `/`, `/scenarios`, `/docs`, `/metrics`, `/webhooks/recent` are closed unless `AI_EXPOSE_*=true`.
4. Confirm health probes still work without JWT.
5. Load-test Ollama with N concurrent labs; confirm 429→fallback→503 path still returns client-safe errors.
6. Decide persistence Option A vs B before multi-instance deploy.

---

## Out of scope for this review

- Re-adding SQLite / choosing Redis.
- Changing Spring contracts beyond JWT claim names (`sub`, `role`, `aud`, `iss`, `labId`).
- UI redesign of `static/*` (keep as **dev-only** behind `AI_EXPOSE_UI`).

---

## Quick map: file → change

| File | Change |
|---|---|
| `app/core/config.py` | Safer defaults + new flags (`AI_EXPOSE_*`, JWT iss/aud, professor roles) |
| `.env.example` | Document production-safe values |
| `app/api/auth.py` | `aud`/`iss`/`sub`; `require_professor()` |
| `app/api/middleware.py` | Shrink open paths; gate UI/docs/metrics |
| `app/api/routers/conversations.py` | Force-hint role check; ownership assert |
| `app/api/routers/health.py` | Protect metrics / webhook recent |
| `app/main.py` | Conditional docs/UI routers; tighter CORS |
| `app/domain/conversation.py` | `owner_sub` / `lab_id` |
| `app/application/session_service.py` | Set owner on create |
| `app/application/prelab_service.py` | Word-boundary keywords |
| `app/application/security.py` | Optional stronger classifier policy |

After you mark which rows you want, we can implement them in a focused PR without touching the rest.
