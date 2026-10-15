import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

VALID_CONFIG = {
    "language": "pl",
    "evaluationCriteria": "strict",
    "learningContext": {"goals": [{"id": "g1", "description": "Cel 1"}]},
    "agentPersona": {"name": "Sensei", "tone": "helpful"},
    "agentBehavior": {"mode": "theory"}
}

def test_validate_config_valid():
    response = client.post("/validate-config", json={"config": VALID_CONFIG})
    assert response.status_code == 200
    assert response.json()["valid"] is True

def test_validate_config_invalid_checkpoint():
    invalid_config = VALID_CONFIG.copy()
    invalid_config["checkpoints"] = [{"id": "cp1", "afterGoal": "nie_istnieje", "hint": "hint"}]
    response = client.post("/validate-config", json={"config": invalid_config})
    assert response.status_code == 200
    assert response.json()["valid"] is False
    assert len(response.json()["pydantic_errors"]) > 0

def test_conversation_lifecycle():
    # Start
    start_resp = client.post("/conversations", json={"config": VALID_CONFIG})
    assert start_resp.status_code == 200
    conv_id = start_resp.json()["conversation_id"]

    # Get
    get_resp = client.get(f"/conversations/{conv_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["goal_progress"]["g1"] == "not_started"

    # Export Shape
    export_resp = client.get(f"/conversations/{conv_id}/export")
    assert export_resp.status_code == 200
    assert "learningContext" in export_resp.json()["config"]

    # Delete
    del_resp = client.delete(f"/conversations/{conv_id}")
    assert del_resp.status_code == 200

    # Get 404
    get_resp_404 = client.get(f"/conversations/{conv_id}")
    assert get_resp_404.status_code == 404