from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

CONFIG_WITH_PRELAB = {
    "language": "pl",
    "evaluationCriteria": "strict",
    "learningContext": {"goals": [{"id": "g1", "description": "Cel 1"}]},
    "agentPersona": {"name": "Sensei", "tone": "helpful"},
    "agentBehavior": {"mode": "theory"},
    "preLab": {
        "enabled": True,
        "maxAttempts": 2,
        "hintAfterFail": "Przeczytaj dokumentację Spring IOC.",
        "questions": [
            {"id": "q1", "question": "Co to jest DI?", "expectedKeywords": ["Dependency", "Injection"]},
            {"id": "q2", "question": "Jakieś pytanie bez słów?", "expectedKeywords": []}
        ]
    }
}


def test_prelab_gate_blocks_messages():
    start_resp = client.post("/conversations", json={"config": CONFIG_WITH_PRELAB})
    conv_id = start_resp.json()["conversation_id"]

    msg_resp = client.post(
        f"/conversations/{conv_id}/messages",
        json={"question": "Próba ominięcia pre-labu"}
    )
    assert msg_resp.status_code == 403
    assert msg_resp.json()["message_id"] == "prelab_required"


def test_prelab_submit_fail_and_limits():
    start_resp = client.post("/conversations", json={"config": CONFIG_WITH_PRELAB})
    conv_id = start_resp.json()["conversation_id"]

    resp1 = client.post(f"/conversations/{conv_id}/prelab",
                        json={"answers": [{"id": "q1", "answer": "Nie wiem"}, {"id": "q2", "answer": "Odp"}]})
    assert resp1.json()["passed"] is False
    assert "q1" in resp1.json()["failed_ids"]
    assert resp1.json()["attempts"] == 1

    resp2 = client.post(f"/conversations/{conv_id}/prelab",
                        json={"answers": [{"id": "q1", "answer": "Dalej nie wiem"}, {"id": "q2", "answer": "Odp"}]})
    assert resp2.json()["passed"] is False
    assert resp2.json()["attempts"] == 2

    status = client.get(f"/conversations/{conv_id}/prelab")
    assert status.json()["hint_after_fail"] == "Przeczytaj dokumentację Spring IOC."

    resp3 = client.post(f"/conversations/{conv_id}/prelab",
                        json={"answers": [{"id": "q1", "answer": "Dependency Injection"}]})
    assert resp3.json()["passed"] is False
    assert resp3.json()["detail"] == "Wyczerpano limit prób."


def test_prelab_submit_success_unlocks_chat():
    start_resp = client.post("/conversations", json={"config": CONFIG_WITH_PRELAB})
    conv_id = start_resp.json()["conversation_id"]

    resp = client.post(f"/conversations/{conv_id}/prelab", json={
        "answers": [
            {"id": "q1", "answer": "To jest dependency injection w klasie"},
            {"id": "q2", "answer": "Dowolny tekst"}
        ]
    })

    assert resp.json()["passed"] is True
    assert resp.json()["unlocked"] is True

    status_resp = client.get(f"/conversations/{conv_id}/prelab")
    assert status_resp.json()["passed"] is True