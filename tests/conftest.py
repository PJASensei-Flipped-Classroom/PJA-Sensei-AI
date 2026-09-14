"""Shared pytest fixtures for offline ASGI tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.adapters.security import SecurityService
from app.application.container import AppContainer
from app.main import create_app


def build_valid_config(**overrides) -> dict:
    """Factory creating minimal valid SenseiConfig."""
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
    """TestClient with security regex/LLM bypassed and isolated container."""

    async def always_safe(self, user_input: str) -> bool:
        return True

    monkeypatch.setattr(SecurityService, "is_prompt_safe", always_safe)
    monkeypatch.setattr(
        "app.api.routers.health.openrouter_key_is_configured", lambda: True
    )

    app = create_app(container=container)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def client_secure(monkeypatch: pytest.MonkeyPatch, container: AppContainer):
    """TestClient that keeps SecurityService heuristics (no always-safe bypass)."""
    monkeypatch.setattr(
        "app.api.routers.health.openrouter_key_is_configured", lambda: True
    )
    app = create_app(container=container)
    with TestClient(app) as test_client:
        yield test_client


def mock_llm_json(
    monkeypatch: pytest.MonkeyPatch,
    container: AppContainer,
    *,
    answer: str = "ok",
    prompt_tokens: int = 5,
    completion_tokens: int = 5,
) -> AsyncMock:
    """Stub OpenAI-compatible chat.completions.create with a JSON answer."""
    mock_choice = MagicMock()
    mock_choice.message.content = (
        f'{{"answer": "{answer}", "prompt_score": 5, "prompt_feedback": "f"}}'
    )
    mock_response = MagicMock(
        choices=[mock_choice],
        usage=MagicMock(
            prompt_tokens=prompt_tokens, completion_tokens=completion_tokens
        ),
    )
    mock_llm_call = AsyncMock(return_value=mock_response)
    monkeypatch.setattr(container.client.chat.completions, "create", mock_llm_call)
    return mock_llm_call
