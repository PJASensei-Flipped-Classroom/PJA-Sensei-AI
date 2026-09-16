# Uruchomienie PJA-Sensei AI Module

Od zera do działającego API + lokalnego modelu LLM w terminalu.

## Wymagania

- Python **3.11+**
- [Ollama](https://ollama.com/) (domyślnie) albo LM Studio / inny endpoint OpenAI-compatible
- Windows: PowerShell; Linux/macOS: bash (komendy poniżej mają warianty)

## 1. Środowisko Python

```powershell
cd C:\Users\Admin\PJASensei_AI_Module
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

Unix:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2. Plik `.env`

```powershell
copy .env.example .env
```

Unix: `cp .env.example .env`

Kluczowe zmienne (domyślnie pod lokalne Ollama):

| Zmienna | Domyślnie | Znaczenie |
|---------|-----------|-----------|
| `LLM_BASE_URL` | `http://127.0.0.1:11434/v1` | Endpoint chat completions (suffix `/v1`) |
| `LLM_API_KEY` | `ollama` | Dowolny niepusty klucz dla Ollamy |
| `MAIN_MODEL` | `qwen2.5-coder:7b` | Model czatu / summary |
| `SECURITY_MODEL` | ten sam | Model bramki jailbreak |
| `AI_AUTH_ENABLED` | `false` | Lokalnie bez JWT |
| `TELEMETRY_URL` | puste | Webhook wyłączony |

**Po zmianie `.env` zrestartuj uvicorn** — stałe ładują się przy imporcie `app.core.config`.

LM Studio (przykład):

```env
LLM_BASE_URL=http://127.0.0.1:1234/v1
LLM_API_KEY=lm-studio
MAIN_MODEL=<nazwa z LM Studio>
```

## 3. Model (Ollama)

W **osobnym** terminalu:

```powershell
ollama pull qwen2.5-coder:7b
ollama serve
```

Sprawdzenie: `ollama list` — model musi być widoczny.

## 4. Serwer API

Z aktywowanym `.venv`, w katalogu projektu:

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

| URL | Co to |
|-----|--------|
| http://127.0.0.1:8000/health | Readiness (LLM + Chroma) |
| http://127.0.0.1:8000/ | Tester UI (Wykładowca / Student) |
| http://127.0.0.1:8000/scenarios | Runner scenariuszy z logiem |
| http://127.0.0.1:8000/docs | Swagger |

Smoke w PowerShell:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

Unix: `curl -s http://127.0.0.1:8000/health`

## 5. Testy

Szczegóły plików i **wszystkie komendy osobno**: [TESTY.md](TESTY.md).

Offline (mock LLM, bez Ollamy):

```powershell
python -m pytest -q
```

Offline + live (gdy API i Ollama działają):

```powershell
python -m tests.live.test_all
```

Tylko offline przez orchestrator:

```powershell
python -m tests.live.test_all --offline-only
```

Tylko warstwa live:

```powershell
python -m tests.live.test_scenarios --group happy
```

## 6. Docker Compose (lab)

```powershell
copy .env.example .env
# W .env dla Ollamy na hoście Windows/Mac:
# LLM_BASE_URL=http://host.docker.internal:11434/v1
docker compose up --build
```

Compose mapuje port na **127.0.0.1:8000** (nie wystawiaj bez auth na sieć).

## Typowe problemy

| Objaw | Co sprawdzić |
|-------|----------------|
| `health` → 503 / `llm_configured: false` | Ollama działa? `LLM_BASE_URL` kończy się na `/v1`? |
| Czat „nie łączy się z modelem” | `ollama serve`, nazwa `MAIN_MODEL` = `ollama list` |
| Zmiana `.env` bez efektu | Restart uvicorn (nie wystarczy samo `--reload` plików Pythona dla env przy starcie procesu) |
| `401` na API | `AI_AUTH_ENABLED=true` bez JWT — lokalnie ustaw `false` |
| Rate limit 429 | `RATE_LIMIT_PER_MINUTE` albo poczekaj minutę |

## Co dalej

- Endpointy: [API.md](API.md)
- Mapa plików: [MAPA_PLIKOW.md](MAPA_PLIKOW.md)
- Testy: [TESTY.md](TESTY.md)
- Reguły dla agentów: [../AGENTS.md](../AGENTS.md)
