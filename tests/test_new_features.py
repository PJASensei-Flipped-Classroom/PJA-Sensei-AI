"""File gates, RAG preview, force-hint, metrics, webhook buffer."""
import json
from typing import Dict, List, Optional

from fastapi.testclient import TestClient

from app.main import app
from app.api.routers.conversations import get_llm_port
from app.domain.ports import LlmPort, LlmResult
from app.infrastructure.webhooks import HttpWebhookAdapter
from app.api.routers.conversations import get_webhook_port

client = TestClient(app)


class QuietLlm(LlmPort):
    def is_configured(self) -> bool:
        return True

    def generate_json(
        self,
        system_prompt: str,
        messages: List[Dict[str, str]],
        model_override: Optional[str] = None,
    ) -> LlmResult:
        payload = {
            "answer": "OK",
            "prompt_score": 5,
            "prompt_feedback": "ok",
            "penalty_applied": False,
            "suggested_next_step": "next",
            "goal_progress": [{"goal": "g1", "status": "in_progress"}],
        }
        return LlmResult(raw_content=json.dumps(payload), tokens_used=1, model="quiet")


def _cfg(**extra):
    base = {
        "language": "en",
        "evaluationCriteria": "REST",
        "learningContext": {"goals": [{"id": "g1", "description": "Goal 1"}]},
        "agentPersona": {"name": "Sensei", "tone": "helpful"},
        "agentBehavior": {"mode": "theory"},
        "preLab": {"enabled": False},
        "hints": ["Look at the controller annotation."],
        "maxHints": 2,
        "frustrationThreshold": 2,
    }
    base.update(extra)
    return base


def test_allowed_and_blocked_files_enforced():
    app.dependency_overrides[get_llm_port] = lambda: QuietLlm()
    try:
        cfg = _cfg(
            requireFileContext=True,
            ideRestrictions={
                "allowedFiles": ["lab.java"],
                "blockedFiles": ["secrets.env"],
                "requireFileContext": True,
            },
        )
        cid = client.post("/conversations", json={"config": cfg}).json()["conversation_id"]

        blocked = client.post(
            f"/conversations/{cid}/messages",
            json={
                "question": "Help with this file",
                "codeContext": {
                    "currentCode": "class X {}",
                    "currentFileName": "secrets.env",
                },
            },
        )
        assert blocked.status_code == 200
        assert blocked.json()["debug_info"]["reason_code"] == "blocked_file"

        not_allowed = client.post(
            f"/conversations/{cid}/messages",
            json={
                "question": "Help with this file",
                "codeContext": {
                    "currentCode": "class X {}",
                    "currentFileName": "other.java",
                },
            },
        )
        assert not_allowed.json()["debug_info"]["reason_code"] == "file_not_allowed"

        ok = client.post(
            f"/conversations/{cid}/messages",
            json={
                "question": "What should I add?",
                "codeContext": {
                    "currentCode": "class Lab {}",
                    "currentFileName": "lab.java",
                },
            },
        )
        assert ok.status_code == 200
        assert ok.json()["message_id"] not in ("blocked", "rejected")
    finally:
        app.dependency_overrides.clear()


def test_rag_preview_on_start_with_inline_content():
    cfg = _cfg(
        referenceMaterials=[
            {
                "title": "Guide",
                "link": "https://example.com/guide",
                "content": "Use @RestController for REST endpoints.",
            }
        ]
    )
    res = client.post("/conversations", json={"config": cfg})
    assert res.status_code == 200
    preview = res.json()["rag_preview"]
    assert preview["chunks_ingested"] >= 1
    assert preview["materials"][0]["title"] == "Guide"


def test_force_hint_bypasses_streak_and_audits():
    cfg = _cfg()
    cid = client.post("/conversations", json={"config": cfg}).json()["conversation_id"]
    locked = client.post(f"/conversations/{cid}/hints/reveal")
    assert locked.status_code == 403

    forced = client.post(
        f"/conversations/{cid}/hints/force",
        json={"reason": "demo"},
    )
    assert forced.status_code == 200
    assert forced.json()["forced"] is True
    assert forced.json()["hint"]

    exported = client.get(f"/conversations/{cid}/export").json()
    assert any(e.get("type") == "force_hint" for e in exported.get("events", []))


def test_metrics_and_webhook_recent_buffer():
    captured = []

    def sender(url, payload):
        captured.append(payload)

    adapter = HttpWebhookAdapter(sender=sender)
    app.dependency_overrides[get_webhook_port] = lambda: adapter
    app.dependency_overrides[get_llm_port] = lambda: QuietLlm()
    try:
        before = client.get("/metrics").json()["requests_total"]
        cid = client.post("/conversations", json={"config": _cfg()}).json()["conversation_id"]
        client.post(
            f"/conversations/{cid}/messages",
            json={"question": "hello", "codeContext": {"currentCode": "x"}},
        )
        after = client.get("/metrics").json()
        assert after["requests_total"] > before
        assert after["messages_total"] >= 1

        client.post(f"/conversations/{cid}/summary")
        recent = client.get("/webhooks/recent").json()
        assert recent["count"] >= 1
        assert any(e["payload"]["event"] == "session_summary" for e in recent["events"])
    finally:
        app.dependency_overrides.clear()
