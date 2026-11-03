import json
from typing import List, Dict, Optional, Any
from fastapi.testclient import TestClient
from app.main import app
from app.domain.ports import LlmPort, LlmResult
from app.infrastructure.webhooks import HttpWebhookAdapter
from app.api.routers.conversations import (
    get_llm_port,
    get_webhook_port,
    get_rag_port,
    repo,
)

client = TestClient(app)


class M7MockLlm(LlmPort):
    def is_configured(self) -> bool:
        return True

    def generate_json(
        self,
        system_prompt: str,
        messages: List[Dict[str, str]],
        model_override: Optional[str] = None,
    ) -> LlmResult:
        payload = {
            "answer": "Dobry krok! Zastosowałeś adnotację @RestController poprawnie.",
            "prompt_score": 9,
            "prompt_feedback": "Bardzo dobre pytanie",
            "penalty_applied": False,
            "suggested_next_step": "Dodaj teraz metodę z @GetMapping.",
            "goal_progress": [
                {"goal": "g1", "status": "done"},
                {"goal": "g2", "status": "in_progress"},
            ],
        }
        return LlmResult(
            raw_content=json.dumps(payload),
            tokens_used=45,
            model="m7-mock-llm",
        )


def _sample_config() -> Dict[str, Any]:
    return {
        "language": "pl",
        "evaluationCriteria": "Kontroler Spring",
        "referenceMaterials": [
            {
                "title": "Spring Boot REST Docs",
                "link": "https://spring.io/guides/gs/rest-service",
                "content": "Adnotacja @RestController w Spring Boot łączy @Controller oraz @ResponseBody.",
            }
        ],
        "learningContext": {
            "goals": [
                {"id": "g1", "description": "Utworzenie klasy @RestController"},
                {"id": "g2", "description": "Dodanie endpointu GET"},
            ]
        },
        "checkpoints": [
            {"id": "cp1", "afterGoal": "g1", "hint": "Teraz dodaj @GetMapping('/api')."},
            {"id": "cp2", "afterGoal": "g2", "hint": "Brawo, całe API gotowe!"},
        ],
        "agentPersona": {"name": "Sensei", "tone": "sokratyczny"},
        "agentBehavior": {"mode": "theory"},
        "preLab": {"enabled": False},
    }


def test_m7_request_id_middleware_and_ui_endpoints():
    # 1. X-Request-Id generowany automatycznie
    r1 = client.get("/health")
    assert "X-Request-Id" in r1.headers
    assert len(r1.headers["X-Request-Id"]) > 8

    # 2. X-Request-Id przepisany z żądania klienta
    custom_id = "req-pja-sensei-12345"
    r2 = client.get("/health", headers={"X-Request-Id": custom_id})
    assert r2.headers["X-Request-Id"] == custom_id

    # 3. Endpointy UI: GET / oraz GET /scenarios
    ui_home = client.get("/")
    assert ui_home.status_code == 200
    assert "Panel Wykładowcy" in ui_home.text
    assert "Panel Studenta" in ui_home.text

    ui_scenarios = client.get("/scenarios")
    assert ui_scenarios.status_code == 200
    assert "Scenariusze E2E" in ui_scenarios.text


def test_m7_summary_soft_delete_and_webhooks_fire_and_forget():
    captured_webhooks: List[Dict[str, Any]] = []

    def failing_then_recording_sender(url: str, payload: Dict[str, Any]) -> None:
        captured_webhooks.append(payload)
        # Symulujemy awarię serwera zewnętrznego webhooków (timeout/500)
        raise RuntimeError("Simulated external webhook server 500 timeout!")

    test_webhook_adapter = HttpWebhookAdapter(sender=failing_then_recording_sender)
    app.dependency_overrides[get_llm_port] = lambda: M7MockLlm()
    app.dependency_overrides[get_webhook_port] = lambda: test_webhook_adapter

    try:
        # 1. Start sesji
        start_res = client.post("/conversations", json={"config": _sample_config()})
        assert start_res.status_code == 200
        conv_id = start_res.json()["conversation_id"]

        # 2. Wysłanie wiadomości -> wyzwala webhook 'message' (odporny na błędy sieciowe)
        msg_res = client.post(
            f"/conversations/{conv_id}/messages",
            json={"question": "Mam już @RestController, co dalej?"},
        )
        assert msg_res.status_code == 200
        assert any(w["event"] == "message" for w in captured_webhooks)

        # 3. Wysłanie zdarzenia IDE -> wyzwala webhook 'ide_event' z kluczem "type"
        ev_res = client.post(
            f"/conversations/{conv_id}/events",
            json={"type": "compile_error", "meta": {"line": 12}},
        )
        assert ev_res.status_code == 200
        assert ev_res.json()["frustration_streak"] == 1
        assert any(w["event"] == "ide_event" for w in captured_webhooks)

        # 4. Wygenerowanie podsumowania POST /conversations/{id}/summary -> webhook 'session_summary'
        sum_res = client.post(f"/conversations/{conv_id}/summary")
        assert sum_res.status_code == 200
        sum_data = sum_res.json()
        assert sum_data["conversation_id"] == conv_id
        assert sum_data["lab_score"] == 5  # 1 cel z 2 ukończony: round(10 * 1 / 2) == 5
        assert sum_data["messages_count"] == 2
        assert "Podsumowanie sesji" in sum_data["summary"]
        assert any(w["event"] == "session_summary" for w in captured_webhooks)

        # 5. Soft DELETE: zwraca summary, czyści RAG, oznacza sesję w repo jako is_deleted=True
        del_res = client.delete(f"/conversations/{conv_id}")
        assert del_res.status_code == 200
        del_data = del_res.json()
        assert del_data["status"] == "deleted"
        assert del_data["soft_deleted"] is True
        assert del_data["summary"]["lab_score"] == 5

        # Wektory RAG zostały wyczyszczone
        assert get_rag_port().retrieve(conv_id, "RestController") == []

        # Rekord nadal istnieje w pamięci repozytorium (soft delete) z zapisanym summary
        raw_stored_conv = repo.get(conv_id)
        assert raw_stored_conv is not None
        assert raw_stored_conv.is_deleted is True
        assert raw_stored_conv.summary is not None

        # Kolejne zapytanie GET na usuniętą sesję zwraca 404 Not Found
        get_after_del = client.get(f"/conversations/{conv_id}")
        assert get_after_del.status_code == 404
    finally:
        app.dependency_overrides.clear()