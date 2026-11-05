"""Abuse / reliability hardening from university audit."""
from typing import Dict, List, Optional

import pytest
from fastapi.testclient import TestClient
from openai import APIConnectionError

from app.api.middleware import reset_rate_limit_buckets
from app.api.routers.conversations import get_llm_port
from app.core.config import settings
from app.domain.ports import LlmPort, LlmResult
from app.domain.sensei import SenseiConfig
from app.infrastructure.llm_errors import LlmUnavailableError, execute_with_retry_and_fallback
from app.main import app

client = TestClient(app, raise_server_exceptions=False)

MINIMAL = {
    "language": "pl",
    "evaluationCriteria": "strict",
    "learningContext": {"goals": [{"id": "g1", "description": "Cel 1"}]},
    "agentPersona": {"name": "Sensei", "tone": "helpful"},
    "agentBehavior": {"mode": "theory"},
    "preLab": {"enabled": False},
}


@pytest.fixture(autouse=True)
def _auth_off():
    prev = settings.AI_AUTH_ENABLED
    settings.AI_AUTH_ENABLED = False
    reset_rate_limit_buckets()
    yield
    settings.AI_AUTH_ENABLED = prev
    app.dependency_overrides.clear()
    reset_rate_limit_buckets()


class BoomLlm(LlmPort):
    def is_configured(self) -> bool:
        return True

    def generate_json(
        self,
        system_prompt: str,
        messages: List[Dict[str, str]],
        model_override: Optional[str] = None,
    ) -> LlmResult:
        raise APIConnectionError(request=None)  # type: ignore[arg-type]


def test_llm_connection_maps_to_503_unavailable():
    app.dependency_overrides[get_llm_port] = lambda: BoomLlm()
    start = client.post("/conversations", json={"config": MINIMAL})
    assert start.status_code == 200
    cid = start.json()["conversation_id"]

    res = client.post(
        f"/conversations/{cid}/messages",
        json={"question": "Jak zacząć?", "codeContext": {"codeSnippet": "class A {}"}},
    )
    assert res.status_code == 503
    body = res.json()
    assert body["message_id"] == "llm_unavailable"
    assert "Retry-After" in res.headers


def test_execute_wraps_transient_as_unavailable():
    def boom(_model):
        raise APIConnectionError(request=None)  # type: ignore[arg-type]

    with pytest.raises(LlmUnavailableError):
        execute_with_retry_and_fallback(
            fn=boom,
            primary_model="m1",
            fallback_model=None,
            max_retries=0,
            backoff_seconds=0,
        )


def test_frustration_cooldown_blocks_hint_farming():
    prev = settings.FRUSTRATION_EVENT_COOLDOWN_SECONDS
    settings.FRUSTRATION_EVENT_COOLDOWN_SECONDS = 60.0
    try:
        cfg = {
            **MINIMAL,
            "frustrationThreshold": 2,
            "maxHints": 2,
            "hints": ["hint-1"],
        }
        cid = client.post("/conversations", json={"config": cfg}).json()["conversation_id"]

        e1 = client.post(
            f"/conversations/{cid}/events",
            json={"type": "compile_error", "meta": {}},
        )
        assert e1.status_code == 200
        assert e1.json()["frustration_streak"] == 1
        assert e1.json()["streak_incremented"] is True

        e2 = client.post(
            f"/conversations/{cid}/events",
            json={"type": "test_failed", "meta": {}},
        )
        assert e2.status_code == 200
        assert e2.json()["frustration_streak"] == 1
        assert e2.json()["streak_incremented"] is False

        locked = client.post(f"/conversations/{cid}/hints/reveal")
        assert locked.status_code == 403
    finally:
        settings.FRUSTRATION_EVENT_COOLDOWN_SECONDS = prev


def test_enabled_prelab_rejects_empty_keywords():
    with pytest.raises(Exception):
        SenseiConfig(
            evaluation_criteria="x",
            learning_context={"goals": [{"id": "g1", "description": "g"}]},
            agent_persona={"name": "S", "tone": "t"},
            agent_behavior={"mode": "theory"},
            pre_lab={
                "enabled": True,
                "questions": [{"id": "q1", "question": "Q?", "expectedKeywords": []}],
            },
        )

    res = client.post(
        "/conversations",
        json={
            "config": {
                **MINIMAL,
                "preLab": {
                    "enabled": True,
                    "questions": [{"id": "q1", "question": "Q?", "expectedKeywords": []}],
                },
            }
        },
    )
    assert res.status_code == 422


def test_oversized_question_rejected():
    cid = client.post("/conversations", json={"config": MINIMAL}).json()["conversation_id"]
    huge = "x" * 9000
    res = client.post(
        f"/conversations/{cid}/messages",
        json={"question": huge},
    )
    assert res.status_code == 422


def test_default_token_budget_not_unlimited():
    cfg = SenseiConfig(
        evaluation_criteria="x",
        learning_context={"goals": [{"id": "g1", "description": "g"}]},
        agent_persona={"name": "S", "tone": "t"},
        agent_behavior={"mode": "theory"},
    )
    assert cfg.max_tokens_per_session == 80_000

    cfg_null = SenseiConfig(
        evaluation_criteria="x",
        learning_context={"goals": [{"id": "g1", "description": "g"}]},
        agent_persona={"name": "S", "tone": "t"},
        agent_behavior={"mode": "theory"},
        max_tokens_per_session=None,
    )
    assert cfg_null.max_tokens_per_session == 80_000


def test_schema_validate_finds_file_off_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    res = client.post(
        "/config/validate",
        json={"config": MINIMAL},
    )
    assert res.status_code == 200
    body = res.json()
    assert body.get("schema_unavailable") is not True
    assert body["valid"] is True
