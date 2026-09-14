"""Offline tests for provider 429 retry → fallback model policy."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.application.container import AppContainer
from app.application.llm_errors import (
    call_with_rate_limit_policy,
    is_rate_limit_error,
    resolve_fallback_model,
)
from app.application.response_pipeline import (
    PROVIDER_RATE_LIMITED_ID,
    rate_limit_fallback,
)
from tests.conftest import build_valid_config
from tests.live.helpers import is_provider_rate_limited, skip_if_provider_429


def _rate_limit_exc(msg: str = "Error code: 429 - rate-limited upstream") -> Exception:
    exc = Exception(msg)
    exc.status_code = 429  # type: ignore[attr-defined]
    return exc


def test_is_rate_limit_error_detects_429() -> None:
    assert is_rate_limit_error(_rate_limit_exc())
    assert is_rate_limit_error(Exception("Provider returned error code: 429"))
    assert not is_rate_limit_error(Exception("timeout"))


def test_resolve_fallback_model_skips_empty_or_same(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.application.llm_errors.MAIN_MODEL_FALLBACK", "")
    assert resolve_fallback_model("primary") is None
    monkeypatch.setattr("app.application.llm_errors.MAIN_MODEL_FALLBACK", "primary")
    assert resolve_fallback_model("primary") is None
    monkeypatch.setattr("app.application.llm_errors.MAIN_MODEL_FALLBACK", "other-model")
    assert resolve_fallback_model("primary") == "other-model"


def test_rate_limit_fallback_copy_pl_en() -> None:
    pl = rate_limit_fallback("m1", "pl")
    assert pl["message_id"] == PROVIDER_RATE_LIMITED_ID
    assert pl["tokens_used"] == 0
    assert "limit" in pl["prompt_feedback"].lower() or "ograniczył" in pl["answer"].lower()
    en = rate_limit_fallback("m2", "en")
    assert en["message_id"] == PROVIDER_RATE_LIMITED_ID
    assert "rate-limited" in en["answer"].lower()


def test_is_provider_rate_limited_detects_sentinel() -> None:
    assert is_provider_rate_limited(rate_limit_fallback("ignored", "pl"))
    assert is_provider_rate_limited({"message_id": "x", "prompt_feedback": "Limit (429)."})
    assert not is_provider_rate_limited({"message_id": "abc", "prompt_feedback": "ok"})
    skip = skip_if_provider_429(1, "Teoria", rate_limit_fallback("x", "en"))
    assert skip is not None and skip.skipped and skip.passed


def test_policy_retry_same_model_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.application.llm_errors.MAIN_MODEL_FALLBACK", "fb-model")
    calls: list[str] = []

    async def call(model: str) -> str:
        calls.append(model)
        if len(calls) == 1:
            raise _rate_limit_exc()
        return "ok"

    result = asyncio.run(call_with_rate_limit_policy("primary", call, backoff_seconds=0))
    assert result == ("ok", "primary")
    assert calls == ["primary", "primary"]


def test_policy_falls_back_after_two_429s(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.application.llm_errors.MAIN_MODEL_FALLBACK", "fb-model")
    calls: list[str] = []

    async def call(model: str) -> str:
        calls.append(model)
        if model == "primary":
            raise _rate_limit_exc()
        return "from-fallback"

    result = asyncio.run(call_with_rate_limit_policy("primary", call, backoff_seconds=0))
    assert result == ("from-fallback", "fb-model")
    assert calls == ["primary", "primary", "fb-model"]


def test_policy_exhausted_reraises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.application.llm_errors.MAIN_MODEL_FALLBACK", "fb-model")

    async def always_429(model: str) -> str:
        raise _rate_limit_exc(f"429 on {model}")

    with pytest.raises(Exception) as ei:
        asyncio.run(call_with_rate_limit_policy("primary", always_429, backoff_seconds=0))
    assert is_rate_limit_error(ei.value)


def test_chat_message_rate_limit_exhausted_returns_friendly_body(
    client: TestClient,
    container: AppContainer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.application.llm_errors.MAIN_MODEL_FALLBACK", "fb-model")
    monkeypatch.setattr("app.application.llm_errors.RATE_LIMIT_BACKOFF_SECONDS", 0)

    async def always_429(*_a, **_k):
        raise _rate_limit_exc()

    monkeypatch.setattr(
        container.client.chat.completions, "create", AsyncMock(side_effect=always_429)
    )

    started = client.post(
        "/conversations",
        json={"problem_description": "lab", "config": build_valid_config()},
    )
    assert started.status_code == 200
    cid = started.json()["conversation_id"]

    res = client.post(
        f"/conversations/{cid}/messages",
        json={
            "question": "Jak zaczac?",
            "code_context": {
                "current_file_name": "A.java",
                "current_code": "class A {}",
                "error_logs": "",
            },
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert body["tokens_used"] == 0
    assert body["message_id"] == PROVIDER_RATE_LIMITED_ID
    assert body.get("model") is None
    text = (body.get("answer") or "") + (body.get("prompt_feedback") or "")
    assert "429" in text or "ograniczył" in text.lower() or "limit" in text.lower()


def test_chat_message_recovers_via_fallback_model(
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
        choices=[ok],
        usage=MagicMock(prompt_tokens=2, completion_tokens=2, total_tokens=4),
    )
    calls: list[str] = []

    async def side_effect(*_a, **kwargs):
        model = kwargs.get("model", "unknown")
        calls.append(model)
        if model != "fb-model":
            raise _rate_limit_exc()
        return ok_resp

    monkeypatch.setattr(
        container.client.chat.completions, "create", AsyncMock(side_effect=side_effect)
    )
    monkeypatch.setattr(container.llm, "model_for", lambda _c: "primary-model")

    started = client.post(
        "/conversations",
        json={"problem_description": "lab", "config": build_valid_config()},
    )
    cid = started.json()["conversation_id"]
    res = client.post(
        f"/conversations/{cid}/messages",
        json={
            "question": "Podpowiedz krok",
            "code_context": {
                "current_file_name": "A.java",
                "current_code": "class A {}",
                "error_logs": "",
            },
        },
    )
    assert res.status_code == 200
    assert "ok z fallback" in res.json()["answer"]
    assert res.json().get("model") == "fb-model"
    assert calls.count("primary-model") >= 2
    assert "fb-model" in calls


def test_chat_message_includes_primary_model(
    client: TestClient,
    container: AppContainer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tests.conftest import mock_llm_json

    mock_llm_json(monkeypatch, container, answer="hello")
    monkeypatch.setattr(container.llm, "model_for", lambda _c: "test-primary-model")

    started = client.post(
        "/conversations",
        json={"problem_description": "lab", "config": build_valid_config()},
    )
    cid = started.json()["conversation_id"]
    res = client.post(
        f"/conversations/{cid}/messages",
        json={
            "question": "Cześć",
            "code_context": {
                "current_file_name": "A.java",
                "current_code": "class A {}",
                "error_logs": "",
            },
        },
    )
    assert res.status_code == 200
    assert res.json().get("model") == "test-primary-model"
