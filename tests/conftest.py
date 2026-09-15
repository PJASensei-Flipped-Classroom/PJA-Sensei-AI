"""Shared pytest fixtures for offline narrative ASGI tests."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.adapters.security import SecurityService
from app.application.container import AppContainer
from app.main import create_app


def build_valid_config(**overrides) -> dict:
    """Factory creating minimal valid SenseiConfig (camelCase)."""
    base = {
        "learningContext": {
            "goals": ["g1"],
            "referenceMaterials": [],
        },
        "agentBehavior": {
            "persona": {"role": "mentor", "tone": "calm"},
            "strictRules": ["no full code"],
            "mode": "debug",
        },
        "language": "pl",
    }
    base.update(overrides)
    return base


@pytest.fixture()
def container() -> AppContainer:
    """Izolowany AppContainer per test (bez globalnego stanu)."""
    return AppContainer()


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch, container: AppContainer):
    """TestClient with security bypassed and isolated container."""

    async def always_safe(self, user_input: str) -> bool:
        return True

    monkeypatch.setattr(SecurityService, "is_prompt_safe", always_safe)
    monkeypatch.setattr("app.api.routers.health.llm_is_configured", lambda: True)

    app = create_app(container=container)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def client_secure(monkeypatch: pytest.MonkeyPatch, container: AppContainer):
    """TestClient that keeps SecurityService heuristics."""
    monkeypatch.setattr("app.api.routers.health.llm_is_configured", lambda: True)
    app = create_app(container=container)
    with TestClient(app) as test_client:
        yield test_client


def mock_llm_json(
    monkeypatch: pytest.MonkeyPatch,
    container: AppContainer,
    *,
    answer: str = "ok",
    prompt_score: int = 5,
    prompt_feedback: str = "f",
    prompt_tokens: int = 5,
    completion_tokens: int = 5,
    extra: dict | None = None,
) -> AsyncMock:
    """Stub OpenAI-compatible chat.completions.create with a JSON mentor answer."""
    payload: dict = {
        "answer": answer,
        "prompt_score": prompt_score,
        "prompt_feedback": prompt_feedback,
        "penalty_applied": False,
    }
    if extra:
        payload.update(extra)
    mock_choice = MagicMock()
    mock_choice.message.content = json.dumps(payload, ensure_ascii=False)
    mock_response = MagicMock(
        choices=[mock_choice],
        usage=MagicMock(
            prompt_tokens=prompt_tokens, completion_tokens=completion_tokens
        ),
    )
    mock_llm_call = AsyncMock(return_value=mock_response)
    monkeypatch.setattr(container.client.chat.completions, "create", mock_llm_call)
    return mock_llm_call


def mock_hint_json(
    monkeypatch: pytest.MonkeyPatch,
    container: AppContainer,
    *,
    hint: str = "Sprawdź adnotację klasy.",
) -> AsyncMock:
    """Stub LLM for reveal endpoint (hint JSON shape)."""
    mock_choice = MagicMock()
    mock_choice.message.content = json.dumps(
        {"hint": hint, "suggested_next_step": "Dodaj mapping"},
        ensure_ascii=False,
    )
    mock_response = MagicMock(
        choices=[mock_choice],
        usage=MagicMock(prompt_tokens=1, completion_tokens=1),
    )
    mock_call = AsyncMock(return_value=mock_response)
    monkeypatch.setattr(container.client.chat.completions, "create", mock_call)
    return mock_call
