# Dokumentacja Milestone M0: Fundamenty i Architektura

## 1. Cel i Zakres
Celem Milestone'a M0 było ustanowienie fundamentów pod mikroserwis **PJA-Sensei AI Module**. Skupiliśmy się na przygotowaniu szkieletu aplikacji w frameworku FastAPI, wdrożeniu architektury heksagonalnej (Portów i Adapterów) oraz implementacji podstawowej obserwowalności (health checks, metrics).

W fazie M0 celowo **pominięto** logikę biznesową (sesje, rozmowy) oraz integrację z modelami LLM.

## 2. Architektura Systemu
Zastosowano architekturę heksagonalną w celu ścisłego odseparowania logiki biznesowej od warstwy infrastruktury (np. bazy danych, zew. API LLM) oraz warstwy transportowej (HTTP/FastAPI).

### Struktura Katalogów
* **`app/domain/`**: Serce systemu. Zawiera modele danych (encje) oraz abstrakcje (interfejsy). Nie zależy od żadnych zewnętrznych bibliotek (poza ew. Pydantic).
* **`app/application/`**: Logika orkiestracji (Use Cases). Realizuje scenariusze biznesowe, korzystając z interfejsów zdefiniowanych w domenie.
* **`app/infrastructure/`**: Implementacje interfejsów domenowych (adaptery). Tutaj znajdzie się kod łączący aplikację z bazą wektorową (ChromaDB), klientem LLM (Ollama/OpenAI) oraz systemami uczelni (Webhooki).
* **`app/api/`**: Warstwa prezentacji i transportu. Odpowiada za routing FastAPI, parsowanie żądań (DTO), autoryzację oraz wstrzykiwanie zależności (Dependency Injection).
* **`app/core/`**: Konfiguracja (Settings), zarządzanie błędami i logowanie.

## 3. Zarządzanie Konfiguracją (The Twelve-Factor App)
Konfiguracja opiera się na bibliotece `pydantic-settings`. Aplikacja jest w pełni sterowana przez zmienne środowiskowe (plik `.env`), co gwarantuje łatwe wdrożenie na różnych środowiskach (lokalne, testowe, produkcyjne).

**Kluczowe zmienne środowiskowe:**
* `LLM_BASE_URL` & `MAIN_MODEL`: Adres i model głównego silnika LLM.
* `SECURITY_FAIL_CLOSED` (Boolean): Krytyczna flaga decydująca o zachowaniu w przypadku awarii systemów bezpieczeństwa. Ustawienie `True` (domyślne) gwarantuje, że student nie otrzyma niezweryfikowanej odpowiedzi w razie timeoutu.
* `CORS_ORIGINS`: Pozwala na bezpieczne łączenie się z API z innych domen (np. z webowego UI uczelni).

## 4. Obserwowalność (API Diagnostyczne)
Zaimplementowano zestaw endpointów w `app/api/routers/health.py`, które pozwalają na monitorowanie stanu aplikacji (gotowe pod integrację z Docker/Kubernetes i Prometheus).

| Metoda | Endpoint | Opis | Przykładowa odpowiedź / Kody HTTP |
|---|---|---|---|
| GET | `/healthz` | **Liveness Probe**. Zwraca informację, czy proces w ogóle żyje i odpowiada na żądania. | `200 OK` <br> `{"status": "ok"}` |
| GET | `/health` | **Readiness Probe**. Weryfikuje gotowość do pracy. Sprawdza m.in. czy poprawnie wczytano konfigurację LLM. | `200 OK` (gotowy)<br>`503 Service Unavailable` (brak konfiguracji LLM) |
| GET | `/metrics` | Surowe metryki w formacie JSON (np. liczba aktywnych rozmów). Do prostego monitoringu. | `{"requests_total": 0, ...}` |
| GET | `/metrics/prometheus` | Metryki w natywnym, płaskim formacie tekstowym serwera Prometheus. | `pja_sensei_requests_total 0` |

## 5. Stos Technologiczny
W pliku `requirements.txt` zdefiniowano następujący stos, zoptymalizowany pod lekkość i wydajność:
* **FastAPI + Uvicorn**: Szybki framework webowy z asynchronicznym serwerem.
* **Pydantic**: Walidacja typów i konfiguracji.
* **OpenAI (SDK)**: Standardowy klient pozwalający na komunikację z każdym LLM wspierającym API zgodne z OpenAI (w tym lokalna Ollama).
* **ChromaDB**: Wektorowa baza danych przygotowana pod przyszły moduł RAG (Retrieval-Augmented Generation).