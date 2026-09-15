"""Shared helpers for live HTTP narrative scenarios."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from app.application.response_pipeline import PROVIDER_RATE_LIMITED_ID

API_BASE = "http://127.0.0.1:8000"
DEFAULT_PROBLEM = "Napisz kontroler REST zwracający dane użytkownika w JSON."


@dataclass
class ScenarioResult:
    number: int
    name: str
    passed: bool
    details: str
    skipped: bool = False


def is_provider_rate_limited(body: dict[str, Any] | None) -> bool:
    if not isinstance(body, dict):
        return False
    if body.get("message_id") == PROVIDER_RATE_LIMITED_ID:
        return True
    feedback = str(body.get("prompt_feedback") or "").lower()
    return "429" in feedback


def skip_if_provider_429(
    number: int, name: str, *bodies: Any, extra: str = ""
) -> ScenarioResult | None:
    if any(is_provider_rate_limited(b) for b in bodies):
        details = "provider 429"
        if extra:
            details = f"{details}; {extra}"
        return ScenarioResult(number, name, True, details, skipped=True)
    return None


def base_config(**overrides: Any) -> dict[str, Any]:
    cfg: dict[str, Any] = {
        "learningContext": {
            "goals": ["Utwórz @RestController", "Zwróć JSON"],
            "referenceMaterials": [],
        },
        "agentBehavior": {
            "persona": {"role": "mentor", "tone": "calm"},
            "strictRules": ["Nie podawaj gotowego kodu."],
            "mode": "debug",
        },
        "language": "pl",
    }
    cfg.update(overrides)
    return cfg


def msg_body(question: str, *, code: str = "class A {}") -> dict[str, Any]:
    return {
        "question": question,
        "code_context": {
            "current_file_name": "A.java",
            "current_code": code,
            "error_logs": "",
        },
    }


async def start_conversation(
    client: httpx.AsyncClient,
    *,
    config: dict[str, Any] | None = None,
    problem: str = DEFAULT_PROBLEM,
) -> str:
    res = await client.post(
        "/conversations",
        json={"problem_description": problem, "config": config or base_config()},
    )
    res.raise_for_status()
    return res.json()["conversation_id"]


def print_turn(step_label: str, status: int, body: dict[str, Any] | None = None) -> None:
    """Log jednej odpowiedzi API (CLI live) — status + skrócona treść."""
    print(f"\n--- [{step_label}] HTTP {status}")
    if not isinstance(body, dict):
        if body is not None:
            print(f"  body: {str(body)[:300]}")
        print("-" * 60)
        return
    if mid := body.get("message_id"):
        print(f"  message_id: {mid}")
    if "prompt_score" in body:
        print(f"  prompt_score: {body.get('prompt_score')}")
    if "passed" in body:
        print(f"  passed: {body.get('passed')}")
    answer = str(
        body.get("answer") or body.get("hint") or body.get("professors_summary") or ""
    ).strip()
    if answer:
        preview = answer if len(answer) <= 320 else answer[:320] + "..."
        print(f"  answer: {preview!r}")
    if detail := body.get("detail"):
        print(f"  detail: {detail}")
    print("-" * 60)
