"""Live scenarios S10–S20, S24 — HTTP contract / session ops."""

from __future__ import annotations

import httpx

from tests.live.helpers import (
    ScenarioResult,
    ask,
    ask_stream,
    base_config,
    print_turn,
    skip_if_provider_429,
    start_conversation,
)


async def scenario_10_health_metrics(client: httpx.AsyncClient) -> ScenarioResult:
    print("\n=== S10: Health i metrics ===")
    h = await client.get("/health")
    m = await client.get("/metrics")
    ok = h.status_code == 200 and m.status_code == 200
    hj, mj = h.json(), m.json()
    passed = ok and hj.get("status") == "ok" and "requests_total" in mj
    return ScenarioResult(
        10,
        "Health i metrics",
        passed,
        f"health={h.status_code}, metrics={m.status_code}, keys_ok={passed}",
    )


async def scenario_11_session_contract(client: httpx.AsyncClient) -> ScenarioResult:
    print("\n=== S11: GET/DELETE/events/restrictions ===")
    conv_id = await start_conversation(client, config=base_config())
    await ask(client, conv_id, "Co to jest JSON?", code="class T {}")
    st = await client.get(f"/conversations/{conv_id}")
    hist = await client.get(f"/conversations/{conv_id}/messages")
    restr = await client.get(f"/conversations/{conv_id}/restrictions")
    ev = await client.post(
        f"/conversations/{conv_id}/events",
        json={"type": "copy_blocked", "meta": {"from": "test"}},
    )
    deleted = await client.delete(f"/conversations/{conv_id}")
    gone = await client.get(f"/conversations/{conv_id}")
    hist_body = hist.json() if hist.status_code == 200 else {}
    n_msgs = len(hist_body.get("messages", []) or [])
    passed = (
        st.status_code == 200
        and hist.status_code == 200
        and isinstance(hist_body.get("messages"), list)
        and restr.status_code == 200
        and ev.status_code == 200
        and deleted.status_code == 200
        and gone.status_code == 404
        and n_msgs >= 2
    )
    return ScenarioResult(
        11,
        "GET/DELETE/events/restrictions",
        passed,
        (
            f"st={st.status_code}, hist={hist.status_code}, restr={restr.status_code}, "
            f"ev={ev.status_code}, del={deleted.status_code}, gone={gone.status_code}, "
            f"n_msgs={n_msgs}"
        ),
    )


async def scenario_12_prelab_gate(client: httpx.AsyncClient) -> ScenarioResult:
    print("\n=== S12: Pre-lab gate ===")
    cfg = base_config()
    cfg["preLab"] = {
        "enabled": True,
        "questions": [
            {
                "id": "q1",
                "prompt": "Co to REST?",
                "expected_keywords": ["http", "api", "rest"],
            }
        ],
    }
    conv_id = await start_conversation(client, config=cfg)
    blocked = await client.post(
        f"/conversations/{conv_id}/messages",
        json={
            "question": "Czesc",
            "code_context": {
                "current_file_name": "A.java",
                "current_code": "class A {}",
                "error_logs": "",
            },
        },
    )
    submit = await client.post(
        f"/conversations/{conv_id}/prelab",
        json={"answers": [{"id": "q1", "answer": "To API HTTP REST"}]},
    )
    after = await client.post(
        f"/conversations/{conv_id}/messages",
        json={
            "question": "Co to jest endpoint?",
            "code_context": {
                "current_file_name": "A.java",
                "current_code": "class A {}",
                "error_logs": "",
            },
        },
    )
    passed = (
        blocked.status_code == 403
        and submit.status_code == 200
        and submit.json().get("passed") is True
        and after.status_code == 200
    )
    return ScenarioResult(
        12,
        "Pre-lab gate",
        passed,
        f"blocked={blocked.status_code}, submit_passed={submit.json().get('passed')}, after={after.status_code}",
    )


async def scenario_13_validate_config(client: httpx.AsyncClient) -> ScenarioResult:
    print("\n=== S13: Validate config ===")
    good = await client.post("/validate-config", json={"config": base_config()})
    bad = await client.post(
        "/validate-config",
        json={"config": {"language": "pl"}},
    )
    passed = (
        good.status_code == 200
        and good.json().get("valid") is True
        and bad.status_code == 200
        and bad.json().get("valid") is False
    )
    return ScenarioResult(
        13,
        "Validate config",
        passed,
        f"good_valid={good.json().get('valid')}, bad_valid={bad.json().get('valid')}",
    )


async def scenario_14_prometheus_request_id(client: httpx.AsyncClient) -> ScenarioResult:
    print("\n=== S14: Prometheus + request_id ===")
    h = await client.get("/health", headers={"X-Request-Id": "suite-req-14"})
    p = await client.get("/metrics/prometheus")
    rid = h.headers.get("x-request-id") or h.headers.get("X-Request-Id")
    passed = (
        h.status_code == 200
        and p.status_code == 200
        and "pja_sensei_requests_total" in p.text
        and rid == "suite-req-14"
    )
    return ScenarioResult(
        14,
        "Prometheus + request_id",
        passed,
        f"health={h.status_code}, prom={p.status_code}, rid={rid}",
    )


async def scenario_15_export_soft_delete(client: httpx.AsyncClient) -> ScenarioResult:
    print("\n=== S15: Export + soft DELETE ===")
    conv_id = await start_conversation(client, config=base_config())
    await ask(client, conv_id, "Co to REST?", code="class T {}")
    exp = await client.get(f"/conversations/{conv_id}/export")
    deleted = await client.delete(f"/conversations/{conv_id}")
    gone = await client.get(f"/conversations/{conv_id}")
    body = deleted.json() if deleted.status_code == 200 else {}
    passed = (
        exp.status_code == 200
        and isinstance(exp.json().get("messages"), list)
        and len(exp.json().get("messages") or []) >= 2
        and deleted.status_code == 200
        and gone.status_code == 404
        and body.get("status") == "deleted"
    )
    return ScenarioResult(
        15,
        "Export + soft DELETE",
        passed,
        f"export={exp.status_code}, del={deleted.status_code}, has_summary={bool(body.get('summary'))}",
    )


async def scenario_16_live_stream_tokens(client: httpx.AsyncClient) -> ScenarioResult:
    print("\n=== S16: Live stream tokens ===")
    conv_id = await start_conversation(client, config=base_config())
    elapsed, data, stats = await ask_stream(
        client, conv_id, "Co to jest klasa w Javie? Krótko.", code="class A {}"
    )
    print_turn("S16 Stream", elapsed, data)
    if skip := skip_if_provider_429(16, "Live stream tokens", data):
        return skip
    answer = str(data.get("answer") or "").strip()
    passed = (
        stats.get("token_events", 0) >= 1
        and stats.get("final_events", 0) >= 1
        and bool(answer)
    )
    return ScenarioResult(
        16,
        "Live stream tokens",
        passed,
        f"tokens={stats.get('token_events')}, finals={stats.get('final_events')}, answer={bool(answer)}",
    )


async def scenario_17_idempotency(client: httpx.AsyncClient) -> ScenarioResult:
    print("\n=== S17: Idempotency client_message_id ===")
    conv_id = await start_conversation(client, config=base_config())
    cid = "suite-idem-17"
    _, d1, s1 = await ask(
        client,
        conv_id,
        "Co to jest zmienna?",
        code="class A {}",
        client_message_id=cid,
    )
    _, d2, s2 = await ask(
        client,
        conv_id,
        "Co to jest zmienna?",
        code="class A {}",
        client_message_id=cid,
    )
    passed = (
        s1 == 200
        and s2 == 200
        and d1.get("message_id")
        and d1.get("message_id") == d2.get("message_id")
    )
    return ScenarioResult(
        17,
        "Idempotency client_message_id",
        passed,
        f"id1={d1.get('message_id')}, id2={d2.get('message_id')}, cached2={d2.get('is_cached')}",
    )


async def scenario_18_rich_code_context(client: httpx.AsyncClient) -> ScenarioResult:
    print("\n=== S18: Rich CodeContext ===")
    conv_id = await start_conversation(client, config=base_config(mode="debug"))
    ctx = {
        "current_file_name": "MyController.java",
        "current_code": "public class MyController {}",
        "workspace_root": "/lab/demo",
        "selection": {
            "start_line": 1,
            "end_line": 1,
            "text": "public class MyController {}",
        },
        "diagnostics": [
            {
                "severity": "error",
                "message": "cannot find symbol RestController",
                "line": 1,
                "file": "MyController.java",
            }
        ],
        "open_files": [
            {"path": "pom.xml", "content": "<project></project>", "language": "xml"}
        ],
        "error_logs": "404",
    }
    elapsed, data, status = await ask(
        client,
        conv_id,
        "Dlaczego mam błąd kompilacji przy kontrolerze?",
        code_context=ctx,
    )
    print_turn("S18 Rich context", elapsed, data)
    if skip := skip_if_provider_429(18, "Rich CodeContext", data):
        return skip
    passed = status == 200 and bool(str(data.get("answer") or "").strip())
    return ScenarioResult(
        18,
        "Rich CodeContext",
        passed,
        f"status={status}, answer_len={len(str(data.get('answer') or ''))}",
    )


async def scenario_19_checkpoints(client: httpx.AsyncClient) -> ScenarioResult:
    print("\n=== S19: Checkpoints + session goals ===")
    cfg = base_config(
        goals=["Utwórz @RestController", "Zwróć JSON"],
        checkpoints=[
            {
                "id": "cp1",
                "after_goal": "Utwórz @RestController",
                "hint": "Odblokuj testy",
            }
        ],
    )
    conv_id = await start_conversation(client, config=cfg)
    await ask(client, conv_id, "Jak oznaczyć klasę jako kontroler REST?", code="class C {}")
    cps = await client.get(f"/conversations/{conv_id}/checkpoints")
    state = await client.get(f"/conversations/{conv_id}")
    passed = (
        cps.status_code == 200
        and isinstance(cps.json().get("checkpoints"), list)
        and len(cps.json().get("checkpoints") or []) >= 1
        and state.status_code == 200
        and isinstance(state.json().get("goals"), list)
        and len(state.json().get("goals") or []) >= 2
    )
    return ScenarioResult(
        19,
        "Checkpoints + session goals",
        passed,
        f"cps={cps.status_code}, state={state.status_code}, "
        f"n_cps={len(cps.json().get('checkpoints') or [])}, "
        f"n_goals={len(state.json().get('goals') or [])}",
    )


async def scenario_20_restrictions(client: httpx.AsyncClient) -> ScenarioResult:
    print("\n=== S20: Restrictions endpoint ===")
    conv_id = await start_conversation(
        client, config=base_config(require_file_context=True)
    )
    res = await client.get(f"/conversations/{conv_id}/restrictions")
    body = res.json() if res.status_code == 200 else {}
    passed = (
        res.status_code == 200
        and body.get("requireFileContextForChat") is True
        and "prelab_required" in body
        and "disableCopyFromChat" in body
    )
    return ScenarioResult(
        20,
        "Restrictions endpoint",
        passed,
        f"status={res.status_code}, require_file={body.get('requireFileContextForChat')}",
    )


async def scenario_24_unknown_conversation(client: httpx.AsyncClient) -> ScenarioResult:
    print("\n=== S24: Unknown conversation 404 ===")
    missing = "00000000-0000-0000-0000-000000000000"
    st = await client.get(f"/conversations/{missing}")
    msg = await client.post(
        f"/conversations/{missing}/messages",
        json={
            "question": "ping",
            "code_context": {
                "current_file_name": "A.java",
                "current_code": "class A {}",
                "error_logs": "",
            },
        },
    )
    passed = st.status_code == 404 and msg.status_code == 404
    return ScenarioResult(
        24,
        "Unknown conversation 404",
        passed,
        f"get={st.status_code}, messages={msg.status_code}",
    )
