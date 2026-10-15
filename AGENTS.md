#### 7. `AGENTS.md`
Reguły dla warstw i przyszłego asystenta kodu.


# Reguły Architektoniczne (Hexagonal Architecture)

1. **`app/domain`**: 
   - Jądro systemu. 
   - Zawiera encje (np. Session, SenseiConfig, Goal) i interfejsy (porty abstrakcyjne). 
   - NIE ZNA żadnego zewnętrznego frameworka (np. FastAPI, bazy danych, czy OpenAI). Importy tylko z biblioteki standardowej (ewentualnie Pydantic).

2. **`app/application`**:
   - Zawiera Use Cases (serwisy).
   - Orkiestruje logikę: pobiera dane z interfejsów, wykonuje logikę domenową, zapisuje.
   - Nie wie nic o tym, czy wywołano ją przez HTTP, czy przez CLI.

3. **`app/infrastructure`**:
   - Tu lądują implementacje (adaptery). 
   - Kod komunikujący się z ChromaDB, klient HTTP do Ollamy (OpenAI API), Webhooki Spring.

4. **`app/api`**:
   - Routing FastAPI, parsowanie requestów do DTOs, wstrzykiwanie zależności.
   - Zwraca kody HTTP (200, 400, 503). Przekazuje żądania do `app/application`.