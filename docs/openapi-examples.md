# OpenAPI / client integration examples (PJA-Sensei AI Module)

Base URL: `http://127.0.0.1:8000`  
Auth: optional `Authorization: Bearer <jwt>` when `AI_AUTH_ENABLED=true`.  
Propagate `X-Request-Id` for correlation with Spring telemetry.

Live OpenAPI: `GET /openapi.json` or Swagger UI `/docs`.  
Static snapshot: [`schemas/openapi.json`](../schemas/openapi.json) / [`schemas/openapi.yaml`](../schemas/openapi.yaml).

---

## 1. Start session

`POST /conversations`

```json
{
  "problem_description": "Napisz kontroler REST zwracający użytkownika w JSON.",
  "config": {
    "learningContext": {
      "goals": ["Utwórz @RestController", "Zwróć JSON"],
      "referenceMaterials": [
        { "type": "doc", "title": "Spring REST", "url": "https://spring.io/guides/gs/rest-service/" }
      ]
    },
    "agentBehavior": {
      "persona": { "role": "mentor", "tone": "cierpliwy" },
      "strictRules": ["Nie podawaj gotowego kodu"],
      "mode": "debug"
    },
    "language": "pl",
    "checkpoints": [
      { "id": "cp1", "after_goal": "Utwórz @RestController", "hint": "Odblokuj testy jednostkowe kontrolera" }
    ],
    "preLab": {
      "enabled": true,
      "max_attempts": 3,
      "hint_after_fail": "Przypomnij sobie, że REST opiera się na HTTP.",
      "questions": [
        { "id": "q1", "prompt": "Co to REST?", "expected_keywords": ["http", "api"] }
      ]
    }
  }
}
```

---

## 2. Pre-lab then chat (rich CodeContext)

`POST /conversations/{id}/prelab` → then `POST /conversations/{id}/messages`

```json
{
  "question": "Dlaczego dostaję 404?",
  "client_message_id": "vscode-msg-001",
  "code_context": {
    "current_file_name": "MyController.java",
    "current_code": "public class MyController {}",
    "workspace_root": "/lab/project",
    "selection": { "start_line": 1, "end_line": 1, "text": "public class MyController {}" },
    "diagnostics": [
      { "severity": "error", "message": "cannot find symbol RestController", "line": 1, "file": "MyController.java" }
    ],
    "open_files": [
      { "path": "pom.xml", "content": "<project>...</project>", "language": "xml" }
    ],
    "error_logs": "404 Not Found"
  }
}
```

Stream: same body to `POST /conversations/{id}/messages/stream` → NDJSON lines `{"type":"token"}` then `{"type":"final",...}`.

---

## 3. IDE events + export + soft close

`POST /conversations/{id}/events`

```json
{ "type": "copy_blocked", "meta": { "source": "chat" } }
```

`GET /conversations/{id}/export` — full archive JSON.

`DELETE /conversations/{id}` — soft summary (if needed) + webhook + RAM/Chroma cleanup.

---

## 4. Experimental endpoints

Tagged `experimental` in OpenAPI (usable in labs, not required for the VS Code happy-path):

| Method | Path |
|--------|------|
| POST | `/conversations/{id}/review` |
| POST | `/conversations/{id}/hints/reveal` |
| POST | `/conversations/{id}/goals/assess` |
| POST | `/conversations/{id}/messages/{message_id}/regenerate` |
| POST | `/conversations/{id}/prelab/generate` |
| GET | `/analytics/correlations` |
