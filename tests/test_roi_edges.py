"""Additional offline ROI / gate edge cases beyond test_feature_pack."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.application.container import AppContainer
from app.application.response_pipeline import contains_revealed_code
from app.core.config import MAX_REVEALS_PER_SESSION
from tests.conftest import build_valid_config, mock_llm_json


def _start(client: TestClient, **cfg_overrides) -> str:
    res = client.post(
        "/conversations",
        json={
            "problem_description": "ROI edges lab",
            "config": build_valid_config(**cfg_overrides),
        },
    )
    assert res.status_code == 200, res.text
    return res.json()["conversation_id"]


def _msg(question: str = "Jak zacząć?") -> dict:
    return {
        "question": question,
        "code_context": {
            "current_file_name": "A.java",
            "current_code": "class A {}",
            "error_logs": "",
        },
    }


def test_prelab_exhausted_blocks_chat(client: TestClient) -> None:
    cid = _start(
        client,
        preLab={
            "enabled": True,
            "max_attempts": 1,
            "hint_after_fail": "HTTP",
            "questions": [
                {"id": "q1", "prompt": "REST?", "expected_keywords": ["http"]}
            ],
        },
    )
    fail = client.post(
        f"/conversations/{cid}/prelab",
        json={"answers": [{"id": "q1", "answer": "nie"}]},
    )
    assert fail.status_code == 200
    assert fail.json()["passed"] is False

    chat = client.post(f"/conversations/{cid}/messages", json=_msg())
    assert chat.status_code == 403
    assert chat.json().get("message_id") == "prelab_required"


def test_reveal_sanitizes_code_dump_hint(
    client: TestClient,
    container: AppContainer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cid = _start(client)
    conv = container.sessions.get_conversation_or_404(cid)
    conv.prompt_scores.extend([1, 1])

    dump = (
        "```java\n"
        "public class MyController {\n"
        "  @RestController\n"
        "  @GetMapping(\"/users\")\n"
        "  public String users() { return \"x\"; }\n"
        "}\n"
        "```"
    )
    assert contains_revealed_code(dump)

    hint_choice = MagicMock()
    hint_choice.message.content = json.dumps(
        {"hint": dump, "suggested_next_step": "fix"}
    )
    monkeypatch.setattr(
        container.client.chat.completions,
        "create",
        AsyncMock(
            return_value=MagicMock(
                choices=[hint_choice],
                usage=MagicMock(prompt_tokens=1, completion_tokens=1),
            )
        ),
    )

    res = client.post(
        f"/conversations/{cid}/hints/reveal",
        json={"focus": "controller"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert not contains_revealed_code(body["hint"])
    assert "```" not in body["hint"]
    assert body["reveal_count"] == 1
    assert body["reveals_remaining"] == MAX_REVEALS_PER_SESSION - 1


def test_summary_fallback_on_llm_error_still_structured(
    client: TestClient,
    container: AppContainer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cid = _start(
        client,
        learningContext={"goals": ["g1", "g2"], "referenceMaterials": []},
        evaluationCriteria=["Clarity"],
    )
    conv = container.sessions.get_conversation_or_404(cid)
    conv.messages.append({"role": "user", "content": "q"})
    conv.reveal_count = 2
    conv.ide_events.append({"type": "paste_attempt", "meta": {}, "at": "t"})

    monkeypatch.setattr(
        container.client.chat.completions,
        "create",
        AsyncMock(side_effect=RuntimeError("llm down")),
    )

    res = client.post(f"/conversations/{cid}/summary")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["mastery_score"] == 0
    assert isinstance(body.get("goal_mastery"), list)
    assert len(body["goal_mastery"]) == 2
    assert isinstance(body.get("criteria_assessment"), list)
    assert body.get("reveal_usage", {}).get("count") == 2
    assert body["ide_events_structured"]["paste_attempt"] == 1
    assert body["reveal_count"] == 2
    assert "professors_summary" in body


def test_attach_checkpoint_without_matching_goal_keeps_none(
    client: TestClient,
    container: AppContainer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cid = _start(
        client,
        learningContext={
            "goals": ["A", "B"],
            "referenceMaterials": [],
        },
        checkpoints=[
            {"id": "cp1", "after_goal": "A", "hint": "hint-a"},
        ],
    )
    mock_llm_json(monkeypatch, container, answer="jeszcze nie")
    # Override goal_progress to not done
    mock_choice = MagicMock()
    mock_choice.message.content = json.dumps(
        {
            "answer": "jeszcze nie",
            "prompt_score": 5,
            "prompt_feedback": "f",
            "goal_progress": [
                {"goal": "A", "status": "in_progress"},
                {"goal": "B", "status": "not_started"},
            ],
        }
    )
    monkeypatch.setattr(
        container.client.chat.completions,
        "create",
        AsyncMock(
            return_value=MagicMock(
                choices=[mock_choice],
                usage=MagicMock(prompt_tokens=2, completion_tokens=2),
            )
        ),
    )
    res = client.post(f"/conversations/{cid}/messages", json=_msg())
    assert res.status_code == 200
    assert res.json().get("next_checkpoint") is None
    assert "cp1" not in container.sessions.get_conversation_or_404(
        cid
    ).unlocked_checkpoints


def test_empty_answer_uses_prompt_feedback() -> None:
    from app.application.response_pipeline import process_model_response
    from app.domain.conversation import Conversation
    from app.domain.sensei import SenseiConfig

    conv = Conversation(
        problem="lab",
        config=SenseiConfig.model_validate(build_valid_config()),
    )
    raw = json.dumps(
        {
            "answer": "",
            "prompt_score": 3,
            "prompt_feedback": "Zadawaj pytania precyzyjniej, załączając fragmenty kodu.",
            "penalty_applied": False,
        }
    )
    result = process_model_response(
        raw, conv, message_id="m1", tokens_used=10, code_changed=False
    )
    assert result["answer"].startswith("Zadawaj pytania")
    assert result["prompt_score"] == 3
    assert result["answer"] == result["prompt_feedback"]


def test_empty_answer_and_feedback_uses_language_fallback() -> None:
    from app.application.response_pipeline import (
        EMPTY_ANSWER_FALLBACK_PL,
        process_model_response,
    )
    from app.domain.conversation import Conversation
    from app.domain.sensei import SenseiConfig

    conv = Conversation(
        problem="lab",
        config=SenseiConfig.model_validate(build_valid_config()),
    )
    raw = json.dumps(
        {"answer": "", "prompt_score": 3, "prompt_feedback": "", "penalty_applied": False}
    )
    result = process_model_response(
        raw, conv, message_id="m2", tokens_used=0, code_changed=False
    )
    assert result["answer"] == EMPTY_ANSWER_FALLBACK_PL


def test_message_response_accepts_score_up_to_10() -> None:
    from app.api.schemas.responses import MessageResponse

    msg = MessageResponse(
        answer="ok",
        prompt_score=10,
        prompt_feedback="excellent",
        tokens_used=1,
        debug_info={
            "is_frustrated": False,
            "avg_score": 8.5,
            "code_changed": False,
        },
    )
    assert msg.prompt_score == 10
    assert msg.debug_info is not None
    assert msg.debug_info.avg_score == 8.5


def test_truncated_json_extracts_partial_answer_not_raw_blob() -> None:
    from app.application.response_pipeline import parse_model_json, process_model_response
    from app.domain.conversation import Conversation
    from app.domain.sensei import SenseiConfig

    truncated = '{"answer": "Cześć! Jak mogę pomóc z kontrolerem REST?, "prompt_score": 3'
    parsed = parse_model_json(truncated, "pl")
    assert not parsed["answer"].lstrip().startswith("{")
    assert parsed["answer"].startswith("Cześć!")

    conv = Conversation(
        problem="lab",
        config=SenseiConfig.model_validate(build_valid_config()),
    )
    result = process_model_response(
        truncated, conv, message_id="m3", tokens_used=5, code_changed=False
    )
    assert result["answer"].startswith("Cześć!")
    assert "{" not in result["answer"][:3]


def test_process_strips_json_blob_answer() -> None:
    from app.application.response_pipeline import process_model_response
    from app.domain.conversation import Conversation
    from app.domain.sensei import SenseiConfig

    conv = Conversation(
        problem="lab",
        config=SenseiConfig.model_validate(build_valid_config()),
    )
    # Simulate parse returning whole object string as answer somehow via step-1 success
    # with nested misuse — feed truncated blob that falls through to sanitize.
    blob = '{"answer": "Tylko tekst dla studenta", "prompt_score": 5, "prompt_feedback": "ok"}'
    # Force sanitize path: valid JSON parses fine; also test raw-looking answer field
    result = process_model_response(
        blob, conv, message_id="m4", tokens_used=1, code_changed=False
    )
    assert result["answer"] == "Tylko tekst dla studenta"


def test_is_structured_output_unsupported() -> None:
    from app.application.llm_errors import is_structured_output_unsupported

    assert is_structured_output_unsupported(
        Exception(
            "model: inclusionai/ling-3.0-flash-sante does not support feature: structured-outputs"
        )
    )
    assert is_structured_output_unsupported(
        Exception("response_format is unsupported for this model")
    )
    assert not is_structured_output_unsupported(Exception("rate limit exceeded"))
