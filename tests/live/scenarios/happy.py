"""Live: happy-path lab session — PASS tylko przy celu labu 10/10."""

from __future__ import annotations

import httpx

from tests.live.helpers import (
    ScenarioResult,
    base_config,
    msg_body,
    print_turn,
    skip_if_provider_429,
    start_conversation,
)

GOALS = ["Utwórz @RestController", "Zwróć JSON"]


def lab_score(goal_progress: list | None) -> int:
    if not goal_progress:
        return 0
    done = sum(1 for g in goal_progress if isinstance(g, dict) and g.get("status") == "done")
    return round(10 * done / len(goal_progress))


async def full_lab(client: httpx.AsyncClient) -> ScenarioResult:
    name = "Student przechodzi lab od startu do końca"
    cfg = base_config(
        learningContext={"goals": GOALS, "referenceMaterials": []},
        checkpoints=[
            {
                "id": "cp1",
                "afterGoal": "Utwórz @RestController",
                "hint": "Dodaj endpoint zwracający JSON użytkownika",
            }
        ],
        preLab={
            "enabled": True,
            "maxAttempts": 3,
            "hintAfterFail": "HTTP",
            "questions": [
                {
                    "id": "q1",
                    "prompt": "Na czym opiera się REST?",
                    "expectedKeywords": ["http"],
                }
            ],
        },
    )
    cid = await start_conversation(client, config=cfg)

    fail = await client.post(
        f"/conversations/{cid}/prelab",
        json={"answers": [{"id": "q1", "answer": "nie wiem"}]},
    )
    print_turn("prelab fail", fail.status_code, fail.json() if fail.status_code == 200 else None)
    if fail.status_code != 200 or fail.json().get("passed") is not False:
        return ScenarioResult(1, name, False, f"prelab fail unexpected: {fail.text}")

    blocked = await client.post(
        f"/conversations/{cid}/messages", json=msg_body("pomóż")
    )
    print_turn("chat blocked", blocked.status_code, blocked.json() if blocked.content else None)
    if blocked.status_code != 403:
        return ScenarioResult(1, name, False, f"expected 403 before pass, got {blocked.status_code}")

    passed = await client.post(
        f"/conversations/{cid}/prelab",
        json={"answers": [{"id": "q1", "answer": "REST opiera się na HTTP"}]},
    )
    print_turn("prelab pass", passed.status_code, passed.json() if passed.status_code == 200 else None)
    if passed.status_code != 200 or not passed.json().get("passed"):
        return ScenarioResult(1, name, False, f"prelab pass failed: {passed.text}")

    turns = [
        (
            "teoria",
            "Co to jest REST i po co nam @RestController w Springu?",
            "",
        ),
        (
            "kontroler",
            "Dodałem @RestController na klasie UserController. Co dalej, żeby zwrócić użytkownika?",
            "@RestController\n@RequestMapping(\"/api/users\")\npublic class UserController {\n}",
        ),
        (
            "json",
            "Mam @GetMapping i zwracam User przez ResponseEntity jako JSON. Czy cele labu są domknięte?",
            "@RestController\npublic class UserController {\n  @GetMapping(\"/{id}\")\n"
            "  public ResponseEntity<User> get(@PathVariable Long id) {\n"
            "    return ResponseEntity.ok(user);\n  }\n}",
        ),
    ]

    last_body: dict | None = None
    for label, question, code in turns:
        chat = await client.post(
            f"/conversations/{cid}/messages",
            json=msg_body(question, code=code),
        )
        last_body = chat.json() if chat.content else None
        print_turn(label, chat.status_code, last_body if isinstance(last_body, dict) else None)
        if skip := skip_if_provider_429(1, name, last_body):
            return skip
        if chat.status_code != 200:
            return ScenarioResult(1, name, False, f"{label} → {chat.status_code}")

    state = await client.get(f"/conversations/{cid}")
    state_body = state.json() if state.status_code == 200 else {}
    print_turn("session state", state.status_code, state_body if isinstance(state_body, dict) else None)
    gp = state_body.get("goal_progress") or (last_body or {}).get("goal_progress") or []
    score = lab_score(gp)
    if score < 10:
        return ScenarioResult(
            1,
            name,
            False,
            f"cel labu {score}/10 — oczekiwane 10/10 (cele: {gp})",
        )

    summary = await client.post(f"/conversations/{cid}/summary")
    print_turn("summary", summary.status_code, summary.json() if summary.status_code == 200 else None)
    deleted = await client.delete(f"/conversations/{cid}")
    print_turn("delete", deleted.status_code, deleted.json() if deleted.content else None)
    ok = summary.status_code == 200 and deleted.status_code == 200
    return ScenarioResult(
        1,
        name,
        ok,
        f"cel=10/10 summary={summary.status_code} delete={deleted.status_code}",
    )
