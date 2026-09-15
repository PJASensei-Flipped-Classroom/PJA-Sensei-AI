"""Warstwa 4: edge case’y kontraktu, i18n, ops, unit helpers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import jwt
import pytest
from fastapi.testclient import TestClient

from app.adapters.cache_memory import ExactMatchCache
from app.adapters.rag_chroma import is_safe_rag_url
from app.application.container import AppContainer
from app.application.llm_errors import call_with_rate_limit_policy, is_rate_limit_error
from app.application.response_pipeline import (
    IncrementalAnswerExtractor,
    PROVIDER_RATE_LIMITED_ID,
    answer_has_language_drift,
    contains_cyrillic,
    contains_revealed_code,
)
from app.core.rate_limit import rate_limiter
from app.main import create_app
from tests.conftest import build_valid_config, mock_llm_json
from tests.helpers import msg_body, start_session


# --- Contract ---


def test_unknown_conversation_404(client: TestClient) -> None:
    missing = "00000000-0000-0000-0000-000000000000"
    assert client.get(f"/conversations/{missing}").status_code == 404
    assert client.post(f"/conversations/{missing}/messages", json=msg_body()).status_code == 404


def test_idempotency_same_key_reuses_response(
    client: TestClient,
    container: AppContainer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock = mock_llm_json(monkeypatch, container, answer="raz")
    cid = start_session(client)
    payload = msg_body("pytanie", client_message_id="idem-1")
    r1 = client.post(f"/conversations/{cid}/messages", json=payload)
    r2 = client.post(f"/conversations/{cid}/messages", json=payload)
    assert r1.status_code == 200 and r2.status_code == 200
    assert r1.json()["message_id"] == r2.json()["message_id"]
    assert mock.call_count == 1


def test_rate_limit_returns_429(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(rate_limiter, "limit", 2)
    rate_limiter._hits.clear()
    statuses = [
        client.post("/validate-config", json={"config": build_valid_config()}).status_code
        for _ in range(3)
    ]
    assert 429 in statuses
    rate_limiter._hits.clear()


def test_auth_rejects_missing_and_bad_jwt(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.core.auth.AI_AUTH_ENABLED", True)
    monkeypatch.setattr("app.core.auth.AI_JWT_SECRET", "edge-test-secret-32bytes-minimum!")
    rate_limiter._hits.clear()
    app = create_app(container=AppContainer())
    with TestClient(app) as tc:
        assert tc.get("/conversations/x").status_code == 401
        bad = tc.post(
            "/validate-config",
            json={"config": build_valid_config()},
            headers={"Authorization": "Bearer not-a-jwt"},
        )
        assert bad.status_code == 401
        token = jwt.encode(
            {
                "sub": "student-1",
                "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            },
            "edge-test-secret-32bytes-minimum!",
            algorithm="HS256",
        )
        ok = tc.post(
            "/validate-config",
            json={"config": build_valid_config()},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert ok.status_code == 200
    rate_limiter._hits.clear()


# --- Budget / i18n ---


def test_token_budget_403_pl_and_en(
    client: TestClient,
    container: AppContainer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_llm_json(monkeypatch, container, prompt_tokens=3, completion_tokens=2)
    cid_pl = start_session(client, maxTokensPerSession=1, language="pl")
    assert client.post(f"/conversations/{cid_pl}/messages", json=msg_body("q1")).status_code == 200
    second = client.post(f"/conversations/{cid_pl}/messages", json=msg_body("q2"))
    assert second.status_code == 403
    assert second.json()["message_id"] == "token_budget_exceeded"
    assert "budżet" in second.json()["answer"].lower() or "token" in second.json()["answer"].lower()

    cid_en = start_session(client, maxTokensPerSession=1, language="en")
    assert client.post(f"/conversations/{cid_en}/messages", json=msg_body("q1")).status_code == 200
    second_en = client.post(f"/conversations/{cid_en}/messages", json=msg_body("q2"))
    assert second_en.status_code == 403
    assert "budget" in second_en.json()["answer"].lower()
    assert "budżet" not in second_en.json()["answer"].lower()


def test_en_prelab_403_is_english(client: TestClient) -> None:
    cid = start_session(
        client,
        language="en",
        preLab={
            "enabled": True,
            "maxAttempts": 3,
            "hintAfterFail": "try HTTP",
            "questions": [
                {"id": "q1", "prompt": "REST?", "expectedKeywords": ["http"]}
            ],
        },
    )
    blocked = client.post(f"/conversations/{cid}/messages", json=msg_body("help"))
    assert blocked.status_code == 403
    assert "pre-lab" in blocked.json()["answer"].lower()
    assert "ukończ" not in blocked.json()["answer"].lower()


# --- Session lifecycle ---


def test_ttl_purge_on_start(client: TestClient, container: AppContainer) -> None:
    cid = start_session(client)
    conv = container.sessions.get_conversation_or_404(cid)
    conv.last_active_at = datetime.now(timezone.utc) - timedelta(hours=5)
    assert client.get("/health").status_code == 200
    assert container.conversations.get(cid) is not None
    start_session(client)
    assert container.conversations.get(cid) is None


def test_soft_delete_survives_summary_failure(
    client: TestClient,
    container: AppContainer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cid = start_session(client)
    conv = container.sessions.get_conversation_or_404(cid)
    conv.messages.extend(
        [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello", "message_id": "m1"},
        ]
    )

    async def boom(_conversation_id: str):
        raise RuntimeError("summary unavailable")

    monkeypatch.setattr(container.summary, "generate_summary", boom)
    deleted = client.delete(f"/conversations/{cid}")
    assert deleted.status_code == 200
    assert deleted.json()["status"] == "deleted"
    assert client.get(f"/conversations/{cid}").status_code == 404


# --- Config ---


def test_empty_goals_rejected_by_validate_and_start(client: TestClient) -> None:
    bad = build_valid_config()
    bad["learningContext"] = {"goals": [], "referenceMaterials": []}
    validate = client.post("/validate-config", json={"config": bad})
    assert validate.status_code == 200
    assert validate.json()["valid"] is False
    start = client.post(
        "/conversations",
        json={"problem_description": "lab", "config": bad},
    )
    assert start.status_code == 422


def test_schema_unavailable_fail_closed(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "app.api.routers.config_validate._get_json_schema_validator",
        lambda: None,
    )
    res = client.post("/validate-config", json={"config": build_valid_config()})
    assert res.status_code == 200
    body = res.json()
    assert body["valid"] is False
    assert body["schema_unavailable"] is True


# --- Stream extractor ---


def test_incremental_answer_extractor_partial_json() -> None:
    ext = IncrementalAnswerExtractor()
    chunks = [
        '{"answer":"',
        "Cześć",
        "!",
        '","prompt_score":5}',
    ]
    out = "".join(ext.feed(c) or "" for c in chunks)
    assert "Cześć" in out
    assert "Cześć!" in ext.answer_so_far


# --- LLM 429 ---


def _rate_limit_exc() -> Exception:
    exc = Exception("Error code: 429 - rate limit")
    exc.status_code = 429  # type: ignore[attr-defined]
    return exc


def test_rate_limit_policy_detects_429() -> None:
    assert is_rate_limit_error(_rate_limit_exc()) is True

    import asyncio

    async def always_ok(model: str):
        return f"ok:{model}"

    result, used = asyncio.run(
        call_with_rate_limit_policy("primary", always_ok, backoff_seconds=0)
    )
    assert result == "ok:primary"
    assert used == "primary"


def test_chat_provider_429_friendly_body(
    client: TestClient,
    container: AppContainer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.application.llm_errors.MAIN_MODEL_FALLBACK", "")
    monkeypatch.setattr("app.application.llm_errors.RATE_LIMIT_BACKOFF_SECONDS", 0)

    async def always_429(*_a, **_k):
        raise _rate_limit_exc()

    monkeypatch.setattr(
        container.client.chat.completions, "create", AsyncMock(side_effect=always_429)
    )
    cid = start_session(client)
    res = client.post(f"/conversations/{cid}/messages", json=msg_body())
    assert res.status_code == 200
    body = res.json()
    assert body["message_id"] == PROVIDER_RATE_LIMITED_ID
    assert body["tokens_used"] == 0


def test_chat_recovers_via_fallback_model(
    client: TestClient,
    container: AppContainer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.application.llm_errors.MAIN_MODEL_FALLBACK", "fb-model")
    monkeypatch.setattr("app.application.llm_errors.RATE_LIMIT_BACKOFF_SECONDS", 0)

    ok = MagicMock()
    ok.message.content = (
        '{"answer": "ok z fallback", "prompt_score": 6, "prompt_feedback": "f"}'
    )
    ok_resp = MagicMock(
        choices=[ok], usage=MagicMock(prompt_tokens=1, completion_tokens=1)
    )
    calls = {"n": 0}

    async def flaky(*_a, **kwargs):
        calls["n"] += 1
        model = kwargs.get("model") or (_a[0] if _a else None)
        # First two attempts on primary → 429; then fallback succeeds
        if calls["n"] <= 2:
            raise _rate_limit_exc()
        return ok_resp

    monkeypatch.setattr(
        container.client.chat.completions, "create", AsyncMock(side_effect=flaky)
    )
    cid = start_session(client)
    res = client.post(f"/conversations/{cid}/messages", json=msg_body())
    assert res.status_code == 200
    assert "fallback" in res.json().get("answer", "").lower() or res.json().get(
        "prompt_score", 0
    ) >= 1


# --- RAG / security units ---


def test_is_safe_rag_url_blocks_private() -> None:
    assert is_safe_rag_url("https://example.com/doc.pdf") is True
    assert is_safe_rag_url("http://127.0.0.1/secret") is False
    assert is_safe_rag_url("http://localhost/x") is False
    assert is_safe_rag_url("http://10.0.0.5/internal") is False
    assert is_safe_rag_url("file:///etc/passwd") is False


def test_contains_revealed_code_and_cyrillic_drift() -> None:
    assert contains_revealed_code("Rozważ @RestController nad klasą.") is False
    assert (
        contains_revealed_code(
            "```java\npublic class A { public void x(){ return; } }\n```"
        )
        is True
    )
    mixed = "Pomoc w написании kontrolera"
    assert contains_cyrillic(mixed) is True
    assert answer_has_language_drift(mixed, "pl") is True
    assert answer_has_language_drift("Pomoc w napisaniu kontrolera", "pl") is False


def test_exact_match_cache_ttl_lru() -> None:
    cache = ExactMatchCache(ttl_seconds=3600, max_entries=2)
    cache.save_to_cache("c1", "q1", "", "code-a", {"answer": "1"})
    cache.save_to_cache("c1", "q2", "", "code-b", {"answer": "2"})
    assert cache.get_cached_response("c1", "q1", "", "code-a") is not None
    cache.save_to_cache("c1", "q3", "", "code-c", {"answer": "3"})
    # Capacity 2: after touching q1 then adding q3, one of the older keys is gone
    assert cache.size <= 2
    assert cache.get_cached_response("c1", "q3", "", "code-c") is not None
