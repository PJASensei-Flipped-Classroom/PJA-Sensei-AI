"""Warstwa 1: student przechodzi lab od startu do końca (happy path)."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.application.container import AppContainer
from tests.conftest import mock_llm_json
from tests.helpers import (
    assert_message_shape,
    happy_lab_config,
    msg_body,
    pass_prelab,
    start_session,
)


def test_student_completes_full_lab_session(
    client: TestClient,
    container: AppContainer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Health → validate → start → prelab fail+pass → chat → events → summary → export → delete."""
    # 1. Health / metrics
    assert client.get("/health").status_code == 200
    assert client.get("/metrics").status_code == 200

    # 2. Validate config
    cfg = happy_lab_config()
    validated = client.post("/validate-config", json={"config": cfg})
    assert validated.status_code == 200
    assert validated.json()["valid"] is True

    # 3. Start session
    started = client.post(
        "/conversations",
        json={
            "problem_description": "Napisz kontroler REST zwracający dane użytkownika w JSON.",
            "config": cfg,
        },
    )
    assert started.status_code == 200, started.text
    body = started.json()
    cid = body["conversation_id"]
    assert body.get("prelab_required") is True

    # 4. Prelab: fail once, then pass
    quiz = client.get(f"/conversations/{cid}/prelab")
    assert quiz.status_code == 200
    assert quiz.json().get("questions")

    fail = client.post(
        f"/conversations/{cid}/prelab",
        json={"answers": [{"id": "q1", "answer": "nie wiem"}]},
    )
    assert fail.status_code == 200
    assert fail.json()["passed"] is False

    # Chat still gated
    blocked = client.post(f"/conversations/{cid}/messages", json=msg_body("pomóż"))
    assert blocked.status_code == 403
    assert blocked.json().get("message_id") == "prelab_required"

    pass_prelab(client, cid)

    # 5. Theory-ish question after unlock
    mock_llm_json(
        monkeypatch,
        container,
        answer="REST to styl API oparty o HTTP i zasoby.",
        prompt_score=7,
        extra={
            "suggested_next_step": "Dodaj @RestController",
            "goal_progress": [
                {"goal": "Utwórz @RestController", "status": "in_progress"},
                {"goal": "Zwróć JSON", "status": "not_started"},
            ],
        },
    )
    theory = client.post(
        f"/conversations/{cid}/messages",
        json=msg_body("Co to jest REST?", code=""),
    )
    assert theory.status_code == 200, theory.text
    assert_message_shape(theory.json())
    assert "REST" in theory.json()["answer"] or theory.json()["prompt_score"] >= 1

    # 6. Code-context turn + goal progress that unlocks checkpoint
    mock_choice = MagicMock()
    mock_choice.message.content = json.dumps(
        {
            "answer": "Dobrze — masz kontroler. Co z body odpowiedzi?",
            "prompt_score": 8,
            "prompt_feedback": "ok",
            "penalty_applied": False,
            "suggested_next_step": "",
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
    coded = client.post(
        f"/conversations/{cid}/messages",
        json=msg_body(
            "Mam klasę z @RestController — co dalej?",
            code="@RestController\nclass UserController {}",
        ),
    )
    assert coded.status_code == 200, coded.text
    coded_body = coded.json()
    assert coded_body.get("next_checkpoint") is not None
    assert coded_body["next_checkpoint"]["id"] == "cp1"

    # 6b. Domknięcie obu celów → cel labu 10/10
    mock_choice_done = MagicMock()
    mock_choice_done.message.content = json.dumps(
        {
            "answer": "Świetnie — masz @RestController i zwrot JSON. Cel labu zaliczony.",
            "prompt_score": 10,
            "prompt_feedback": "Oba cele domknięte.",
            "penalty_applied": False,
            "goal_progress": [
                {"goal": "Utwórz @RestController", "status": "done"},
                {"goal": "Zwróć JSON", "status": "done"},
            ],
        },
        ensure_ascii=False,
    )
    monkeypatch.setattr(
        container.client.chat.completions,
        "create",
        AsyncMock(
            return_value=MagicMock(
                choices=[mock_choice_done],
                usage=MagicMock(prompt_tokens=5, completion_tokens=5),
            )
        ),
    )
    done_turn = client.post(
        f"/conversations/{cid}/messages",
        json=msg_body(
            "Zwracam User przez ResponseEntity — czy cele są gotowe?",
            code="@RestController\npublic class UserController {\n"
            "  @GetMapping(\"/{id}\")\n"
            "  public ResponseEntity<User> get(@PathVariable Long id) {\n"
            "    return ResponseEntity.ok(user);\n  }\n}",
        ),
    )
    assert done_turn.status_code == 200, done_turn.text
    assert done_turn.json()["prompt_score"] == 10
    state = client.get(f"/conversations/{cid}")
    assert state.status_code == 200
    gp = state.json().get("goal_progress") or []
    assert gp and all(g.get("status") == "done" for g in gp)
    lab = round(10 * sum(1 for g in gp if g.get("status") == "done") / len(gp))
    assert lab == 10

    # Events + feedback
    ev = client.post(
        f"/conversations/{cid}/events",
        json={"type": "file_opened", "meta": {"path": "UserController.java"}},
    )
    assert ev.status_code == 200

    mid = done_turn.json()["message_id"]
    fb = client.post(
        f"/conversations/{cid}/messages/{mid}/feedback",
        json={"rating": 5, "comment": "pomocne"},
    )
    assert fb.status_code == 200

    cps = client.get(f"/conversations/{cid}/checkpoints")
    assert cps.status_code == 200
    cp_payload = cps.json()
    items = cp_payload if isinstance(cp_payload, list) else cp_payload.get("checkpoints") or cp_payload.get("items") or []
    if isinstance(items, list) and items:
        assert any(i.get("id") == "cp1" and i.get("unlocked") for i in items)
    else:
        assert "cp1" in container.sessions.get_conversation_or_404(cid).unlocked_checkpoints

    # 7. Summary
    summary_choice = MagicMock()
    summary_choice.message.content = json.dumps(
        {
            "mastery_score": 70,
            "student_actions": "prelab + 2 pytania",
            "agent_evaluation_of_student": "dobry postęp",
            "student_evaluation_of_agent": "n/a",
            "professors_summary": "Student zaliczył prelab i ruszył kontroler.",
            "goal_mastery": [
                {"goal": "Utwórz @RestController", "status": "done", "notes": "ok"}
            ],
            "criteria_assessment": [
                {"criterion": "Clarity", "assessment": "good"},
                {"criterion": "Progress", "assessment": "good"},
            ],
            "reveal_usage": {"count": 0, "notes": "none"},
            "ide_events_detail": "file_saved",
        },
        ensure_ascii=False,
    )
    monkeypatch.setattr(
        container.client.chat.completions,
        "create",
        AsyncMock(
            return_value=MagicMock(
                choices=[summary_choice],
                usage=MagicMock(prompt_tokens=1, completion_tokens=1),
            )
        ),
    )
    summary = client.post(f"/conversations/{cid}/summary")
    assert summary.status_code == 200, summary.text
    sbody = summary.json()
    assert "professors_summary" in sbody
    assert "mastery_score" in sbody

    # 8. Export + soft delete
    export = client.get(f"/conversations/{cid}/export")
    assert export.status_code == 200

    deleted = client.delete(f"/conversations/{cid}")
    assert deleted.status_code == 200
    assert deleted.json().get("status") == "deleted"
    assert client.get(f"/conversations/{cid}").status_code == 404


def test_start_session_helper_works(client: TestClient) -> None:
    cid = start_session(client)
    assert client.get(f"/conversations/{cid}").status_code == 200
