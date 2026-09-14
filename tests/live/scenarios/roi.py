"""Live scenarios S21–S23 + ROI edges S25+."""

from __future__ import annotations

import httpx

from app.core.config import MAX_REVEALS_PER_SESSION
from tests.live.helpers import (
    ScenarioResult,
    _looks_like_full_controller_dump,
    ask,
    ask_stream,
    base_config,
    is_provider_rate_limited,
    print_turn,
    skip_if_provider_429,
    skip_provider_429,
    start_conversation,
)


async def scenario_21_reveal_feedback_summary(
    client: httpx.AsyncClient,
) -> ScenarioResult:
    print("\n=== S21: Reveal + feedback + summary ===")
    conv_id = await start_conversation(client, config=base_config())
    _, data, _ = await ask(client, conv_id, "Co to jest HTTP?", code="class A {}")
    mid = data.get("message_id")
    # Without frustration, reveal should be 403 (endpoint wired)
    reveal = await client.post(
        f"/conversations/{conv_id}/hints/reveal",
        json={"focus": "start"},
    )
    fb = await client.post(
        f"/conversations/{conv_id}/messages/{mid}/feedback",
        json={"rating": 4, "comment": "ok"},
    )
    summary = await client.post(f"/conversations/{conv_id}/summary")
    passed = (
        reveal.status_code == 403
        and fb.status_code == 200
        and summary.status_code == 200
    )
    return ScenarioResult(
        21,
        "Reveal + feedback + summary",
        passed,
        f"reveal={reveal.status_code}, fb={fb.status_code}, summary={summary.status_code}",
    )


async def scenario_22_token_budget(client: httpx.AsyncClient) -> ScenarioResult:
    print("\n=== S22: Token budget 403 ===")
    conv_id = await start_conversation(
        client, config=base_config(max_tokens_per_session=1)
    )
    _, d1, s1 = await ask(
        client, conv_id, "Co to jest klasa?", code="class A {}", raise_on_error=False
    )
    if skip := skip_if_provider_429(22, "Token budget 403", d1):
        return skip
    _, d2, s2 = await ask(
        client,
        conv_id,
        "A co to jest metoda?",
        code="class A {}",
        raise_on_error=False,
    )
    # First call may succeed (budget checked before tokens added); second should 403
    passed = s1 == 200 and s2 == 403 and (
        d2.get("message_id") == "token_budget_exceeded"
        or "budget" in str(d2.get("prompt_feedback") or "").lower()
        or "token" in str(d2.get("detail") or "").lower()
    )
    return ScenarioResult(
        22,
        "Token budget 403",
        passed,
        f"s1={s1}, s2={s2}, mid2={d2.get('message_id')}",
    )


async def scenario_23_require_file_context(client: httpx.AsyncClient) -> ScenarioResult:
    print("\n=== S23: Missing file context gate ===")
    conv_id = await start_conversation(
        client, config=base_config(require_file_context=True)
    )
    _, data, status = await ask(
        client,
        conv_id,
        "Co tu jest nie tak?",
        code="   ",
        raise_on_error=False,
    )
    text = f"{data.get('answer', '')} {data.get('prompt_feedback', '')}".lower()
    passed = (
        status == 200
        and data.get("message_id") == "rejected"
        and data.get("tokens_used") == 0
        and ("plik" in text or "file" in text or "iderestrictions" in text)
    )
    return ScenarioResult(
        23,
        "Missing file context gate",
        passed,
        f"status={status}, mid={data.get('message_id')}, tokens={data.get('tokens_used')}",
    )


async def _drive_low_scores(
    client: httpx.AsyncClient, conv_id: str, *, turns: int = 4
) -> tuple[list[int], dict | None]:
    """Ask vague questions to accumulate low prompt scores for reveal gate.

    Returns (scores, rate_limited_body). If the provider 429-stubbed an LLM
    turn, stop early so callers can SKIP instead of FAIL the reveal gate.
    """
    scores: list[int] = []
    for i in range(turns):
        _, data, status = await ask(
            client,
            conv_id,
            "nie wiem" if i % 2 == 0 else "daj kod",
            code="class Broken {}",
            raise_on_error=False,
        )
        print_turn(f"low-score/{i+1}", 0.0, data if isinstance(data, dict) else {})
        if is_provider_rate_limited(data):
            return scores, data
        if status == 200 and data.get("prompt_score") is not None:
            scores.append(int(data["prompt_score"]))
    return scores, None



async def scenario_25_reveal_after_low_streak(
    client: httpx.AsyncClient,
) -> ScenarioResult:
    print("\n=== S25: Reveal after low streak ===")
    conv_id = await start_conversation(client, config=base_config())
    scores, limited = await _drive_low_scores(client, conv_id, turns=4)
    if limited:
        return skip_provider_429(25, "Reveal after low streak")
    reveal_payload = {
        "focus": "RestController",
        "code_context": {
            "current_file_name": "C.java",
            "current_code": "class C {}",
            "error_logs": "",
        },
    }
    reveal = await client.post(
        f"/conversations/{conv_id}/hints/reveal",
        json=reveal_payload,
    )
    if reveal.status_code == 403:
        extra, limited = await _drive_low_scores(client, conv_id, turns=2)
        if limited:
            return skip_provider_429(25, "Reveal after low streak")
        scores.extend(extra)
        reveal = await client.post(
            f"/conversations/{conv_id}/hints/reveal",
            json=reveal_payload,
        )
    if reveal.status_code != 200:
        return ScenarioResult(
            25,
            "Reveal after low streak",
            False,
            f"reveal still {reveal.status_code} after low-score turns "
            f"(scores={scores}); live LLM may not open gate",
        )
    body = reveal.json()
    hint = str(body.get("hint") or "")
    rem = body.get("reveals_remaining")
    decreased = rem is not None and int(rem) < MAX_REVEALS_PER_SESSION
    no_dump = not _looks_like_full_controller_dump(hint)
    passed = decreased and no_dump and bool(hint.strip())
    return ScenarioResult(
        25,
        "Reveal after low streak",
        passed,
        f"scores={scores}, reveal=200, rem={rem}, no_dump={no_dump}",
    )



async def scenario_26_reveal_quota_exhausted(
    client: httpx.AsyncClient,
) -> ScenarioResult:
    print("\n=== S26: Reveal quota exhausted ===")
    conv_id = await start_conversation(client, config=base_config())
    scores, limited = await _drive_low_scores(client, conv_id, turns=4)
    if limited:
        return skip_provider_429(26, "Reveal quota exhausted")
    oks = 0
    last_status = None
    for i in range(MAX_REVEALS_PER_SESSION + 1):
        r = await client.post(
            f"/conversations/{conv_id}/hints/reveal",
            json={"focus": f"step-{i}"},
        )
        last_status = r.status_code
        if r.status_code == 200:
            oks += 1
            if oks >= MAX_REVEALS_PER_SESSION:
                break
            continue
        if r.status_code == 403 and oks == 0:
            extra, limited = await _drive_low_scores(client, conv_id, turns=2)
            if limited:
                return skip_provider_429(26, "Reveal quota exhausted")
            scores.extend(extra)
            continue
        break
    if oks == 0:
        return ScenarioResult(
            26,
            "Reveal quota exhausted",
            False,
            f"could not unlock reveal (last={last_status}, scores={scores})",
        )
    while oks < MAX_REVEALS_PER_SESSION:
        r = await client.post(
            f"/conversations/{conv_id}/hints/reveal",
            json={"focus": f"quota-{oks}"},
        )
        last_status = r.status_code
        if r.status_code != 200:
            break
        oks += 1
    over = await client.post(
        f"/conversations/{conv_id}/hints/reveal",
        json={"focus": "overflow"},
    )
    passed = oks >= MAX_REVEALS_PER_SESSION and over.status_code == 403
    return ScenarioResult(
        26,
        "Reveal quota exhausted",
        passed,
        f"oks={oks}/{MAX_REVEALS_PER_SESSION}, last={last_status}, over={over.status_code}",
    )



async def scenario_27_next_checkpoint_coaching(
    client: httpx.AsyncClient,
) -> ScenarioResult:
    print("\n=== S27: next_checkpoint coaching ===")
    cfg = base_config(
        goals=["Utwórz @RestController", "Zwróć JSON"],
        checkpoints=[
            {
                "id": "cp-rest",
                "after_goal": "Utwórz @RestController",
                "hint": "Dodaj mapowanie HTTP",
            }
        ],
    )
    conv_id = await start_conversation(client, config=cfg)
    _, data, status = await ask(
        client,
        conv_id,
        "Oznaczyłem klasę adnotacją @RestController — co dalej?",
        code="@RestController\npublic class Demo {}",
    )
    if skip := skip_if_provider_429(27, "next_checkpoint coaching", data):
        return skip
    cps = await client.get(f"/conversations/{conv_id}/checkpoints")
    cp_body = cps.json() if cps.status_code == 200 else {}
    unlocked = any(
        c.get("unlocked") for c in (cp_body.get("checkpoints") or [])
    )
    has_next = bool(data.get("next_checkpoint"))
    has_step = bool(data.get("suggested_next_step"))
    passed = status == 200 and (has_next or unlocked or has_step)
    return ScenarioResult(
        27,
        "next_checkpoint coaching",
        passed,
        f"status={status}, next={has_next}, unlocked={unlocked}, step={has_step}",
    )



async def scenario_28_rich_summary_shape(
    client: httpx.AsyncClient,
) -> ScenarioResult:
    print("\n=== S28: Rich summary shape ===")
    conv_id = await start_conversation(
        client,
        config=base_config(goals=["REST controller", "JSON"]),
    )
    _, data, _ = await ask(client, conv_id, "Co to jest REST?", code="class A {}")
    mid = data.get("message_id")
    await client.post(
        f"/conversations/{conv_id}/messages/{mid}/feedback",
        json={"rating": 4, "comment": "ok"},
    )
    summary = await client.post(f"/conversations/{conv_id}/summary")
    body = summary.json() if summary.status_code == 200 else {}
    legacy = "mastery_score" in body or "professors_summary" in body
    rich = any(
        k in body
        for k in (
            "goal_mastery",
            "reveal_usage",
            "ide_events",
            "ide_events_structured",
            "reveal_count",
            "goals",
        )
    )
    passed = summary.status_code == 200 and legacy and rich
    return ScenarioResult(
        28,
        "Rich summary shape",
        passed,
        f"status={summary.status_code}, legacy={legacy}, rich={rich}",
    )



async def scenario_29_prelab_fail_then_pass(
    client: httpx.AsyncClient,
) -> ScenarioResult:
    print("\n=== S29: Prelab fail then pass ===")
    cfg = base_config(
        prelab={
            "enabled": True,
            "questions": [
                {
                    "id": "q1",
                    "prompt": "Adnotacja REST controller?",
                    "expected_keywords": ["RestController"],
                }
            ],
            "max_attempts": 5,
            "hint_after_fail": "Szukaj RestController",
        }
    )
    conv_id = await start_conversation(client, config=cfg)
    fail = await client.post(
        f"/conversations/{conv_id}/prelab",
        json={"answers": [{"id": "q1", "answer": "nie wiem"}]},
    )
    ok = await client.post(
        f"/conversations/{conv_id}/prelab",
        json={"answers": [{"id": "q1", "answer": "Używam @RestController"}]},
    )
    _, _, chat_status = await ask(
        client, conv_id, "Jak zacząć?", code="class A {}", raise_on_error=False
    )
    passed = (
        fail.status_code == 200
        and fail.json().get("passed") is False
        and ok.status_code == 200
        and ok.json().get("passed") is True
        and chat_status == 200
    )
    return ScenarioResult(
        29,
        "Prelab fail then pass",
        passed,
        f"fail_passed={fail.json().get('passed')}, ok_passed={ok.json().get('passed')}, chat={chat_status}",
    )



async def scenario_30_mode_theory(
    client: httpx.AsyncClient,
) -> ScenarioResult:
    print("\n=== S30: Mode theory session ===")
    conv_id = await start_conversation(client, config=base_config(mode="theory"))
    _, data, status = await ask(
        client,
        conv_id,
        "Czym różni się klasa od obiektu w Javie?",
        code="",
    )
    if skip := skip_if_provider_429(30, "Mode theory session", data):
        return skip
    score = data.get("prompt_score")
    passed = status == 200 and score is not None and int(score) >= 1
    state = await client.get(f"/conversations/{conv_id}")
    mode_ok = state.status_code == 200 and state.json().get("mode") == "theory"
    return ScenarioResult(
        30,
        "Mode theory session",
        passed and mode_ok,
        f"status={status}, score={score}, mode={state.json().get('mode') if state.status_code == 200 else None}",
    )



async def scenario_31_pdf_rag_material(
    client: httpx.AsyncClient,
) -> ScenarioResult:
    print("\n=== S31: PDF RAG material ===")
    pdf_url = (
        "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"
    )
    cfg = base_config(
        reference_materials=[
            {"type": "pdf", "title": "Dummy PDF", "url": pdf_url},
        ]
    )
    start = await client.post(
        "/conversations",
        json={"problem_description": "PDF lab", "config": cfg},
    )
    if start.status_code != 200:
        return ScenarioResult(
            31, "PDF RAG material", False, f"start={start.status_code}"
        )
    conv_id = start.json()["conversation_id"]
    _, data, status = await ask(
        client, conv_id, "Co jest w materiałach?", code="class A {}", raise_on_error=False
    )
    if skip := skip_if_provider_429(31, "PDF RAG material", data):
        return skip
    passed = status == 200 and bool(data.get("answer") or data.get("message_id"))
    return ScenarioResult(
        31,
        "PDF RAG material",
        passed,
        f"start=200, msg={status}, sources={len(data.get('sources') or [])}",
    )



async def scenario_32_ide_events_in_summary(
    client: httpx.AsyncClient,
) -> ScenarioResult:
    print("\n=== S32: IDE events + summary ===")
    conv_id = await start_conversation(client, config=base_config())
    await ask(client, conv_id, "Start", code="class A {}")
    for evt in ("copy_blocked", "paste_attempt"):
        await client.post(
            f"/conversations/{conv_id}/events",
            json={"type": evt, "meta": {"source": "live-suite"}},
        )
    summary = await client.post(f"/conversations/{conv_id}/summary")
    export = await client.get(f"/conversations/{conv_id}/export")
    sbody = summary.json() if summary.status_code == 200 else {}
    ebody = export.json() if export.status_code == 200 else {}
    structured = sbody.get("ide_events_structured") or sbody.get("ide_events") or {}
    export_events = ebody.get("ide_events") or []
    evidence = (
        (isinstance(structured, dict) and (
            structured.get("copy_blocked", 0) >= 1
            or structured.get("paste_attempt", 0) >= 1
        ))
        or any(
            e.get("type") in ("copy_blocked", "paste_attempt")
            for e in export_events
            if isinstance(e, dict)
        )
    )
    passed = summary.status_code == 200 and evidence
    return ScenarioResult(
        32,
        "IDE events + summary",
        passed,
        f"summary={summary.status_code}, evidence={evidence}",
    )



async def scenario_33_sync_stream_parity(
    client: httpx.AsyncClient,
) -> ScenarioResult:
    print("\n=== S33: Sync vs stream parity ===")
    conv_sync = await start_conversation(client, config=base_config())
    _, sync_data, sync_status = await ask(
        client, conv_sync, "Co to jest klasa?", code="class A {}"
    )
    if skip := skip_if_provider_429(33, "Sync vs stream parity", sync_data):
        return skip
    conv_stream = await start_conversation(client, config=base_config())
    try:
        _, stream_data, stats = await ask_stream(
            client, conv_stream, "Co to jest metoda?", code="class A {}"
        )
        if skip := skip_if_provider_429(33, "Sync vs stream parity", stream_data):
            return skip
        stream_ok = (
            stats.get("token_events", 0) >= 1
            and stats.get("final_events", 0) >= 1
            and bool(str(stream_data.get("answer") or "").strip())
        )
        stream_detail = (
            f"tokens={stats.get('token_events')}, finals={stats.get('final_events')}"
        )
    except Exception as exc:
        stream_ok = False
        stream_detail = f"error={exc}"
    sync_ok = (
        sync_status == 200
        and bool(sync_data.get("message_id"))
        and sync_data.get("prompt_score") is not None
    )
    passed = sync_ok and stream_ok
    return ScenarioResult(
        33,
        "Sync vs stream parity",
        passed,
        f"sync={sync_status}, mid={sync_data.get('message_id')}, "
        f"score={sync_data.get('prompt_score')}, {stream_detail}",
    )
