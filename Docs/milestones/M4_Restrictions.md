# Dokumentacja Milestone M4: Strumieniowanie NDJSON, Niezawodność i Potok Odpowiedzi

## 1. Cel i Zakres
Milestone M4 koncentrował się na rozwiązaniu kluczowych problemów UX oraz stabilności występujących przy pracy z wielkimi modelami językowymi (LLM). Głównym celem było wprowadzenie **strumieniowania w czasie rzeczywistym (NDJSON)**, aby zminimalizować odczuwalny czas oczekiwania na odpowiedź, oraz zbudowanie **odpornego potoku przetwarzania (Response Pipeline)**. Potok ten uodparnia system na uszkodzone dane wyjściowe z modelu (zepsuty JSON), błędy sieciowe (np. `429 Rate Limit`) oraz błędy logiczne LLM-a (np. odpowiadanie w złym języku lub podawanie gotowego kodu).

Głównym wymogiem inżynieryjnym w tym etapie było zachowanie aksjomatu **sync $\equiv$ final** – czyli zagwarantowanie, że tryb synchroniczny i strumieniowy przechodzą przez dokładnie taką samą ścieżkę ewaluacji i zwracają tożsamy stan końcowy w bazie danych.

---

## 2. Wprowadzone mechanizmy i nowości

### 2.1. Strumieniowanie NDJSON (`POST .../stream`)
Wdrożono nowy endpoint zwracający odpowiedź w standardzie *Newline Delimited JSON* (NDJSON). Pozwala to wtyczce IDE (lub klientowi webowemu) na renderowanie znaków w czasie rzeczywistym w miarę ich generowania przez układ GPU.
* Klient odbiera strumień zdarzeń z tokenami: `{"type": "token", "text": "..."}`.
* Na samym końcu strumienia serwer przesyła skompletowany, zwalidowany i przeliczony obiekt końcowy: `{"type": "final", "message_id": "...", "prompt_score": 7, ...}`.

### 2.2. Potok Przetwarzania: `ResponsePipeline`
Wydzielono z `ChatService` osobną klasę odpowiedzialną wyłącznie za post-processing surowego tekstu z LLM. Posiada ona następujące filtry:
* **JSON Extractor & Fallback**: Wyłuskuje strukturę JSON z bloków Markdown. Jeśli LLM zhalucynuje i wygeneruje nieparsowalny ciąg (np. urwany bracket), potok automatycznie generuje bezpieczny payload zastępczy (`build_fallback_payload`). Dzięki temu zepsuty JSON nie powoduje już błędu `500 Internal Server Error`.
* **Language Drift Corrector**: Wykrywa zmianę języka generacji na podstawie zoptymalizowanych słowników wyrażeń regularnych (`PL_WORDS_RE` i `EN_WORDS_RE`). Gdy model pomyłkowo przejdzie na angielski (przy ustawionym `language="pl"`), potok przechwytuje błąd przed wysłaniem odpowiedzi i automatycznie ponawia zapytanie (Retry) ze stanowczym upomnieniem dla LLM.
* **Code Penalty**: Weryfikuje za pomocą regexów (np. `CODE_BLOCK_RE`), czy wygenerowana odpowiedź zawiera wielolinijkowy, gotowy kod źródłowy lub czy uczeń wymusił na modelu gotowca. W przypadku naruszenia reguł, potok oznacza sesję flagą `"penalty_applied": true` i brutalnie przycina `prompt_score` do maksymalnie 4 punktów.

### 2.3. Odporność na Błędy LLM (`llm_errors.py`)
Zaimplementowano dekorator/wrapper `execute_with_retry_and_fallback`, który:
* Reaguje na tymczasowe błędy sieciowe (Timeout, Connection Error) poprzez automatyczne ponawianie złożeń (Backoff).
* Reaguje na limit zapytań **429 Too Many Requests**. W przypadku jego wystąpienia system "w locie" podmienia główny model (np. `qwen2.5-coder:7b`) na zdefiniowany model zapasowy (`MAIN_MODEL_FALLBACK`, np. `qwen2.5-coder:3b`) i kontynuuje działanie bez zwracania błędu do studenta.

---

## 3. Zmiany w strukturze projektu (Katalogi i Pliki)

| Plik | Typ zmiany | Opis |
|---|---|---|
| `app/infrastructure/llm_errors.py` | 🟢 NOWY | Logika retry, klasyfikacja błędów (Transient / Rate Limit) oraz mechanizm fallbacku na model zapasowy. |
| `app/application/response_pipeline.py` | 🟢 NOWY | Ekstrakcja JSON, bezpieczny fallback, naprawa `language drift`, wymuszanie `code penalty` i monotoniczność postępu celów. |
| `tests/test_m4.py` | 🟢 NOWY | Kompletny zestaw 4 testów automatycznych weryfikujących edge case'y zepsutego JSONa, dryfu językowego, HTTP 429 i równoważności strumienia. |
| `app/core/config.py` | 🟡 EDYTOWANY | Zdefiniowanie parametrów `MAIN_MODEL_FALLBACK` i `LLM_MAX_RETRIES`. |
| `app/domain/ports.py` | 🟡 EDYTOWANY | Rozszerzenie `LlmPort` o abstrakcyjną metodę `stream_json()` zwracającą `Iterator[str]`. |
| `app/infrastructure/llm_openai.py` | 🟡 EDYTOWANY | Implementacja strumieniowania przez oficjalne SDK OpenAI (`stream=True`) oraz integracja `execute_with_retry_and_fallback`. |
| `app/application/chat_service.py` | 🟡 EDYTOWANY | Przeniesienie logiki analizy tekstu do obiektu `pipeline`. Utworzenie wspólnego gardła ewaluacyjnego `_finalize_response` używanego zarówno przez tryb sync jak i stream. |
| `app/api/routers/conversations.py` | 🟡 EDYTOWANY | Dodanie endpointu `POST /{conv_id}/messages/stream` z wykorzystaniem `StreamingResponse`. |

---

## 4. Spełnienie Definition of Done (DoD)

Wszystkie warunki DoD dla M4 zostały rygorystycznie spełnione i pokryte testami:
1. **Stream działa**: Zaimplementowano strumień NDJSON zwracający płynnie wydarzenia `token` oraz finałowe zakończenie `final`.
2. **sync $\equiv$ final**: Test `test_stream_ndjson_and_sync_equivalence` weryfikuje, że zapytanie synchroniczne i strumieniowe z deterministycznego modelu zwracają identyczne parametry (punktację, `message_id`, oceny i statusy celów).
3. **Zły JSON $\neq$ 500**: Test `test_bad_json_does_not_return_500` udowadnia, że podrzucenie do parsera uszkodzonego stringa skutecznie buduje awaryjny zestaw odpowiedzi i kontynuuje działanie sesji bez zawieszania serwera błędem HTTP 5xx.

---

## 5. Impakt na cały projekt (Dlaczego M4 było kluczowe?)

1. **Gotowość Frontendu / IDE (UX)**: Interfejs programowania (np. wtyczka w JetBrains/VSCode) nie musi "zawieszać się" na 10 sekund po każdym pytaniu studenta. Odbieranie strumienia tokenów symuluje żywą obecność mentora i drastycznie zwiększa odczuwalną responsywność aplikacji.
2. **Solidność i Ciągłość (Resilience)**: PJA-Sensei jest teraz uodpornione na tak zwany *AI Hallucination Crash*. Jeśli mały model lokalny pod wpływem wysokiej "temperatury" wygeneruje kod zamiast JSON-a, aplikacja poradzi sobie bez wybudzania administratora (bezpieczny fallback).
3. **Czysta Architektura (Separation of Concerns)**: Wydzielenie `ResponsePipeline` uchroniło klasę `ChatService` przed przekształceniem w trudny do utrzymania tzw. *God Object*. `ChatService` orkiestruje sesją i bazą, a `ResponsePipeline` samodzielnie brudzi sobie ręce wyrażeniami regularnymi.
4. **Gotowość na wdrażanie w Chmurze (AWS/Azure)**: Zaimplementowanie mechanizmu obsługi błędu `429 Too Many Requests` z natychmiastowym przełączeniem na model zapasowy to fundamentalny wzorzec z systemów High Availability, który uchroni uczelniany budżet i zapewni ciągłość laboratorium podczas piku zapytań setek studentów.