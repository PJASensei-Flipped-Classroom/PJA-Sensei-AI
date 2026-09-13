"""Shared pytest fixtures for offline ASGI tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.adapters.security import SecurityService
from app.api.deps import get_container
from app.main import app


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
def client(monkeypatch: pytest.MonkeyPatch):
    """TestClient with security regex/LLM bypassed and clean in-memory state."""

    async def always_safe(self, user_input: str) -> bool:
        return True

    monkeypatch.setattr(SecurityService, "is_prompt_safe", always_safe)

    container = get_container()
    container.conversations.clear()
    if hasattr(container, "cache") and hasattr(container.cache, "_cache"):
        container.cache._cache.clear()

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def client_secure(monkeypatch: pytest.MonkeyPatch):
    """TestClient that keeps SecurityService heuristics (no always-safe bypass)."""
    container = get_container()
    container.conversations.clear()
    if hasattr(container, "cache") and hasattr(container.cache, "_cache"):
        container.cache._cache.clear()

    with TestClient(app) as test_client:
        yield test_client


def mock_llm_json(
    monkeypatch: pytest.MonkeyPatch,
    *,
    answer: str = "ok",
    prompt_tokens: int = 5,
    completion_tokens: int = 5,
) -> AsyncMock:
    """Stub OpenAI-compatible chat.completions.create with a JSON answer."""
    container = get_container()
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
