# PJA-Sensei AI Module

Sokratyczny asystent dydaktyczny (FastAPI) do laboratoriów programistycznych — lokalny LLM (Ollama / OpenAI-compatible).

## Dokumentacja

| Plik | Treść |
|------|--------|
| [docs/URUCHOMIENIE.md](docs/URUCHOMIENIE.md) | Jak odpalić projekt, model i API w terminalu |
| [docs/MAPA_PLIKOW.md](docs/MAPA_PLIKOW.md) | Co robi dany plik i z czym jest powiązany |
| [docs/API.md](docs/API.md) | Endpointy dla backendu |
| [docs/TESTY.md](docs/TESTY.md) | Co robi każdy test i jak go uruchomić (komendy osobno) |
| [AGENTS.md](AGENTS.md) | Reguły warstw (dla ludzi i agentów Cursor) |

## Start w 4 komendach

```powershell
.\.venv\Scripts\activate
copy .env.example .env
ollama serve
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

(Pierwszy raz: venv + `pip install -r requirements.txt` + `ollama pull qwen2.5-coder:7b` — szczegóły w [URUCHOMIENIE.md](docs/URUCHOMIENIE.md).)

| URL | |
|-----|--|
| http://127.0.0.1:8000/ | Tester UI |
| http://127.0.0.1:8000/scenarios | Scenariusze z logiem |
| http://127.0.0.1:8000/docs | Swagger |
| http://127.0.0.1:8000/health | Health |

```powershell
python -m pytest -q
```

Wszystkie komendy testów (offline / live / per plik): [docs/TESTY.md](docs/TESTY.md).
