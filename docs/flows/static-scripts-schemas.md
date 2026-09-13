# Przebiegi: static/, scripts/, schemas/

Tester UI, narzędzie dump OpenAPI YAML oraz kontrakty JSON Schema / OpenAPI (bez komentarzy w JSON).

### `static/index.html`

- **Rola:** Prosty tester UI (HTML/CSS/JS) do ręcznych wywołań API.
- **Przebieg funkcjonalności:**
  1. Panel wykładowcy: problem, URL RAG, strictRules → `POST /conversations` + start sesji.
  2. Panel studenta: chat box, kontekst pliku/kodu, pytanie.
  3. JS: send (sync lub stream NDJSON), feedback rating, badge cache/penalty, score bar.
  4. Obsługa loading/spinner, błędy system-red, wyświetlanie sources/debug.
- **Główne zależności:** endpointy /conversations, /messages, /messages/stream, feedback

### `scripts/dump_openapi_yaml.py`

- **Rola:** Konwerter `schemas/openapi.json` → `openapi.yaml` bez PyYAML.
- **Przebieg funkcjonalności:**
  1. `dump(obj)` rekurencyjnie serializuje dict/list/skalary do YAML-like tekstu.
  2. `main` czyta JSON, zapisuje YAML + print ścieżki.

### `schemas/sensei-config.schema.json`

- **Rola:** JSON Schema Draft 2020-12 dla manifestu SenseiConfig.
- **Przebieg funkcjonalności:**
  1. Wymaga `learningContext` + `agentBehavior`; `additionalProperties: false`.
  2. `$defs`: referenceMaterial, preLabQuestion, checkpoint.
  3. Properties: language, ideRestrictions, preLab, evaluationCriteria, maxTokensPerSession, checkpoints.
  4. Używane przez `POST /validate-config` (jsonschema) oraz dokumentację kontraktu labu.

### `schemas/openapi.json`

- **Rola:** Zrzut OpenAPI 3 wygenerowany z aplikacji (kontrakt HTTP).
- **Przebieg funkcjonalności:**
  1. Opisuje paths (conversations, messages, prelab, health, metrics, validate-config, analytics, …).
  2. Komponenty schemas odpowiadają modelom Pydantic request/response.
  3. Tagi: ops, conversations, messages, prelab, experimental, config, analytics.
  4. Źródło prawdy dla klientów VS Code / lab; regeneracja z działającej aplikacji.

### `schemas/openapi.yaml`

- **Rola:** YAML-owa wersja OpenAPI (wygenerowana skryptem dump, bez PyYAML).
- **Przebieg funkcjonalności:**
  1. Semantycznie równoważna `openapi.json`.
  2. Wygodniejsza do diffów w review; odświeżana przez `scripts/dump_openapi_yaml.py`.
