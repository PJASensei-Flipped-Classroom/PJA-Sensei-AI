"""Warstwa 2: student utyka — frustracja, reveal, coaching, theory vs debug."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.application.container import AppContainer
from app.core.config import MAX_REVEALS_PER_SESSION
from tests.conftest import mock_hint_json, mock_llm_json
from tests.helpers import msg_body, start_session


def test_low_scores_unlock_reveal_then_quota(
    client: TestClient,
    container: AppContainer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bez streaku niskich score → 403; po streaku reveal OK aż do limitu sesji."""
    cid = start_session(client)
    conv = container.sessions.get_conversation_or_404(cid)

    assert (
        client.post(f"/conversations/{cid}/hints/reveal", json={"focus": "x"}).status_code
        == 403
    )

    conv.prompt_scores.extend([2, 2])
    mock_hint_json(monkeypatch, container)

    for i in range(MAX_REVEALS_PER_SESSION):
        ok = client.post(
            f"/conversations/{cid}/hints/reveal",
            json={"focus": "controller"},
        )
        assert ok.status_code == 200, ok.text
        body = ok.json()
        assert body["reveal_count"] == i + 1
        assert "```" not in body.get("hint", "")

    exhausted = client.post(
        f"/conversations/{cid}/hints/reveal",
        json={"focus": "controller"},
    )
    assert exhausted.status_code == 403
    assert "quota" in exhausted.json()["detail"].lower()


def test_goal_progress_surfaces_next_checkpoint(
    client: TestClient,
    container: AppContainer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cid = start_session(
        client,
        learningContext={
            "goals": ["Utwórz @RestController", "Zwróć JSON"],
            "referenceMaterials": [],
        },
        checkpoints=[
            {
                "id": "cp1",
                "afterGoal": "Utwórz @RestController",
                "hint": "Odblokuj testy jednostkowe kontrolera",
            }
        ],
    )
    mock_choice = MagicMock()
    mock_choice.message.content = json.dumps(
        {
            "answer": "Kontroler wygląda dobrze.",
            "prompt_score": 7,
            "prompt_feedback": "ok",
            "penalty_applied": False,
            "goal_progress": [
                {"goal": "Utwórz @RestController", "status": "done"},
                {"goal": "Zwróć JSON", "status": "in_progress"},
            ],
        },
        ensure_ascii=False,
    )
    monkeypatch.setattr(
        container.client.chat.completions,
        "create",
        AsyncMock(
            return_value=MagicMock(
                choices=[mock_choice],
                usage=MagicMock(prompt_tokens=5, completion_tokens=5),
            )
        ),
    )
    res = client.post(f"/conversations/{cid}/messages", json=msg_body())
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["next_checkpoint"]["id"] == "cp1"
    assert "cp1" in container.sessions.get_conversation_or_404(cid).unlocked_checkpoints


def test_theory_mode_allows_empty_file_despite_require_context(
    client: TestClient,
    container: AppContainer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_llm_json(monkeypatch, container, answer="Lab o REST JSON.")
    cid = start_session(
        client,
        agentBehavior={
            "persona": {"role": "mentor", "tone": "calm"},
            "strictRules": ["no full code"],
            "mode": "theory",
        },
        ideRestrictions={"requireFileContextForChat": True},
    )
    body = client.post(
        f"/conversations/{cid}/messages",
        json=msg_body("O czym jest zadanie?", code="   "),
    ).json()
    assert body.get("message_id") != "rejected"


def test_debug_require_file_rejects_empty_editor(
    client: TestClient,
    container: AppContainer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_llm_json(monkeypatch, container)
    cid = start_session(client, ideRestrictions={"requireFileContextForChat": True})
    body = client.post(
        f"/conversations/{cid}/messages",
        json=msg_body("O czym jest zadanie?", code="   "),
    ).json()
    assert body["message_id"] == "rejected"
    assert body["tokens_used"] == 0
