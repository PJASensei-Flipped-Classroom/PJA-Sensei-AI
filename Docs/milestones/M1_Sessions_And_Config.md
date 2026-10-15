# Dokumentacja Milestone M1: Kontrakt SenseiConfig, Sesje In-Memory i Walidacja

## 1. Cel i Zakres
Celem Milestone M1 było wdrożenie rdzenia biznesowego mikroserwisu **PJA-Sensei AI Module**. Zaimplementowano kontrakt konfiguracyjny prowadzącego (`SenseiConfig`), dynamiczne sesje studentów w pamięci RAM, dwupoziomową walidację danych (JSON Schema oraz Pydantic) oraz mechanizm automatycznego usuwania wygasłych sesji (TTL Purge).

W tym etapie nadal celowo pominięto logikę czatu LLM oraz moduł RAG.

---

## 2. Architektura Domeny i Modele Biznesowe

Zgodnie z architekturą heksagonalną, warstwa domeny (`app/domain/`) definiuje strukturę danych w sposób niezależny od frameworków webowych.

### Kluczowe encje:
* **`SenseiConfig`**: Główna konfiguracja laboratoriów tworzona przez prowadzącego. Zawiera cele dydaktyczne (`learningContext`), personę agenta (`agentPersona`), tryb behawioralny (`agentBehavior`: `theory|debug|review`), restrykcje IDE oraz punkty kontrolne (`checkpoints`).
* **Podejście do Checkpointów (Discovery Milestones)**: Checkpointy nie są statycznymi testami wielokrotnego wyboru (ABCD). Działają jako "kamienie milowe odkryć". Gdy student osiągnie dany cel (`afterGoal`), system odblokowuje wskazówkę (`hint`) lub dostęp do kolejnych zasobów kodu.
* **`Conversation`**: Agregat reprezentujący aktywną sesję studenta. Śledzi identyfikator, skopiowaną konfigurację, postęp w celach (`goal_progress` jako statusy: `not_started`, `in_progress`, `done`), odblokowane checkpointy oraz znacznik czasu ostatniej aktywności (`last_activity`).

---

## 3. Dwupoziomowa Walidacja Konfiguracji
Endpoint `POST /validate-config` weryfikuje poprawność pliku konfiguracyjnego dostarczonego przez prowadzącego lub środowisko IDE:
1. **JSON Schema (`schemas/sensei-config.schema.json`)**: Weryfikuje strukturę surowego JSON-a. W przypadku braku pliku schematu system przyjmuje politykę **Fail-Closed** (`schema_unavailable: true`), odrzucając konfigurację ze względów bezpieczeństwa.
2. **Pydantic Model Validator**: Weryfikuje poprawność relacji biznesowych. Przykładowo, customowy walidator sprawdza, czy każdy checkpoint w tablicy `checkpoints` wskazuje na realnie istnienie celu zdefiniowanego w `learning_context.goals`.

---

## 4. Repozytorium i Zarządzanie Cyklem Życia Sesji (TTL Purge)

Zastosowano wzorzec **Repository** z wykorzystaniem portów i adapterów:
* **Port (`app/domain/ports.py`)**: Interfejs `ConversationRepository` definiuje czysty kontrakt operacji na sesjach (`save`, `get`, `delete`, `purge_expired`).
* **Adapter RAM (`app/infrastructure/conversations_memory.py`)**: Implementacja przechowująca dane w słowniku w pamięci operacyjnej.
* **Mechanizm Touch & Garbage Collector**:
  - Każde odczytanie sesji przez metodę `get()` wywołuje funkcję `conv.touch()`, która aktualizuje czas ostatniej aktywności, chroniąc sesję przed przedwczesnym usunięciem.
  - W pliku `app/main.py` skonfigurowano kontekst `lifespan` uruchamiający w tle asynchroniczne zadanie (`purge_task`), które cyklicznie skanuje repozytorium i usuwa sesje, których czas bezczynności przekroczył limit `CONVERSATION_TTL_SECONDS`.

---

## 5. Zestaw Zaimplementowanych Endpointów M1

| Metoda | Ścieżka | Opis |
|---|---|---|
| POST | `/validate-config` | Waliduje przesłany obiekt konfiguracyjny (JSON Schema + reguły Pydantic). |
| POST | `/conversations` | Tworzy nową sesję roboczą studenta, inicjalizując postępy celów. |
| GET | `/conversations/{id}` | Pobiera bieżący stan sesji (m.in. postępy celów, odblokowane checkpointy). |
| DELETE | `/conversations/{id}` | Usuwa wskazaną sesję (zwolnienie zasobów). |
| GET | `/conversations/{id}/restrictions` | Zwraca restrykcje dotyczące plików w IDE dozwolone/zablokowane dla studenta. |
| GET | `/conversations/{id}/export` | Eksportuje pełny zrzut stanu sesji i konfiguracji. |
| GET | `/conversations/{id}/checkpoints` | Zwraca listę aktualnie odblokowanych punktów kontrolnych. |
| POST | `/conversations/{id}/events` | Rejestruje telemetrię i zdarzenia płynące z wtyczki IDE (np. otwarcie pliku, błąd). |

---

## 6. Weryfikacja i Testy
* **Testy jednostkowe**: Uruchamiane przy użyciu biblioteki `pytest` (`PYTHONPATH=. pytest`). Weryfikują poprawność walidatorów, cykl życia sesji oraz kody błędów HTTP 404.
* **Testy interaktywne**: Dostępne za pośrednictwem automatycznie generowanej dokumentacji Swagger UI pod adresem `http://127.0.0.1:8000/docs`.