import json
from typing import List, Dict
from fastapi.testclient import TestClient
from app.main import app
from app.domain.ports import LlmPort, LlmResult
from app.api.routers.conversations import get_llm_port

client = TestClient(app)

class ScriptedMockLlm(LlmPort):
    """Symuluje kolejne tury rozmowy sokratycznej prowadzące studenta do 10/10."""
    def __init__(self):
        self.turn = 0

    def is_configured(self) -> bool:
        return True

    def generate_json(self, system_prompt: str, messages: List[Dict[str, str]]) -> LlmResult:
        self.turn += 1
        if self.turn == 1:
            payload = {
                "answer": "Dobry początek! Masz już klasę, ale jakiej adnotacji brakuje nad kontrolerem?",
                "prompt_score": 6,
                "prompt_feedback": "Dobre pytanie o strukturę REST.",
                "penalty_applied": False,
                "suggested_next_step": "Dodaj @RestController nad klasą.",
                "goal_progress": [
                    {"goal": "g1", "status": "done"},
                    {"goal": "g2", "status": "in_progress"},
                ],
            }
        else:
            payload = {
                "answer": "Świetnie! Endpoint GET zwraca poprawny obiekt ResponseEntity. Wszystkie cele zaliczone!",
                "prompt_score": 9,  # ChatService podbije to automatycznie do 10 przy wszystkich done
                "prompt_feedback": "Kompletne rozwiązanie zadania.",
                "penalty_applied": False,
                "suggested_next_step": "Laboratorium ukończone!",
                "goal_progress": [
                    {"goal": "g1", "status": "done"},
                    {"goal": "g2", "status": "done"},
                ],
            }
        return LlmResult(
            raw_content=json.dumps(payload),
            tokens_used=120,
            model="mock-qwen2.5-coder:7b",
        )

LAB_CONFIG = {
    "language": "pl",
    "evaluationCriteria": "Poprawny kontroler Spring REST",
    "maxTokensPerSession": 300,
    "learningContext": {
        "goals": [
            {"id": "g1", "description": "Utworzenie klasy z @RestController"},
            {"id": "g2", "description": "Implementacja metody @GetMapping"},
        ]
    },
    "checkpoints": [
        {"id": "cp1", "afterGoal": "g1", "hint": "Użyj @GetMapping('/items') w kolejnym kroku."}
    ],
    "agentPersona": {"name": "Sensei", "tone": "sokratyczny"},
    "agentBehavior": {"mode": "debug"},
    "preLab": {
        "enabled": True,
        "maxAttempts": 3,
        "questions": [
            {"id": "q1", "question": "Jaka adnotacja tworzy kontroler REST?", "expectedKeywords": ["RestController"]}
        ],
    },
}

def test_m3_full_happy_path_to_10_out_of_10():
    mock_llm = ScriptedMockLlm()
    app.dependency_overrides[get_llm_port] = lambda: mock_llm

    try:
        # 1. Start sesji
        start_res = client.post("/conversations", json={"config": LAB_CONFIG})
        assert start_res.status_code == 200
        conv_id = start_res.json()["conversation_id"]

        # 2. Próba wysłania wiadomości przed pre-labem -> 403 prelab_required
        blocked_res = client.post(
            f"/conversations/{conv_id}/messages",
            json={"question": "Pomóż mi z kodem"},
        )
        assert blocked_res.status_code == 403
        assert blocked_res.json()["message_id"] == "prelab_required"

        # 3. Zaliczenie Pre-Labu
        prelab_res = client.post(
            f"/conversations/{conv_id}/prelab",
            json={"answers": [{"id": "q1", "answer": "Używamy adnotacji RestController"}]},
        )
        assert prelab_res.json()["passed"] is True

        # 4. Tura 1: częściowy postęp (1/2 cele done -> 5/10) + test Idempotencji
        turn1_payload = {
            "question": "Stworzyłem klasę, co dalej?",
            "client_message_id": "msg-turn-1",
            "code_context": {
                "currentFileName": "ItemController.java",
                "currentCode": "public class ItemController {}",
            },
        }
        msg1_res = client.post(f"/conversations/{conv_id}/messages", json=turn1_payload)
        assert msg1_res.status_code == 200
        data1 = msg1_res.json()
        assert data1["lab_score"] == 5
        assert data1["next_checkpoint"]["id"] == "cp1"
        assert data1["next_checkpoint"]["unlocked"] is True

        # Ponowne wysłanie tego samego client_message_id NIE wywołuje LLM po raz drugi
        msg1_dup = client.post(f"/conversations/{conv_id}/messages", json=turn1_payload)
        assert msg1_dup.status_code == 200
        assert msg1_dup.json()["message_id"] == data1["message_id"]
        assert mock_llm.turn == 1

        # 5. Tura 2: wszystkie cele done -> 10/10 i prompt_score == 10
        msg2_res = client.post(
            f"/conversations/{conv_id}/messages",
            json={
                "question": "Dodałem @RestController i @GetMapping",
                "code_context": {
                    "currentFileName": "ItemController.java",
                    "currentCode": "@RestController public class ItemController { @GetMapping public String ok() { return \"ok\"; } }",
                },
            },
        )
        assert msg2_res.status_code == 200
        data2 = msg2_res.json()
        assert data2["prompt_score"] == 10
        assert data2["lab_score"] == 10

        # 6. Weryfikacja stanu w GET /conversations/{id}
        conv_state = client.get(f"/conversations/{conv_id}").json()
        assert conv_state["goal_progress"] == {"g1": "done", "g2": "done"}
        assert conv_state["lab_score"] == 10
        assert conv_state["lab_completed"] is True
        assert "cp1" in conv_state["unlocked_checkpoints"]
        assert conv_state["token_usage"] == 240

        # 7. Ocena wiadomości (Feedback)
        fb_res = client.post(
            f"/conversations/{conv_id}/messages/{data2['message_id']}/feedback",
            json={"rating": 5, "comment": "Super naprowadzenie!"},
        )
        assert fb_res.status_code == 200
        assert fb_res.json()["rating"] == 5

        # 8. Przekroczenie budżetu tokenów (ustawionego na 300, po 2 turach mamy 240, ale przetestujmy limit)
        # Zmniejszamy sztucznie limit lub wysyłamy 3. turę, która przekroczy 300 po jej wykonaniu, a 4. zablokuje:
        client.post(f"/conversations/{conv_id}/messages", json={"question": "Dodatkowe pytanie"})
        # Teraz token_usage wynosi 360 >= 300
        budget_res = client.post(
            f"/conversations/{conv_id}/messages",
            json={"question": "Czy budżet mnie zablokuje?"},
        )
        assert budget_res.status_code == 403
        assert budget_res.json()["message_id"] == "token_budget_exceeded"

    finally:
        app.dependency_overrides.clear()