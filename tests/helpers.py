"""Shared helpers for offline narrative scenarios."""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from tests.conftest import build_valid_config

DEFAULT_PROBLEM = "Napisz kontroler REST zwracający dane użytkownika w JSON."


def msg_body(
    question: str = "Jak zacząć?",
    *,
    code: str = "class A {}",
    file_name: str = "A.java",
    client_message_id: str | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "question": question,
        "code_context": {
            "current_file_name": file_name,
            "current_code": code,
            "error_logs": "",
        },
    }
    if client_message_id is not None:
        body["client_message_id"] = client_message_id
    return body


def start_session(
    client: TestClient,
    *,
    problem: str = DEFAULT_PROBLEM,
    **cfg_overrides: Any,
) -> str:
    res = client.post(
        "/conversations",
        json={"problem_description": problem, "config": build_valid_config(**cfg_overrides)},
    )
    assert res.status_code == 200, res.text
    return res.json()["conversation_id"]


def happy_lab_config(**extra: Any) -> dict[str, Any]:
    """Config for a full lab: prelab + goals + one checkpoint."""
    cfg = build_valid_config(
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
        preLab={
            "enabled": True,
            "maxAttempts": 3,
            "hintAfterFail": "Pomyśl o HTTP",
            "questions": [
                {
                    "id": "q1",
                    "prompt": "Na czym opiera się REST?",
                    "expectedKeywords": ["http"],
                }
            ],
        },
        evaluationCriteria=["Clarity", "Progress"],
    )
    cfg.update(extra)
    return cfg


def pass_prelab(client: TestClient, cid: str, *, answer: str = "REST opiera się na HTTP") -> None:
    res = client.post(
        f"/conversations/{cid}/prelab",
        json={"answers": [{"id": "q1", "answer": answer}]},
    )
    assert res.status_code == 200, res.text
    assert res.json()["passed"] is True


def assert_message_shape(body: dict[str, Any]) -> None:
    for key in ("message_id", "answer", "prompt_score", "tokens_used"):
        assert key in body
    assert isinstance(body["answer"], str)
    assert body["answer"].strip()
