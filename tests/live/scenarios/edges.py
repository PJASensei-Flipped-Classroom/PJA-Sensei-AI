"""Live: contract / edge scenarios."""

from __future__ import annotations

import httpx

from tests.live.helpers import (
    ScenarioResult,
    base_config,
    msg_body,
    skip_if_provider_429,
    start_conversation,
)


async def health_and_validate(client: httpx.AsyncClient) -> ScenarioResult:
    name = "Health + validate-config"
    health = await client.get("/health")
    validated = await client.post("/validate-config", json={"config": base_config()})
    ok = health.status_code == 200 and validated.status_code == 200 and validated.json().get("valid") is True
    return ScenarioResult(
        7,
        name,
        ok,
        f"health={health.status_code} valid={validated.json().get('valid') if validated.status_code == 200 else None}",
    )


async def unknown_404(client: httpx.AsyncClient) -> ScenarioResult:
    name = "Unknown conversation 404"
    missing = "00000000-0000-0000-0000-000000000000"
    res = await client.get(f"/conversations/{missing}")
    return ScenarioResult(8, name, res.status_code == 404, f"status={res.status_code}")


async def token_budget(client: httpx.AsyncClient) -> ScenarioResult:
    name = "Token budget 403"
    cid = await start_conversation(
        client, config=base_config(maxTokensPerSession=1)
    )
    first = await client.post(f"/conversations/{cid}/messages", json=msg_body("q1"))
    if skip := skip_if_provider_429(9, name, first.json() if first.status_code == 200 else None):
        return skip
    second = await client.post(f"/conversations/{cid}/messages", json=msg_body("q2"))
    # First may succeed; second should 403 if tokens were counted
    ok = first.status_code == 200 and (
        second.status_code == 403
        or second.json().get("message_id") == "token_budget_exceeded"
    )
    return ScenarioResult(
        9,
        name,
        ok,
        f"first={first.status_code} second={second.status_code}",
    )
