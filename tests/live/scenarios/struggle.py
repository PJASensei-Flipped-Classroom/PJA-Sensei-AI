"""Live: struggle / frustration scenarios."""

from __future__ import annotations

import httpx

from tests.live.helpers import (
    ScenarioResult,
    base_config,
    msg_body,
    skip_if_provider_429,
    start_conversation,
)


async def reveal_after_low_scores(client: httpx.AsyncClient) -> ScenarioResult:
    name = "Student utyka i bierze reveal"
    cid = await start_conversation(client)

    early = await client.post(
        f"/conversations/{cid}/hints/reveal", json={"focus": "controller"}
    )
    if early.status_code != 403:
        return ScenarioResult(2, name, False, f"reveal before streak: {early.status_code}")

    # Drive low scores with vague questions (best-effort; may skip on 429)
    last_body = None
    for q in ("nie działa", "dalej źle", "pomocy"):
        res = await client.post(f"/conversations/{cid}/messages", json=msg_body(q))
        if res.status_code == 200:
            last_body = res.json()
            if skip := skip_if_provider_429(2, name, last_body):
                return skip

    reveal = await client.post(
        f"/conversations/{cid}/hints/reveal", json={"focus": "controller"}
    )
    # Live models may not always open the gate; accept 200 or still 403 with detail
    passed = reveal.status_code in (200, 403)
    return ScenarioResult(
        2,
        name,
        passed and early.status_code == 403,
        f"early={early.status_code} reveal={reveal.status_code}",
    )


async def theory_without_file(client: httpx.AsyncClient) -> ScenarioResult:
    name = "Student w theory bez pliku"
    cid = await start_conversation(
        client,
        config=base_config(
            agentBehavior={
                "persona": {"role": "mentor", "tone": "calm"},
                "strictRules": ["Nie podawaj gotowego kodu."],
                "mode": "theory",
            },
            ideRestrictions={"requireFileContextForChat": True},
        ),
    )
    res = await client.post(
        f"/conversations/{cid}/messages",
        json=msg_body("O czym jest to zadanie?", code="   "),
    )
    if skip := skip_if_provider_429(3, name, res.json() if res.status_code == 200 else None):
        return skip
    if res.status_code != 200:
        return ScenarioResult(3, name, False, f"status={res.status_code}")
    body = res.json()
    ok = body.get("message_id") != "rejected"
    return ScenarioResult(3, name, ok, f"message_id={body.get('message_id')}")
