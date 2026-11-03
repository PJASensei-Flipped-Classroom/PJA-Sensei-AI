# Dokumentacja Milestone M6: RAG (ChromaDB + Ochrona SSRF), Cache LRU oraz Progresja Checkpointów

## 1. Cel i Zakres
Milestone M6 miał na celu wzbogacenie mentora **PJA-Sensei** o kontekstową bazę wiedzy (**RAG — Retrieval-Augmented Generation**) zasilaną materiałami prowadzącego, zredukowanie kosztów i opóźnień zapytań do modelu LLM poprzez warstwę pamięci podręcznej (**Exact-Match LRU Cache z TTL**) oraz domknięcie mechaniki punktów kontrolnych (**`next_checkpoint`**) i diagnostyki infrastruktury (**`GET /health`**).

Główne założenia architektoniczne M6 obejmowały:
1. **Bezpieczeństwo sieciowe (SSRF-Safe RAG)**: Zablokowanie możliwości wykorzystania mechanizmu pobierania materiałów referencyjnych do skanowania sieci wewnętrznej lub odczytu metadanych chmurowych.
2. **Pełny cykl życia wektorów**: Indeksacja przy starcie sesji (`POST /conversations`), wyszukiwanie semantyczne w trakcie rozmowy (`POST .../messages` oraz `/stream`) i natychmiastowe zwalnianie pamięci przy usunięciu sesji (`DELETE /conversations/{id}`).
3. **Optymalizacja wywołań LLM**: Zwracanie gotowych odpowiedzi z pamięci podręcznej dla identycznych zapytań bez ponownego obciążania GPU/API.

---

## 2. Wprowadzone mechanizmy i nowości

### 2.1. Moduł RAG z ochroną anty-SSRF (`app/infrastructure/rag_chroma.py`)
* **Walidator `validate_safe_url()`**: Weryfikuje każdy link z `referenceMaterials` przed wykonaniem połączenia HTTP:
  * akceptuje wyłącznie schematy `http` oraz `https` (blokuje m.in. `file://`, `ftp://`, `gopher://`),
  * odrzuca hosty lokalne i wewnętrzne (`localhost`, `.local`, `.internal`, `metadata.google.internal`, `169.254.169.254`),
  * rozwiązuje nazwę domenową przez `socket.getaddrinfo()` i sprawdza każdy zwrócony adres IP za pomocą modułu `ipaddress` (blokuje pule prywatne RFC1918, loopback `127.0.0.0/8`, `::1`, adresy link-local oraz chroni przed atakami typu *DNS Rebinding*),
  * pobiera treść przez `httpx.Client(follow_redirects=False)`, uniemożliwiając otwarte przekierowanie (HTTP 301/302) z bezpiecznej domeny na adres lokalny.
* **Przetwarzanie i indeksacja (`ChromaRagAdapter`)**:
  * Oczyszcza kod HTML ze znaczników `<script>` i `<style>` (`_strip_html`) oraz dzieli tekst na 400-znakowe fragmenty z 50-znakowym zakładem (`_chunk_text`).
  * Wykorzystuje deterministyczny algorytm embeddingów oparty na haszowaniu tokenów (`_embed_text`), co gwarantuje pracę w 100% offline i pełną kompatybilność z Pythonem 3.14 bez konieczności pobierania zewnętrznych modeli ONNX.
  * Zapisuje dokumenty i metadane w efemerycznej kolekcji **ChromaDB** (`EphemeralClient`) z równoległym buforem zapasowym (`_fallback_store`) liczącym podobieństwo kosinusowe.

### 2.2. Pamięć podręczna Exact-Match LRU z TTL (`app/infrastructure/cache_memory.py`)
* **Klucz kanoniczny (`build_cache_key`)**: Generuje skrót `SHA-256` z obiektu JSON zawierającego `model`, `system_prompt` (wraz ze wstrzykniętym kontekstem RAG i aktualnym stanem celów) oraz `messages` z flagą `sort_keys=True`.
* **Struktura `InMemoryLruCache`**:
  * Przechowuje wyniki `LlmResult` w strukturze `OrderedDict` z czasem wygaśnięcia opartym na zegarze monotonicznym (`time.monotonic() + ttl_seconds`).
  * Przy odczycie (`get`) usuwa przeterminowane wpisy (`_purge_expired`), przesuwa odczytany klucz na koniec kolejki LRU i oznacza odpowiedź flagą `debug_info["cache_hit"] = True`.
  * Przy przekroczeniu pojemności `max_size` usuwa najdawniej używany element (`popitem(last=False)`).

### 2.3. Odblokowywanie `next_checkpoint` (`app/application/response_pipeline.py`)
* Rozbudowano metodę `evaluate_checkpoints()`, aby śledziła punkt kontrolny odblokowany w bieżącej turze (`newly_unlocked`). Gdy cel wskazany w `afterGoal` osiąga status `"done"`, student natychmiast otrzymuje w odpowiedzi obiekt `next_checkpoint` z flagą `"unlocked": true` oraz odsłoniętą wskazówką `"hint"`.

### 2.4. Realna diagnostyka w `GET /health` (`app/api/routers/health.py`)
* Zastąpiono statyczne wartości rzeczywistym wywołaniem `rag_adapter.is_healthy()` (wykonującym `heartbeat()` do ChromaDB) oraz `llm_cache.size()`.

---

## 3. Zestawienie utworzonych i edytowanych plików

| Plik | Typ zmiany | Opis wprowadzonych zmian |
|---|---|---|
| `app/infrastructure/rag_chroma.py` | 🟢 **NOWY** | Walidacja anty-SSRF (`validate_safe_url`), czyszczenie HTML, chunking tekstu, generowanie wektorów i klasa `ChromaRagAdapter` (`ingest`, `retrieve`, `delete_conversation`, `is_healthy`). |
| `app/infrastructure/cache_memory.py` | 🟢 **NOWY** | Generator klucza `build_cache_key` (SHA-256) oraz klasa `InMemoryLruCache` z obsługą limitu rozmiaru (LRU) i czasu życia wpisów (TTL). |
| `tests/test_m6.py` | 🟢 **NOWY** | Zestaw testów automatycznych weryfikujących blokadę SSRF, pobieranie źródeł RAG, trafienia w Cache LRU, odblokowanie checkpointu i czyszczenie zasobów. |
| `app/core/config.py` | 🟡 **EDYTOWANY** | Uporządkowano klasę `Settings`, usuwając zduplikowane pola i dodając parametry `CACHE_SIZE`, `CACHE_TTL_SECONDS`, `RAG_TOP_K` oraz `RAG_FETCH_TIMEOUT`. |
| `app/domain/sensei.py` | 🟡 **EDYTOWANY** | Rozszerzono model `ReferenceMaterial` o opcjonalne pole `content: Optional[str] = None` dla środowisk offline i testów. |
| `app/domain/exceptions.py` | 🟡 **EDYTOWANY** | Dodano wyjątek domenowy `SsrfBlockedError(url, reason)`. |
| `app/domain/ports.py` | 🟡 **EDYTOWANY** | Zdefiniowano model `RagChunk` oraz abstrakcyjne interfejsy `RagPort` i `CachePort`. |
| `app/application/prompts.py` | 🟡 **EDYTOWANY** | Rozbudowano `build_system_prompt()` o przyjmowanie `rag_chunks` i wstrzykiwanie sekcji `MATERIAŁY REFERENCYJNE LABU (RAG)` do instrukcji systemowej. |
| `app/application/response_pipeline.py` | 🟡 **EDYTOWANY** | Zmodyfikowano `evaluate_checkpoints()` tak, aby zwracała `newly_unlocked` checkpoint wraz z polem `hint` bezpośrednio w turze zaliczenia celu. |
| `app/application/session_service.py` | 🟡 **EDYTOWANY** | Wstrzyknięto `RagPort`: wywołanie `rag.ingest()` przy starcie sesji oraz `rag.delete_conversation()` przy jej usuwaniu. |
| `app/application/chat_service.py` | 🟡 **EDYTOWANY** | Zintegrowano pobieranie fragmentów RAG i budowanie listy `sources` w `_prepare_turn()` oraz sprawdzanie `cache.get()` / `cache.set()` w `send_message()` i `stream_message()`. |
| `app/api/errors.py` i `app/main.py` | 🟡 **EDYTOWANY** | Dodano i zarejestrowano `ssrf_blocked_handler` mapujący `SsrfBlockedError` na odpowiedź HTTP 400 z `message_id: "ssrf_blocked"`. |
| `app/api/routers/conversations.py` | 🟡 **EDYTOWANY** | Zainicjalizowano singletony `rag_adapter` oraz `llm_cache` i wstrzyknięto je przez `Depends` do `SessionService` oraz `ChatService`. |
| `app/api/routers/health.py` | 🟡 **EDYTOWANY** | Podpięto dynamiczny odczyt `chroma_ok` oraz `cache_size` z aktywnych portów. |

---

## 4. Co testowaliśmy?

1. **Ochrona przed atakami SSRF (`test_m6_ssrf_protection_blocks_unsafe_urls`)**:
   * Bezpośrednie testowanie funkcji `validate_safe_url` na złośliwych wektorach (np. AWS IMDS, hosty z pętli zwrotnej, adresy z puli prywatnej).
   * Test integracyjny endpointu `POST /conversations` z niebezpiecznym linkiem w konfiguracji.
2. **Działanie potoku RAG i pola `sources`**:
   * Zwracanie odnośników w polu `sources` na podstawie trafień z wektorowej bazy wiedzy.
3. **Trafienia w pamięć podręczną (`Cache Hit`)**:
   * Wysłanie identycznego pytania w dwóch sesjach. Weryfikacja pominięcia LLM (`mock_llm.calls == 1`) i zwrotu flagi `cache_hit: true` w drugim zapytaniu.
4. **Odblokowanie punktu kontrolnego (`next_checkpoint`)**:
   * Weryfikacja odblokowania punktu kontrolnego w momencie zaliczenia wymaganego celu (status `done`) wraz z prawidłowym udostępnieniem wskazówki (`hint`).
5. **Diagnostyka i czyszczenie zasobów (`Cleanup`)**:
   * Poprawne raportowanie stanu bazy w `GET /health` oraz czyszczenie danych RAG podczas usuwania sesji przez API.

---

## 5. Napotkane trudności i proces debugowania (Lessons Learned)

Podczas wdrażania Milestone'a M6 rozwiązaliśmy 5 istotnych problemów inżynieryjnych:

### 5.1. Walidacja Pydantic Settings i kolizja zmiennych w `.env`
* **Problem**: Błąd `pydantic_core.ValidationError: Extra inputs are not permitted [cache_ttl]` spowodowany obecnością starej, zduplikowanej zmiennej konfiguracyjnej w pliku `.env`.
* **Rozwiązanie**: Usunięcie zduplikowanych zmiennych, zaktualizowanie klucza na `CACHE_TTL_SECONDS` i opcjonalne dodanie polityki `extra="ignore"` w Pydantic.

### 5.2. Cykliczny błąd zewnętrznego pakietu i literówka
* **Problem**: Środowisko wyrzucało `ImportError` z powodu cyklicznego importu w pakiecie `fetcher`, omyłkowo zaimportowanym przez IDE. Pojawił się również `NameError` przez literówkę `fether` w argumentach konstruktora `ChromaRagAdapter`.
* **Rozwiązanie**: Usunięcie nieużywanych importów (w tym `fetcher` i `bs4`) oraz korekta nazwy argumentu.

### 5.3. Błąd arytmetyki w wyliczaniu wektorów
* **Problem**: Zastosowanie operatora `= sign` nadpisywało wartości na poszczególnych indeksach embeddingu w funkcji `_embed_text`, niszcząc kumulacyjną naturę wektora reprezentującego całe zdanie.
* **Rozwiązanie**: Zmiana operatora na `+= sign`.

### 5.4. Problem podwójnego wywołania LLM (`assert 2 == 1`) i przeskakiwania checkpointów (`assert 'cp2' == 'cp1'`)
* **Problem**: Metoda `ChatService.send_message` z powodu resztkowego kodu z M5 dwukrotnie wzywała LLM dla tego samego zapytania. To prowadziło do błędnego przejścia przez podwójną pętlę w `evaluate_checkpoints`, skutkując natychmiastowym pominięciem odblokowanego punktu i przeskoczeniem do kolejnego zablokowanego.
* **Rozwiązanie**: Zastąpienie potoku `ChatService` zunifikowaną wersją z `self.cache.get()` oraz dodanie obsługi `newly_unlocked` w potoku `ResponsePipeline`.

### 5.5. Utrata atrybutu `cache_hit` przy zwrocie z Cache LRU
* **Problem**: Klasa `InMemoryLruCache` pomyślnie dodawała flagę do nowego słownika, lecz podczas budowania zwracanego obiektu `LlmResult` odwoływano się do starego pola `result.debug_info`.
* **Rozwiązanie**: Podmiana referencji na zbudowany wcześniej `cached_debug`.

---

## 6. Impakt na cały projekt PJA-Sensei

1. **Kontekstowość odpowiedzi (Grounded Mentoring)**: LLM nie zmyśla już odpowiedzi, ale ściśle nawiązuje do przekazanej literatury przedmiotu i popiera swoje rady precyzyjnie przypisanymi linkami z `sources`.
2. **Odporność na ataki sieciowe (Zero-Trust dla URL)**: Bezpieczna walidacja adresów wejściowych chroni serwer przed podatnościami SSRF, skanowaniem portów na localhost i kradzieżą tokenów z instancji Cloud.
3. **Skalowalność**: Exact-Match LRU Cache potrafi zredukować setki identycznych "pytań startowych" od grupy zajęciowej do zaledwie jednego uderzenia w infrastrukturę LLM, skracając czas odpowiedzi do zera i chroniąc budżet tokenów.