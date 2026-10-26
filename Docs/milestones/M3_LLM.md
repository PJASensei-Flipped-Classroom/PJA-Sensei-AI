# Dokumentacja Milestone M3: Czat Sokratyczny, Integracja LLM i Śledzenie Postępu (X/10)

## 1. Cel i Zakres
Celem Milestone M3 było wdrożenie głównego rdzenia biznesowego mikroserwisu **PJA-Sensei AI Module**: synchronicznego czatu z lokalnym modelem językowym (Ollama / OpenAI-compatible API). System działa jako mentor sokratyczny, który naprowadza studenta na rozwiązanie bez podawania gotowego kodu, ocenia postęp realizacji celów dydaktycznych (`goal_progress`), wylicza wynik laboratorium w skali $0\text{--}10$ (`lab_score`), automatycznie odblokowuje punkty kontrolne (`checkpoints`), pilnuje budżetu tokenów na sesję oraz zapewnia idempotentność zapytań.

---

## 2. Szczegółowy Opis Nowych i Zmodyfikowanych Klas oraz Funkcji

### 2.1. Warstwa Domeny (`app/domain/`)

| Plik | Klasa / Metoda | Założenia i działanie |
|---|---|---|
| `sensei.py` | `CodeContext` | Rozszerzono model kontekstu z wtyczki IDE o pola: `current_file_name` (nazwa aktywnego pliku), `current_code` (pełna treść kodu studenta) oraz `error_logs` (zrzut błędów kompilacji/wykonania). |
| `exceptions.py` | `TokenBudgetExceeded` | Wyjątek domenowy rzucany, gdy zużycie tokenów w sesji (`token_usage`) osiągnie lub przekroczy limit `max_tokens_per_session`. Przechowuje język sesji, limit oraz liczbę zużytych tokenów. |
| `exceptions.py` | `UnknownMessage` | Wyjątek domenowy rzucany przy próbie dodania oceny (feedbacku) do nieistniejącego `message_id`. |
| `conversation.py` | `MessageFeedback` | Model przechowujący ocenę odpowiedzi mentora wystawioną przez studenta (`rating` w skali $1\text{--}5$, opcjonalny `comment` oraz znacznik czasu `created_at`). |
| `conversation.py` | `ChatMessage` | Silnie typowany model pojedynczej wiadomości w historii sesji. Rozróżnia rolę (`user` / `assistant`), przechowuje treść, kontekst kodu, metryki oceny (`prompt_score`, `prompt_feedback`, `penalty_applied`, `suggested_next_step`), zużyte tokeny oraz obiekt `feedback`. |
| `conversation.py` | `Conversation.calculate_lab_score()` | Deterministycznie wylicza wynik laboratorium na podstawie statusów celów według wzoru: `round(10 * done_count / total_goals)`. |
| `conversation.py` | `Conversation.all_goals_done()` | Zwraca `True`, gdy wszystkie cele zdefiniowane w `learning_context.goals` mają status `"done"`. |
| `ports.py` | `LlmResult` | Obiekt transferowy zwracany przez adapter LLM. Zawiera surową odpowiedź (`raw_content`), łączną liczbę zużytych tokenów (`tokens_used`), nazwę modelu (`model`) oraz słownik `debug_info` (podział na `prompt_tokens` i `completion_tokens`). |
| `ports.py` | `LlmPort(ABC)` | Abstrakcyjny port definiujący kontrakt komunikacji z modelem językowym (`generate_json` oraz `is_configured`). Odseparowuje logikę biznesową od konkretnego dostawcy AI. |

---

### 2.2. Warstwa Infrastruktury (`app/infrastructure/`)

#### `app/infrastructure/llm_openai.py` — `OpenAiCompatibleLlmAdapter`
Adapter realizujący interfejs `LlmPort` przy użyciu oficjalnego SDK `openai`, kompatybilny z lokalnym serwerem Ollama (`http://127.0.0.1:11434/v1`):
* **`is_configured()`**: Weryfikuje obecność niepustych parametrów `LLM_BASE_URL`, `LLM_API_KEY` oraz `MAIN_MODEL` w konfiguracji środowiska.
* **`generate_json(system_prompt, messages)`**:
  1. Łączy prompt systemowy (`role: "system"`) z historią konwersacji.
  2. Wywołuje `client.chat.completions.create` z niską temperaturą (`temperature=0.2`) dla zachowania determinizmu oceny oraz wymuszeniem formatu `response_format={"type": "json_object"}`.
  3. Zwraca obiekt `LlmResult` wraz ze statystykami zużycia tokenów pobranymi z `response.usage`.

---

### 2.3. Warstwa Aplikacji (`app/application/`)

#### `app/application/prompts.py` — Generator Promptów Sokratycznych
* **`build_system_prompt(config, current_progress)`**:
  * Generuje instrukcję systemową w języku polskim (`pl`) lub angielskim (`en`) na podstawie `SenseiConfig`.
  * Dostosowuje zachowanie mentora do wybranego trybu (`theory` – pytania koncepcyjne, `debug` – analiza logów i naprowadzanie na błąd, `review` – przegląd jakości kodu).
  * Wstrzykuje aktualną listę celów laboratorium wraz z ich bieżącym statusem (`not_started`, `in_progress`, `done`).
  * Narzuca zakaz podawania gotowego kodu rozwiązania (w przypadku prośby o gotowca model ma obowiązek odmówić i ustawić `"penalty_applied": true`).
  * Definiuje ścisły schemat wyjściowy JSON.
* **`build_user_prompt(question, code_context)`**:
  * Formatuje wiadomość studenta, dołączając do niej przekazane z IDE artefakty: nazwę pliku, aktualny kod, zaznaczony fragment, logi błędów, diagnostykę kompilatora oraz listę otwartych plików.

#### `app/application/chat_service.py` — `ChatService`
Główny serwis orkiestrująjący przebieg rozmowy:
* **`send_message(conv_id, req)`**:
  1. **Bramka Pre-Lab**: Wywołuje `session_svc.ensure_prelab_passed(conv_id)` (rzuca `PrelabRequired` $\rightarrow$ HTTP 403, jeśli quiz wstępny nie został zaliczony).
  2. **Idempotencja**: Sprawdza, czy `req.client_message_id` znajduje się w `conv.idempotency_cache`. Jeśli tak, natychmiast zwraca zapisaną wcześniej odpowiedź `MessageResponse` bez ponownego odpytywania modelu LLM.
  3. **Bramka budżetu tokenów**: Sprawdza, czy `conv.token_usage >= max_tokens_per_session`. W przypadku przekroczenia rzuca `TokenBudgetExceeded` $\rightarrow$ HTTP 403.
  4. **Okno kontekstowe (Sliding Window)**: Pobiera ostatnie 10 wiadomości z historii (`conv.messages[-10:]`), składa je z promptem systemowym i bieżącym pytaniem wzbogaconym o `CodeContext`.
  5. **Komunikacja z LLM i parsowanie**: Wywołuje `llm.generate_json(...)` oraz parsuje odpowiedź metodą `_parse_llm_json(...)`.
  6. **Aktualizacja celów i checkpointów**: Wywołuje `_remember_goal_progress(...)` oraz `_evaluate_checkpoints(...)`.
  7. **Obliczenie punktacji**: Wylicza `lab_score`. Jeżeli wszystkie cele osiągnęły status `"done"`, automatycznie wymusza `prompt_score = 10`.
  8. **Zapis stanu**: Dodaje wiadomości `user` i `assistant` do historii, zwiększa `conv.token_usage`, zapisuje wynik w `idempotency_cache` i utrwala sesję w repozytorium.
* **`_parse_llm_json(raw_text, conv)`**:
  * Defensywny parser odporny na halucynacje formatowania: usuwa znaczniki Markdown, wycina podciąg od pierwszego `{` do ostatniego `}`, a w przypadku uszkodzonego JSON-a zwraca bezpieczny słownik awaryjny (fallback), chroniąc API przed błędem HTTP 500.
* **`_remember_goal_progress(conv, llm_goals)`**:
  * Rozpoznaje cele zarówno po identyfikatorze (`id`), jak i po opisie (`description`).
  * **Strażnik monotoniczności (`STATUS_RANK`)**: Pilnuje, aby status celu mógł wyłącznie rosnąć (`not_started` $[0]$ $\rightarrow$ `in_progress` $[1]$ $\rightarrow$ `done` $[2]$). Raz zaliczony cel nigdy nie zostanie cofnięty przez pomyłkę modelu w kolejnych turach.
* **`_evaluate_checkpoints(conv)`**:
  * Sprawdza wszystkie checkpointy z konfiguracji; jeśli cel wskazany w `after_goal` ma status `"done"`, dopisuje checkpoint do `conv.unlocked_checkpoints` i zwraca informację o kolejnym lub właśnie odblokowanym punkcie kontrolnym.
* **`list_messages(conv_id)`**: Zwraca pełną historię wiadomości w sesji.
* **`add_feedback(conv_id, message_id, req)`**: Przypisuje ocenę ($1\text{--}5$) i komentarz studenta do wskazanej wiadomości w historii.

---

### 2.4. Warstwa API i Obsługa Błędów (`app/api/`)

* **`app/api/errors.py`**:
  * `token_budget_exceeded_handler`: Mapuje wyjątek `TokenBudgetExceeded` na odpowiedź **HTTP 403 Forbidden** z kodem `"message_id": "token_budget_exceeded"`, limitem oraz liczbą zużytych tokenów.
  * `unknown_conversation_handler` / `unknown_message_handler`: Mapują brak sesji lub wiadomości na **HTTP 404 Not Found**.

---

## 3. Zestawienie Nowych i Zaktualizowanych Endpointów w M3

| Metoda | Ścieżka | Status w M3 | Opis działania |
|---|---|---|---|
| `POST` | `/conversations/{conv_id}/messages` | **Nowy (zastąpił stub 501)** | Wysyła pytanie studenta wraz z opcjonalnym `code_context` i `client_message_id`. Zwraca `MessageResponse` z odpowiedzią mentora, oceną, postępem celów i wynikiem labu. |
| `GET` | `/conversations/{conv_id}/messages` | **Nowy** | Zwraca pełną historię wiadomości (`user` oraz `assistant`) zapisanych w ramach sesji. |
| `POST` | `/conversations/{conv_id}/messages/{message_id}/feedback` | **Nowy** | Zapisuje ocenę wiadomości (`rating: 1..5`, `comment`) wystawioną przez studenta. |
| `GET` | `/conversations/{conv_id}` | **Zaktualizowany** | Rozszerzony o pola: `lab_score` ($0\text{--}10$), `lab_completed` (`bool`) oraz `token_usage` (`int`). |
| `GET` | `/health` | **Zaktualizowany** | Pole `llm_configured` sprawdza stan realnego adaptera `OpenAiCompatibleLlmAdapter.is_configured()`, a `conversations` zwraca rzeczywistą liczbę sesji w RAM. |

### Kontrakt odpowiedzi `POST /conversations/{conv_id}/messages` (`MessageResponse`)
```json
{
  "message_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "answer": "Masz już zdefiniowaną klasę. Jakiej adnotacji Springa użyjesz, aby oznaczyć ją jako kontroler REST?",
  "prompt_score": 7,
  "prompt_feedback": "Dobre pytanie o kolejny krok architektoniczny.",
  "tokens_used": 185,
  "penalty_applied": false,
  "sources": [],
  "suggested_next_step": "Dodaj adnotację @RestController nad klasą.",
  "goal_progress": [
    {"goal": "g1", "status": "done"},
    {"goal": "g2", "status": "in_progress"}
  ],
  "lab_score": 5,
  "next_checkpoint": {
    "id": "cp1",
    "after_goal": "g1",
    "hint": "Użyj @GetMapping('/items') nad metodą.",
    "unlocked": true
  },
  "model": "qwen2.5-coder:7b",
  "debug_info": {
    "prompt_tokens": 140,
    "completion_tokens": 45
  }
}
```

### Kontrakt błędu przekroczenia budżetu tokenów (`HTTP 403`)
```json
{
  "message_id": "token_budget_exceeded",
  "detail": "Przekroczono budżet tokenów sesji (360/300).",
  "limit": 300,
  "used": 360
}
```

---

## 4. Jak przetestować Milestone M3?

### 4.1. Testy automatyczne Offline (`pytest`)
Testy w pliku `tests/test_m3.py` wykorzystują mechanizm `app.dependency_overrides[get_llm_port]`, podmieniając klienta sieciowego na deterministyczną klasę `ScriptedMockLlm`. Pozwala to przetestować pełny cykl życia laboratorium w mniej niż 2 sekundy bez udziału serwera Ollama.

Uruchomienie w terminalu:
```bash
PYTHONPATH=. pytest tests/test_m3.py -v
```

**Co weryfikuje test `test_m3_full_happy_path_to_10_out_of_10`:**
1. Utworzenie sesji z 2 celami (`g1`, `g2`), 1 checkpointem (`cp1`) i limitem 300 tokenów.
2. Odrzucenie próby wysłania wiadomości przed rozwiązaniem Pre-Labu (`403 prelab_required`).
3. Poprawne zaliczenie Pre-Labu.
4. Pierwszą turę czatu: zaliczenie celu `g1` $\rightarrow$ wzrost `lab_score` do $5/10$ $\rightarrow$ automatyczne odblokowanie checkpointu `cp1`.
5. Idempotencję: ponowne wysłanie tego samego `client_message_id` zwraca identyczny `message_id` bez zwiększania licznika wywołań modelu LLM.
6. Drugą turę czatu: zaliczenie celu `g2` $\rightarrow$ wzrost `lab_score` do $10/10$ oraz automatyczne podbicie `prompt_score` do $10$.
7. Zgodność stanu w `GET /conversations/{id}` (`lab_completed: true`, `token_usage: 240`).
8. Zapisanie oceny odpowiedzi (`rating: 5`) przez `POST .../feedback`.
9. Blokadę czatu po przekroczeniu limitu 300 tokenów (`403 token_budget_exceeded`).

---

### 4.2. Testy manualne na żywo z lokalnym modelem Ollama (Swagger UI)
1. Upewnij się, że lokalny serwer Ollama działa i posiada model `qwen2.5-coder:7b`:
   ```bash
   ollama run qwen2.5-coder:7b
   ```
2. Uruchom serwer FastAPI:
   ```bash
   uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```
3. Otwórz przeglądarkę pod adresem `http://127.0.0.1:8000/docs`:
   * Sprawdź `GET /health` – upewnij się, że `llm_configured` zwraca `true`.
   * Utwórz sesję przez `POST /conversations` i skopiuj `conversation_id`.
   * Wyślij wiadomość przez `POST /conversations/{conv_id}/messages` z prośbą o gotowca – zweryfikuj, że model odmawia i ustawia `penalty_applied: true`.
   * Wyślij wiadomość z poprawnym kodem w polu `code_context.currentCode` – zweryfikuj zmianę statusu w `goal_progress` na `"done"` oraz aktualizację `lab_score` w `GET /conversations/{conv_id}`.