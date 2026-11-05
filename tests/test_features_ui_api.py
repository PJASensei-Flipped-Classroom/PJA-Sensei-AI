"""API contracts for config builder / session inspector features."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

BASE = {
    "language": "pl",
    "evaluationCriteria": "REST",
    "learningContext": {"goals": [{"id": "g1", "description": "Cel 1"}]},
    "agentPersona": {"name": "Sensei", "tone": "helpful"},
    "agentBehavior": {"mode": "theory"},
    "preLab": {"enabled": False},
}


def test_list_conversations_and_count_active_in_health():
    before = client.get("/conversations").json()
    assert "conversations" in before
    assert "count" in before
    start_count = before["count"]

    created = client.post("/conversations", json={"config": BASE})
    assert created.status_code == 200
    cid = created.json()["conversation_id"]

    listed = client.get("/conversations").json()
    assert listed["count"] == start_count + 1
    assert any(item["conversation_id"] == cid for item in listed["conversations"])

    health = client.get("/health")
    assert health.status_code in (200, 503)
    assert health.json()["conversations"] >= 1

    metrics = client.get("/metrics").json()
    assert metrics["active_conversations"] >= 1


def test_ui_index_and_scenarios_still_served():
    idx = client.get("/")
    assert idx.status_code == 200
    assert "Config Builder" in idx.text
    assert "/messages/stream" in idx.text
    assert "Inspector sesji" in idx.text

    sc = client.get("/scenarios")
    assert sc.status_code == 200
    assert "S1: Bramka Pre-Lab" in sc.text
