"""Feature-pack ASGI tests: reveal quota, checkpoints, summary, stream webhook."""

from __future__ import annotations

import io
import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.application.container import AppContainer
from app.core.config import MAX_REVEALS_PER_SESSION
from tests.conftest import build_valid_config, mock_llm_json


def _start(client: TestClient, **cfg_overrides) -> str:
    res = client.post(
        "/conversations",
        json={
            "problem_description": "Feature pack lab",
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


def test_reveal_gated_then_quota(
    client: TestClient,
    container: AppContainer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cid = _start(client)
    conv = container.sessions.get_conversation_or_404(cid)

    blocked = client.post(
        f"/conversations/{cid}/hints/reveal",
        json={"focus": "controller"},
    )
    assert blocked.status_code == 403

    conv.prompt_scores.extend([2, 2])  # REVEAL_LOW_STREAK
    mock_llm_json(monkeypatch, container, answer="hint")
    # Reveal uses separate JSON shape — stub hint payloads.
    hint_choice = MagicMock()
    hint_choice.message.content = (
        '{"hint": "Check the class-level mapping annotation.", '
        '"suggested_next_step": "Add the mapping"}'
    )
    hint_resp = MagicMock(
        choices=[hint_choice],
        usage=MagicMock(prompt_tokens=1, completion_tokens=1),
    )
    monkeypatch.setattr(
        container.client.chat.completions,
        "create",
        AsyncMock(return_value=hint_resp),
    )

    for i in range(MAX_REVEALS_PER_SESSION):
        ok = client.post(
            f"/conversations/{cid}/hints/reveal",
            json={"focus": "controller"},
        )
        assert ok.status_code == 200, ok.text
        body = ok.json()
        assert body["reveal_count"] == i + 1
        assert body["reveals_remaining"] == MAX_REVEALS_PER_SESSION - (i + 1)
        assert "```" not in body["hint"]

    exhausted = client.post(
        f"/conversations/{cid}/hints/reveal",
        json={"focus": "controller"},
    )
    assert exhausted.status_code == 403
    assert "quota" in exhausted.json()["detail"].lower()

    state = client.get(f"/conversations/{cid}").json()
    assert state["reveal_count"] == MAX_REVEALS_PER_SESSION
    assert state["max_reveals_per_session"] == MAX_REVEALS_PER_SESSION


def test_message_surfaces_next_checkpoint(
    client: TestClient,
    container: AppContainer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cid = _start(
        client,
        learningContext={
            "goals": ["Utwórz @RestController", "Zwróć JSON"],
            "referenceMaterials": [],
        },
        checkpoints=[
            {
                "id": "cp1",
                "after_goal": "Utwórz @RestController",
                "hint": "Odblokuj testy jednostkowe kontrolera",
            }
        ],
    )

    mock_choice = MagicMock()
    mock_choice.message.content = json.dumps(
        {
            "answer": "Dobrze — masz kontroler. Co z body odpowiedzi?",
            "prompt_score": 7,
            "prompt_feedback": "ok",
            "penalty_applied": False,
            "suggested_next_step": "",
            "goal_progress": [
                {"goal": "Utwórz @RestController", "status": "done"},
                {"goal": "Zwróć JSON", "status": "in_progress"},
            ],
        }
    )
    mock_response = MagicMock(
        choices=[mock_choice],
        usage=MagicMock(prompt_tokens=5, completion_tokens=5),
    )
    monkeypatch.setattr(
        container.client.chat.completions,
        "create",
        AsyncMock(return_value=mock_response),
    )

    res = client.post(f"/conversations/{cid}/messages", json=_msg())
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["next_checkpoint"] is not None
    assert body["next_checkpoint"]["id"] == "cp1"
    assert "testy" in (body["next_checkpoint"]["hint"] or "").lower()
    assert body["suggested_next_step"]
    assert "cp1" in container.sessions.get_conversation_or_404(cid).unlocked_checkpoints


def test_summary_includes_rich_fields(
    client: TestClient,
    container: AppContainer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cid = _start(
        client,
        learningContext={
            "goals": ["g1"],
            "referenceMaterials": [],
        },
        evaluationCriteria=["Clarity", "Progress"],
    )
    conv = container.sessions.get_conversation_or_404(cid)
    conv.messages.append({"role": "user", "content": "help"})
    conv.messages.append({"role": "assistant", "content": "hint"})
    conv.prompt_scores.append(4)
    conv.reveal_count = 1
    conv.ide_events.append({"type": "copy_blocked", "meta": {}, "at": "t"})
    conv.goal_progress = [{"goal": "g1", "status": "in_progress"}]

    summary_choice = MagicMock()
    summary_choice.message.content = json.dumps(
        {
            "mastery_score": 55,
            "student_actions": "asked once",
            "agent_evaluation_of_student": "ok",
            "student_evaluation_of_agent": "n/a",
            "professors_summary": "brief",
            "goal_mastery": [
                {"goal": "g1", "status": "in_progress", "notes": "started"}
            ],
            "criteria_assessment": [
                {"criterion": "Clarity", "assessment": "fair"},
                {"criterion": "Progress", "assessment": "early"},
            ],
            "reveal_usage": {"count": 1, "notes": "one unlock"},
            "ide_events_detail": "one copy block",
        }
    )
    monkeypatch.setattr(
        container.client.chat.completions,
        "create",
        AsyncMock(
            return_value=MagicMock(
                choices=[summary_choice],
                usage=MagicMock(prompt_tokens=1, completion_tokens=1),
            )
        ),
    )

    res = client.post(f"/conversations/{cid}/summary")
    assert res.status_code == 200, res.text
    body = res.json()
    assert "mastery_score" in body
    assert "professors_summary" in body
    assert body["ide_events"]["reveals"] == 1
    assert body["reveal_count"] == 1
    assert body["goals"] == ["g1"]
    assert body["evaluation_criteria"] == ["Clarity", "Progress"]
    assert "ide_events_structured" in body
    assert body["ide_events_structured"]["copy_blocked"] == 1
    assert isinstance(body.get("goal_mastery"), list)


def test_stream_final_fires_message_webhook(
    client: TestClient,
    container: AppContainer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cid = _start(client)
    mock_llm_json(monkeypatch, container, answer="stream-ok")

    # Fake streaming LLM: non-stream path may be used; stream service tries stream=True.
    class _Delta:
        def __init__(self, content: str):
            self.content = content

    class _Choice:
        def __init__(self, content: str):
            self.delta = _Delta(content)

    class _Chunk:
        def __init__(self, content: str, usage=None):
            self.choices = [_Choice(content)] if content else []
            self.usage = usage

    payload = (
        '{"answer": "stream-ok", "prompt_score": 5, '
        '"prompt_feedback": "f", "penalty_applied": false}'
    )

    async def fake_stream(**kwargs):
        if not kwargs.get("stream"):
            choice = MagicMock()
            choice.message.content = payload
            return MagicMock(
                choices=[choice],
                usage=MagicMock(prompt_tokens=2, completion_tokens=2),
            )

        async def gen():
            mid = len(payload) // 2
            yield _Chunk(payload[:mid])
            yield _Chunk(
                payload[mid:],
                usage=MagicMock(prompt_tokens=2, completion_tokens=2),
            )

        return gen()

    monkeypatch.setattr(
        container.client.chat.completions, "create", AsyncMock(side_effect=fake_stream)
    )

    captured: list[dict] = []

    async def capture_webhook(payload, url=None, *, request_id="-"):
        captured.append(dict(payload))

    monkeypatch.setattr(
        "app.api.routers.messages.send_request_telemetry", capture_webhook
    )

    with client.stream(
        "POST",
        f"/conversations/{cid}/messages/stream",
        json=_msg(),
    ) as resp:
        assert resp.status_code == 200
        body = b"".join(resp.iter_bytes()).decode("utf-8")

    assert '"type": "final"' in body or '"type":"final"' in body
    assert captured, "expected stream final telemetry webhook"
    evt = captured[-1]
    assert evt["event"] == "message"
    assert evt["conversation_id"] == cid
    assert evt.get("message_id")
    assert "prompt_score" in evt
    assert "tokens_used" in evt
    assert "is_cached" in evt
    assert "penalty_applied" in evt


def test_stream_emits_tokens_before_llm_finishes(
    container: AppContainer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """StreamService must yield token NDJSON while the LLM generator is still running."""
    import asyncio
    import uuid

    from app.application.dto import CodeContext, MessageRequest
    from app.domain.sensei import SenseiConfig

    cid = container.sessions.start_conversation(
        "Stream live lab",
        SenseiConfig.model_validate(build_valid_config()),
    )

    class _Delta:
        def __init__(self, content: str):
            self.content = content

    class _Choice:
        def __init__(self, content: str):
            self.delta = _Delta(content)

    class _Chunk:
        def __init__(self, content: str, usage=None):
            self.choices = [_Choice(content)] if content else []
            self.usage = usage

    consumer_got_token = asyncio.Event()
    prefix = '{"answer": "'
    mid = "Hello"
    suffix = ' World", "prompt_score": 5, "prompt_feedback": "f", "penalty_applied": false}'

    async def fake_stream(**kwargs):
        async def gen():
            yield _Chunk(prefix + mid)
            # Block until the consumer has yielded the first token line.
            # If StreamService buffers until done, this deadlocks → timeout.
            await asyncio.wait_for(consumer_got_token.wait(), timeout=2.0)
            yield _Chunk(
                suffix,
                usage=MagicMock(prompt_tokens=2, completion_tokens=2),
            )

        return gen()

    monkeypatch.setattr(
        container.client.chat.completions, "create", AsyncMock(side_effect=fake_stream)
    )

    req = MessageRequest(
        question="Ping?",
        code_context=CodeContext(
            current_file_name="A.java",
            current_code="class A {}",
            error_logs="",
        ),
    )

    async def drive() -> list[str]:
        lines: list[str] = []
        async for line in container.stream.stream_message(cid, req, str(uuid.uuid4())):
            lines.append(line)
            if '"type": "token"' in line or '"type":"token"' in line:
                consumer_got_token.set()
        return lines

    lines = asyncio.run(drive())
    assert any('"type": "token"' in ln or '"type":"token"' in ln for ln in lines)
    assert any('"type": "final"' in ln or '"type":"final"' in ln for ln in lines)
    assert consumer_got_token.is_set()


def test_rag_pdf_extract_chunks(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.adapters.rag_chroma import RagService
    from app.domain.sensei import ReferenceMaterial

    rag = RagService()

    class FakePage:
        def extract_text(self):
            return "Spring REST controllers map HTTP paths to methods. " * 5

    class FakeReader:
        def __init__(self, _buf):
            self.pages = [FakePage(), FakePage()]

    monkeypatch.setattr("pypdf.PdfReader", FakeReader)

    class FakeResp:
        status_code = 200
        headers = {"content-type": "application/pdf"}
        content = b"%PDF-fake"
        text = ""

        def raise_for_status(self):
            return None

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return None

        async def get(self, url):
            return FakeResp()

    monkeypatch.setattr("app.adapters.rag_chroma.httpx.AsyncClient", FakeClient)

    import asyncio

    asyncio.run(
        rag.load_materials(
            "cid-pdf-1",
            [
                ReferenceMaterial(
                    type="pdf",
                    title="Slides PDF",
                    url="https://example.com/notes.pdf",
                )
            ],
        )
    )
    ctx, sources = rag.retrieve_context("cid-pdf-1", "HTTP paths")
    assert "SPRING" in ctx.upper() or "REST" in ctx.upper() or ctx
    # Indexed materials surface via chroma; citation_only empty on success.
    assert sources or ctx


def test_rag_pdf_failure_falls_back_to_citation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.adapters.rag_chroma import RagService
    from app.domain.sensei import ReferenceMaterial

    rag = RagService()

    class BoomClient:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return None

        async def get(self, url):
            raise RuntimeError("network down")

    monkeypatch.setattr("app.adapters.rag_chroma.httpx.AsyncClient", BoomClient)

    import asyncio

    asyncio.run(
        rag.load_materials(
            "cid-pdf-2",
            [
                ReferenceMaterial(
                    type="pdf",
                    title="Broken",
                    url="https://example.com/broken.pdf",
                    page=3,
                )
            ],
        )
    )
    ctx, sources = rag.retrieve_context("cid-pdf-2", "anything")
    assert ctx == ""
    assert sources and sources[0]["title"] == "Broken"
    assert sources[0].get("page") == 3
