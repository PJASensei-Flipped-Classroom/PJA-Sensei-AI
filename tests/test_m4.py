import json
from typing import List, Dict, Optional, Iterator
from fastapi.testclient import TestClient
from app.main import app
from app.domain.ports import LlmPort, LlmResult
from app.api.routers.conversations import get_llm_port
from app.infrastructure.llm_errors import LlmRateLimitError, execute_with_retry_and_fallback

client = TestClient(app)

BASE_CONFIG = {
    "language": "pl",
    "evaluationCriteria": "Poprawny serwis",
    "learningContext": {
        "goals": [
            {"id": "g1", "description": "Stworzenie klasy serwisu"},
            {"id": "g2", "description": "Wstrzyknięcie repozytorium"},
        ]
    },
    "agentPersona": {"name": "Sensei", "tone": "sokratyczny"},
    "agentBehavior": {"mode": "theory"},
    "preLab": {"enabled": False},
}


class BadJsonMockLlm(LlmPort):
    def is_configured(self) -> bool:
        return True

    def generate_json(self, system_prompt: str, messages: List[Dict[str, str]], model_override: Optional[str] = None) -> LlmResult:
        return LlmResult(
            raw_content="{to nie jest poprawny json: [brak zamkniecia",
            tokens_used=40,
            model="bad-json-mock",
        )


class LanguageDriftMockLlm(LlmPort):
    def __init__(self):
        self.calls = 0

    def is_configured(self) -> bool:
        return True

    def generate_json(self, system_prompt: str, messages: List[Dict[str, str]], model_override: Optional[str] = None) -> LlmResult:
        self.calls += 1
        if self.calls == 1:
            payload = {
                "answer": "You should check the constructor and make sure that the repository is injected properly.",
                "prompt_score": 7,
                "prompt_feedback": "Good question",
                "penalty_applied": False,
                "suggested_next_step": "Check constructor",
                "goal_progress": [{"goal": "g1", "status": "in_progress"}],
            }
        else:
            payload = {
                "answer": "Sprawdź konstruktor klasy i zastanów się, jak wstrzyknąć tam repozytorium.",
                "prompt_score": 7,
                "prompt_feedback": "Dobre pytanie",
                "penalty_applied": False,
                "suggested_next_step": "Sprawdź konstruktor",
                "goal_progress": [{"goal": "g1", "status": "in_progress"}],
            }
        return LlmResult(raw_content=json.dumps(payload), tokens_used=50, model="drift-mock")


class DeterministicStreamAndSyncLlm(LlmPort):
    def __init__(self):
        self.payload = {
            "answer": "Świetnie, klasa serwisu jest gotowa! Teraz dodaj konstruktor.",
            "prompt_score": 8,
            "prompt_feedback": "Dobry krok",
            "penalty_applied": False,
            "suggested_next_step": "Dodaj pole repozytorium",
            "goal_progress": [
                {"goal": "g1", "status": "done"},
                {"goal": "g2", "status": "in_progress"},
            ],
        }
        self.raw_json = json.dumps(self.payload, ensure_ascii=False)

    def is_configured(self) -> bool:
        return True

    def generate_json(self, system_prompt: str, messages: List[Dict[str, str]], model_override: Optional[str] = None) -> LlmResult:
        return LlmResult(
            raw_content=self.raw_json,
            tokens_used=max(1, len(self.raw_json) // 4),
            model="deterministic-mock",
        )

    def stream_json(self, system_prompt: str, messages: List[Dict[str, str]], model_override: Optional[str] = None) -> Iterator[str]:
        # Dzielimy surowy JSON na 4 kawałki (tokeny)
        step = max(1, len(self.raw_json) // 4)
        for i in range(0, len(self.raw_json), step):
            yield self.raw_json[i : i + step]


def test_bad_json_does_not_return_500():
    app.dependency_overrides[get_llm_port] = lambda: BadJsonMockLlm()
    try:
        conv_id = client.post("/conversations", json={"config": BASE_CONFIG}).json()["conversation_id"]
        res = client.post(f"/conversations/{conv_id}/messages", json={"question": "Co dalej?"})
        assert res.status_code == 200
        body = res.json()
        assert body["debug_info"]["fallback_json"] is True
        assert len(body["goal_progress"]) == 2
    finally:
        app.dependency_overrides.clear()


def test_language_drift_triggers_retry_and_fixes_language():
    drift_llm = LanguageDriftMockLlm()
    app.dependency_overrides[get_llm_port] = lambda: drift_llm
    try:
        conv_id = client.post("/conversations", json={"config": BASE_CONFIG}).json()["conversation_id"]
        res = client.post(f"/conversations/{conv_id}/messages", json={"question": "Jak zacząć?"})
        assert res.status_code == 200
        body = res.json()
        assert drift_llm.calls == 2
        assert body["debug_info"]["language_drift_retried"] is True
        assert "konstruktor" in body["answer"].lower()
    finally:
        app.dependency_overrides.clear()


def test_llm_errors_429_switches_to_fallback_model():
    called_models = []

    def flaky_call(model_name: Optional[str]) -> str:
        called_models.append(model_name)
        if model_name == "qwen2.5-coder:7b":
            raise LlmRateLimitError("429 Too Many Requests")
        return f"OK from {model_name}"

    result = execute_with_retry_and_fallback(
        fn=flaky_call,
        primary_model="qwen2.5-coder:7b",
        fallback_model="qwen2.5-coder:3b",
        max_retries=2,
    )
    assert result == "OK from qwen2.5-coder:3b"
    assert called_models == ["qwen2.5-coder:7b", "qwen2.5-coder:3b"]


def test_stream_ndjson_and_sync_equivalence():
    mock_llm = DeterministicStreamAndSyncLlm()
    app.dependency_overrides[get_llm_port] = lambda: mock_llm
    try:
        # Sesja A -> wywołanie synchroniczne (POST /messages)
        conv_sync = client.post("/conversations", json={"config": BASE_CONFIG}).json()["conversation_id"]
        sync_res = client.post(
            f"/conversations/{conv_sync}/messages",
            json={"question": "Mam klasę serwisu"},
        )
        assert sync_res.status_code == 200
        sync_data = sync_res.json()

        # Sesja B -> wywołanie strumieniowe (POST /messages/stream)
        conv_stream = client.post("/conversations", json={"config": BASE_CONFIG}).json()["conversation_id"]
        stream_res = client.post(
            f"/conversations/{conv_stream}/messages/stream",
            json={"question": "Mam klasę serwisu"},
        )
        assert stream_res.status_code == 200
        assert "application/x-ndjson" in stream_res.headers["content-type"]

        lines = [json.loads(line) for line in stream_res.text.strip().splitlines() if line.strip()]
        assert len(lines) >= 2

        token_events = [e for e in lines if e["type"] == "token"]
        final_events = [e for e in lines if e["type"] == "final"]

        assert len(token_events) >= 1
        assert len(final_events) == 1

        final_data = final_events[0]
        assert final_data["answer"] == sync_data["answer"]
        assert final_data["prompt_score"] == sync_data["prompt_score"]
        assert final_data["lab_score"] == sync_data["lab_score"]
        assert final_data["goal_progress"] == sync_data["goal_progress"]
        assert final_data["penalty_applied"] == sync_data["penalty_applied"]
    finally:
        app.dependency_overrides.clear()