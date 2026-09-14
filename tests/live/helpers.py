"""Shared helpers for live HTTP scenarios."""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from typing import Any

import httpx

from app.application.response_pipeline import PROVIDER_RATE_LIMITED_ID

API_BASE = "http://localhost:8000"
DEFAULT_PROBLEM = "Napisz kontroler REST zwracający dane użytkownika w JSON."
TARGET_VAR = "wik_jest_spoko"
DUMMY_TURNS = 9
SPRING_RAG_URL = "https://spring.io/guides/gs/rest-service/"
BROKEN_RAG_URL = "http://httpstat.us/200?sleep=6000"


@dataclass
class ScenarioResult:
    """Wynik jednego scenariusza live: numer, nazwa, pass/fail/skip, opis."""

    number: int
    name: str
    passed: bool
    details: str
    skipped: bool = False


def is_provider_rate_limited(body: dict[str, Any] | None) -> bool:
    """True when chat/stream body is the provider-429 stub, not a mentor answer."""
    if not isinstance(body, dict):
        return False
    if body.get("message_id") == PROVIDER_RATE_LIMITED_ID:
        return True
    feedback = str(body.get("prompt_feedback") or "").lower()
    return "429" in feedback


def skip_provider_429(
    number: int, name: str, *, extra: str = ""
) -> ScenarioResult:
    """Live result: do not grade pedagogy when the provider rate-limited us."""
    details = "provider 429"
    if extra:
        details = f"{details}; {extra}"
    return ScenarioResult(number, name, True, details, skipped=True)


def skip_if_provider_429(
    number: int, name: str, *bodies: Any, extra: str = ""
) -> ScenarioResult | None:
    """Return a SKIP result if any body is the 429 stub; otherwise None."""
    if any(is_provider_rate_limited(b) for b in bodies):
        return skip_provider_429(number, name, extra=extra)
    return None


def base_config(
    *,
    require_file_context: bool = False,
    reference_materials: list[dict] | None = None,
    goals: list[str] | None = None,
    mode: str = "debug",
    checkpoints: list[dict] | None = None,
    max_tokens_per_session: int | None = None,
    prelab: dict | None = None,
) -> dict:
    """Minimalny SenseiConfig (camelCase) dla startu sesji w scenariuszach live."""
    cfg: dict[str, Any] = {
        "learningContext": {
            "goals": goals or ["Test scenariuszy"],
            "referenceMaterials": reference_materials or [],
        },
        "agentBehavior": {
            "persona": {"role": "Sokratyczny Nauczyciel", "tone": "Cierpliwy"},
            "strictRules": ["Nie podawaj gotowego kodu."],
            "codeRevealFallback": (
                "Zauważyłem próbę wygenerowania gotowego kodu, co narusza zasady "
                "samodzielnej pracy. Zastanówmy się nad architekturą rozwiązania."
            ),
            "mode": mode,
        },
        "ideRestrictions": {"requireFileContextForChat": require_file_context},
        "language": "pl",
        "checkpoints": checkpoints or [],
    }
    if max_tokens_per_session is not None:
        cfg["maxTokensPerSession"] = max_tokens_per_session
    if prelab is not None:
        cfg["preLab"] = prelab
    return cfg


def print_turn(step_label: str, elapsed: float, res_json: dict) -> None:
    """Czytelny log jednej tury czatu (score, penalty, cache, debug)."""
    answer = str(res_json.get("answer", "")).strip()
    score = res_json.get("prompt_score", "Brak")
    feedback = res_json.get("prompt_feedback", "Brak")
    penalty = res_json.get("penalty_applied", False)
    is_cached = res_json.get("is_cached", False)
    tokens = res_json.get("tokens_used", 0)
    debug = res_json.get("debug_info", {}) or {}

    preview = answer if len(answer) <= 400 else answer[:400] + "..."
    print(f"\n--- [{step_label}] (Czas: {elapsed:.2f}s | Tokeny: {tokens})")
    print(f"  Odpowiedź: \"{preview}\"")
    print(f"  Prompt Score: {score}/10 | Feedback: {feedback}")
    print(f"  Penalty: {penalty} | Cached: {is_cached}")
    if debug:
        print(
            f"  Debug: Frustrated={debug.get('is_frustrated')}, "
            f"AvgScore={debug.get('avg_score')}, CodeChanged={debug.get('code_changed')}"
        )
    print("-" * 60)


async def start_conversation(
    client: httpx.AsyncClient,
    *,
    config: dict,
    problem: str = DEFAULT_PROBLEM,
) -> str:
    """POST /conversations i zwraca conversation_id."""
    res = await client.post(
        "/conversations",
        json={"problem_description": problem, "config": config},
    )
    res.raise_for_status()
    return res.json()["conversation_id"]


async def ask(
    client: httpx.AsyncClient,
    conv_id: str,
    question: str,
    *,
    file_name: str = "Test.java",
    code: str = "",
    error_logs: str = "",
    client_message_id: str | None = None,
    code_context: dict | None = None,
    raise_on_error: bool = True,
) -> tuple[float, dict[str, Any], int]:
    """POST sync message; zwraca (elapsed_s, body, status_code)."""
    payload: dict[str, Any] = {
        "question": question,
        "code_context": code_context
        or {
            "current_file_name": file_name,
            "current_code": code,
            "error_logs": error_logs,
        },
    }
    if client_message_id:
        payload["client_message_id"] = client_message_id
    t0 = time.perf_counter()
    res = await client.post(f"/conversations/{conv_id}/messages", json=payload)
    elapsed = time.perf_counter() - t0
    if raise_on_error:
        res.raise_for_status()
        return elapsed, res.json(), res.status_code
    try:
        body = res.json()
    except Exception:
        body = {"raw": res.text}
    return elapsed, body, res.status_code


async def ask_stream(
    client: httpx.AsyncClient,
    conv_id: str,
    question: str,
    *,
    file_name: str = "Test.java",
    code: str = "",
) -> tuple[float, dict[str, Any], dict[str, int]]:
    """POST stream NDJSON; zwraca (elapsed, final_event, liczniki typów zdarzeń)."""
    payload = {
        "question": question,
        "code_context": {
            "current_file_name": file_name,
            "current_code": code,
            "error_logs": "",
        },
    }
    t0 = time.perf_counter()
    async with client.stream(
        "POST", f"/conversations/{conv_id}/messages/stream", json=payload
    ) as res:
        content_type = res.headers.get("content-type", "")
        body = ""
        async for chunk in res.aiter_text():
            body += chunk
        elapsed = time.perf_counter() - t0
        if res.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"Stream failed: {res.status_code}",
                request=res.request,
                response=res,
            )

        stats = {"token_events": 0, "final_events": 0}
        if "application/json" in content_type and "ndjson" not in content_type:
            return elapsed, json.loads(body), stats

        final = None
        for line in body.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                evt = json.loads(line)
            except json.JSONDecodeError:
                continue
            if evt.get("type") == "token":
                stats["token_events"] += 1
            elif evt.get("type") == "final":
                stats["final_events"] += 1
                final = evt
            elif final is None and "answer" in evt:
                final = evt
        if final is None:
            raise ValueError(f"No final NDJSON event in stream body: {body[:200]}")
        return elapsed, final, stats


def _looks_like_full_controller_dump(answer: str) -> bool:
    has_class = bool(re.search(r"public\s+class\s+\w+", answer))
    has_mapping = "@GetMapping" in answer or "@RestController" in answer and "{" in answer
    code_lines = sum(
        1
        for line in answer.splitlines()
        if any(k in line for k in ("public ", "return ", "class ", "{", "};"))
    )
    return has_class and (has_mapping or code_lines >= 6)
