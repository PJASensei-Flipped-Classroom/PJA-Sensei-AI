# Root i konfiguracja

Opisy linia-po-linii (język: polski). Puste linie pominięte w wypunktowaniu, ale nie zmieniają numeracji `L`.

<a id="readme-md"></a>
## `README.md`
Główna dokumentacja startowa repozytorium: layout, quick start, Docker, testy, powierzchnia API i flagi środowiskowe.

Liczba linii: **84**.

### Opis linia-po-linii

- **L1:** Nagłówek Markdown: `# PJA-Sensei AI Module`.
- **L3:** Treść Markdown: `FastAPI microservice: Socratic coding mentor for Flipped Classroom labs (OpenRouter + in-memory sessions + Ch…`.
- **L5:** Nagłówek Markdown: `## Layout`.
- **L7:** Fence bloku kodu Markdown.
- **L8:** Treść Markdown: `app/`.
- **L9:** Treść Markdown: `main.py # create_app() + lifespan`.
- **L10:** Treść Markdown: `api/ # routers, schemas, deps, middleware`.
- **L11:** Treść Markdown: `application/ # use-cases (chat, prelab, sessions, …)`.
- **L12:** Treść Markdown: `adapters/ # OpenRouter, Chroma, cache, webhooks`.
- **L13:** Treść Markdown: `domain/ # Conversation, SenseiConfig, exceptions`.
- **L14:** Treść Markdown: `core/ # settings, auth, metrics, rate limit`.
- **L15:** Treść Markdown: `static/ # tester UI`.
- **L16:** Treść Markdown: `tests/ # pytest + tests/live HTTP suite`.
- **L17:** Treść Markdown: `schemas/ # OpenAPI / SenseiConfig JSON Schema`.
- **L18:** Fence bloku kodu Markdown.
- **L20:** Nagłówek Markdown: `## Quick start`.
- **L22:** Fence bloku kodu Markdown.
- **L23:** Treść Markdown: `python -m venv .venv`.
- **L24:** Nagłówek Markdown: `# Windows`.
- **L25:** Treść Markdown: `.\.venv\Scripts\activate`.
- **L26:** Treść Markdown: `pip install -r requirements.txt`.
- **L27:** Treść Markdown: `copy .env.example .env # set OPENROUTER_API_KEY`.
- **L28:** Treść Markdown: `uvicorn app.main:app --reload --host 127.0.0.1 --port 8000`.
- **L29:** Fence bloku kodu Markdown.
- **L31:** Punkt listy: `- Tester UI: http://127.0.0.1:8000/`.
- **L32:** Punkt listy: `- Swagger: http://127.0.0.1:8000/docs`.
- **L33:** Punkt listy: `- Health: `GET /health``.
- **L34:** Punkt listy: `- Metrics: `GET /metrics` or `GET /metrics/prometheus``.
- **L36:** Nagłówek Markdown: `## Docker Compose`.
- **L38:** Fence bloku kodu Markdown.
- **L39:** Treść Markdown: `docker compose up --build`.
- **L40:** Fence bloku kodu Markdown.
- **L42:** Nagłówek Markdown: `## Tests`.
- **L44:** Treść Markdown: `Offline (ASGI + unit, no OpenRouter): gates, auth JWT, rate limit, pre-lab, token budget,`.
- **L45:** Treść Markdown: `idempotency, file-context, cache TTL, `SECURITY_FAIL_CLOSED`, stream extract, code penalty.`.
- **L47:** Treść Markdown: `Live HTTP (needs `uvicorn` on `:8000` + LLM key): scenarios **S1–S24** in `tests/live/test_memory.py``.
- **L48:** Treść Markdown: `(theory, RAG, injection, cache, stream, memory, pre-lab, review, reveal, budget, file-context, 404, …).`.
- **L50:** Fence bloku kodu Markdown.
- **L51:** Nagłówek Markdown: `# Full evaluation: offline pytest, then live S1–S24 if API is up (else SKIP live)`.
- **L52:** Treść Markdown: `.\.venv\Scripts\python.exe -m tests.live.test_all`.
- **L54:** Nagłówek Markdown: `# Offline only`.
- **L55:** Treść Markdown: `.\.venv\Scripts\python.exe -m pytest -q`.
- **L56:** Treść Markdown: `.\.venv\Scripts\python.exe -m tests.live.test_all --offline-only`.
- **L58:** Nagłówek Markdown: `# Live subset / require live`.
- **L59:** Treść Markdown: `.\.venv\Scripts\python.exe -m tests.live.test_all --only 23,24`.
- **L60:** Treść Markdown: `.\.venv\Scripts\python.exe -m tests.live.test_memory --only 3,6,22`.
- **L61:** Treść Markdown: `.\.venv\Scripts\python.exe -m tests.live.test_all --require-live`.
- **L62:** Fence bloku kodu Markdown.
- **L64:** Nagłówek Markdown: `## API surface`.
- **L66:** Treść Markdown: `**Happy-path (VS Code / lab):** start conversation → optional pre-lab → messages / stream → events → export o…`.
- **L68:** Treść Markdown: `**Experimental** (tagged in OpenAPI): `/review`, `/hints/reveal`, `/goals/assess`, message regenerate, `/prel…`.
- **L70:** Nagłówek Markdown: `## Notable env flags`.
- **L72:** Wiersz tabeli: `| Variable | Default | Meaning |`.
- **L73:** Wiersz tabeli: `|----------|---------|---------|`.
- **L74:** Wiersz tabeli: `| `AI_AUTH_ENABLED` | `false` | Require Bearer JWT |`.
- **L75:** Wiersz tabeli: `| `SECURITY_FAIL_CLOSED` | `false` | Block chat if security LLM fails |`.
- **L76:** Wiersz tabeli: `| `RATE_LIMIT_PER_MINUTE` | `30` | Sliding window on protected routes |`.
- **L77:** Wiersz tabeli: `| `MAX_CONVERSATIONS` / `CONVERSATION_TTL_SECONDS` | `200` / `7200` | In-memory session limits |`.
- **L79:** Treść Markdown: `See [docs/openapi-examples.md](docs/openapi-examples.md) for sample payloads.`.
- **L81:** Nagłówek Markdown: `## Documentation`.
- **L83:** Punkt listy: `- [docs/FILE_CATALOG.md](docs/FILE_CATALOG.md) — role of every project file`.
- **L84:** Punkt listy: `- [docs/openapi-examples.md](docs/openapi-examples.md) — request/response examples`.

<a id="requirements-txt"></a>
## `requirements.txt`
Lista zależności Pythona (minimalne wersje) instalowanych przez pip / Docker.

Liczba linii: **19**.

### Opis linia-po-linii

- **L1:** Sekcja komentarza: Core API Framework
- **L2:** Zależność pip: `fastapi>=0.109.0`.
- **L3:** Zależność pip: `uvicorn[standard]>=0.27.0`.
- **L5:** Sekcja komentarza: AI & Data Validation
- **L6:** Zależność pip: `openai>=1.12.0`.
- **L7:** Zależność pip: `pydantic>=2.6.0`.
- **L8:** Zależność pip: `pydantic-settings>=2.2.0`.
- **L9:** Zależność pip: `python-dotenv>=1.0.1`.
- **L10:** Zależność pip: `PyJWT>=2.8.0`.
- **L12:** Sekcja komentarza: HTTP, RAG, HTML parsing
- **L13:** Zależność pip: `httpx>=0.27.0`.
- **L14:** Zależność pip: `chromadb>=0.4.22`.
- **L15:** Zależność pip: `beautifulsoup4>=4.12.0`.
- **L16:** Zależność pip: `jsonschema>=4.21.0`.
- **L18:** Sekcja komentarza: Tests
- **L19:** Zależność pip: `pytest>=8.0.0`.

<a id="dockerfile"></a>
## `Dockerfile`
Obraz produkcyjny Python 3.12-slim uruchamiający uvicorn na porcie 8000.

Liczba linii: **19**.

### Opis linia-po-linii

- **L1:** Instrukcja Dockerfile: `FROM python:3.12-slim`.
- **L3:** Instrukcja Dockerfile: `WORKDIR /app`.
- **L5:** Instrukcja Dockerfile: `ENV PYTHONDONTWRITEBYTECODE=1 \`.
- **L6:** Instrukcja Dockerfile: `PYTHONUNBUFFERED=1`.
- **L8:** Instrukcja Dockerfile: `COPY requirements.txt .`.
- **L9:** Instrukcja Dockerfile: `RUN pip install --no-cache-dir -r requirements.txt`.
- **L11:** Instrukcja Dockerfile: `COPY app ./app`.
- **L12:** Instrukcja Dockerfile: `COPY static ./static`.
- **L13:** Instrukcja Dockerfile: `COPY schemas ./schemas`.
- **L14:** Instrukcja Dockerfile: `COPY docs ./docs`.
- **L15:** Instrukcja Dockerfile: `COPY README.md ./README.md`.
- **L17:** Instrukcja Dockerfile: `EXPOSE 8000`.
- **L19:** Instrukcja Dockerfile: `CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]`.

<a id="docker-compose-yml"></a>
## `docker-compose.yml`
Jednoserwisowy compose z healthcheckiem `/health` i plikiem `.env`.

Liczba linii: **16**.

### Opis linia-po-linii

- **L1:** Wpis YAML: `services:`.
- **L2:** Wpis YAML: `ai-module:`.
- **L3:** Wpis YAML: `build: .`.
- **L4:** Wpis YAML: `ports:`.
- **L5:** Wpis YAML: `- "8000:8000"`.
- **L6:** Wpis YAML: `env_file:`.
- **L7:** Wpis YAML: `- .env`.
- **L8:** Wpis YAML: `environment:`.
- **L9:** Wpis YAML: `AI_AUTH_ENABLED: "false"`.
- **L10:** Wpis YAML: `SECURITY_FAIL_CLOSED: "false"`.
- **L11:** Wpis YAML: `healthcheck:`.
- **L12:** Wpis YAML: `test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"]`.
- **L13:** Wpis YAML: `interval: 15s`.
- **L14:** Wpis YAML: `timeout: 5s`.
- **L15:** Wpis YAML: `retries: 5`.
- **L16:** Wpis YAML: `start_period: 20s`.

<a id="pytest-ini"></a>
## `pytest.ini`
Konfiguracja pytest: ścieżki testów i wykluczenie `live/` z domyślnego zbierania.

Liczba linii: **4**.

### Opis linia-po-linii

- **L1:** Wpis INI/pytest: `[pytest]`.
- **L2:** Wpis INI/pytest: `testpaths = tests`.
- **L3:** Wpis INI/pytest: `python_files = test_*.py`.
- **L4:** Wpis INI/pytest: `norecursedirs = live .venv`.

<a id="env-example"></a>
## `.env.example`
Szablon zmiennych środowiskowych bez sekretów produkcyjnych.

Liczba linii: **16**.

### Opis linia-po-linii

- **L1:** Zmienna środowiskowa `OPENROUTER_API_KEY` (wartość przykładowa).
- **L2:** Zmienna środowiskowa `OPENROUTER_BASE_URL` (wartość przykładowa).
- **L3:** Zmienna środowiskowa `MAIN_MODEL` (wartość przykładowa).
- **L4:** Zmienna środowiskowa `SECURITY_MODEL` (wartość przykładowa).
- **L5:** Zmienna środowiskowa `TELEMETRY_URL` (wartość przykładowa).
- **L6:** Zmienna środowiskowa `SUMMARY_WEBHOOK_URL` (wartość przykładowa).
- **L7:** Zmienna środowiskowa `CORS_ORIGINS` (wartość przykładowa).
- **L8:** Zmienna środowiskowa `AI_AUTH_ENABLED` (wartość przykładowa).
- **L9:** Zmienna środowiskowa `AI_JWT_SECRET` (wartość przykładowa).
- **L10:** Zmienna środowiskowa `AI_JWT_ALGORITHM` (wartość przykładowa).
- **L11:** Zmienna środowiskowa `RATE_LIMIT_PER_MINUTE` (wartość przykładowa).
- **L12:** Zmienna środowiskowa `CACHE_TTL_SECONDS` (wartość przykładowa).
- **L13:** Zmienna środowiskowa `CACHE_MAX_ENTRIES` (wartość przykładowa).
- **L14:** Zmienna środowiskowa `CONVERSATION_TTL_SECONDS` (wartość przykładowa).
- **L15:** Zmienna środowiskowa `MAX_CONVERSATIONS` (wartość przykładowa).
- **L16:** Zmienna środowiskowa `SECURITY_FAIL_CLOSED` (wartość przykładowa).

<a id="gitignore"></a>
## `.gitignore`
Wzorce plików ignorowanych przez Git (venv, cache, sekrety, IDE).

Liczba linii: **10**.

### Opis linia-po-linii

- **L1:** Wzorzec ignore: `.env`.
- **L2:** Wzorzec ignore: `.venv/`.
- **L3:** Wzorzec ignore: `__pycache__/`.
- **L4:** Wzorzec ignore: `*.py[cod]`.
- **L5:** Wzorzec ignore: `*.egg-info/`.
- **L6:** Wzorzec ignore: `.idea/`.
- **L7:** Wzorzec ignore: `.chroma/`.
- **L8:** Wzorzec ignore: `*.log`.
- **L9:** Wzorzec ignore: `.pytest_cache/`.
- **L10:** Wzorzec ignore: `.mypy_cache/`.

<a id="dockerignore"></a>
## `.dockerignore`
Wzorce wykluczane z kontekstu budowania obrazu Docker.

Liczba linii: **8**.

### Opis linia-po-linii

- **L1:** Wzorzec ignore: `.venv/`.
- **L2:** Wzorzec ignore: `.env`.
- **L3:** Wzorzec ignore: `.idea/`.
- **L4:** Wzorzec ignore: `__pycache__/`.
- **L5:** Wzorzec ignore: `*.py[cod]`.
- **L6:** Wzorzec ignore: `.git/`.
- **L7:** Wzorzec ignore: `*.log`.
- **L8:** Wzorzec ignore: `.pytest_cache/`.
