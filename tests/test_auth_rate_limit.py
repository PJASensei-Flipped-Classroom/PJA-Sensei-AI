"""JWT auth, inbound IP rate limit, and LLM rate-limit → 503 mapping."""
import time
from typing import Dict, List, Optional

import jwt
import pytest
from fastapi.testclient import TestClient

from app.api.middleware import reset_rate_limit_buckets
from app.api.routers.conversations import get_llm_port
from app.core.config import settings
from app.domain.ports import LlmPort, LlmResult
from app.infrastructure.llm_errors import LlmRateLimitError
from app.main import app

client = TestClient(app)

MINIMAL_CONFIG = {
    "language": "pl",
    "evaluationCriteria": "strict",
    "learningContext": {"goals": [{"id": "g1", "description": "Cel 1"}]},
    "agentPersona": {"name": "Sensei", "tone": "helpful"},
    "agentBehavior": {"mode": "theory"},
    "preLab": {"enabled": False},
}


def _make_token(
    *,
    secret: Optional[str] = None,
    exp_offset: int = 3600,
    sub: str = "student-1",
    role: Optional[str] = None,
    include_aud_iss: bool = True,
) -> str:
    # OLD: payload = {"sub": "spring-backend", "exp": int(time.time()) + exp_offset}
    payload = {
        "sub": sub,
        "exp": int(time.time()) + exp_offset,
    }
    if include_aud_iss:
        aud = (settings.AI_JWT_AUDIENCE or "").strip()
        iss = (settings.AI_JWT_ISSUER or "").strip()
        if aud:
            payload["aud"] = aud
        if iss:
            payload["iss"] = iss
    if role:
        payload["role"] = role
    return jwt.encode(payload, secret or settings.AI_JWT_SECRET, algorithm="HS256")


@pytest.fixture(autouse=True)
def _reset_security_knobs():
    prev_auth = settings.AI_AUTH_ENABLED
    settings.AI_AUTH_ENABLED = False
    reset_rate_limit_buckets()
    yield
    settings.AI_AUTH_ENABLED = prev_auth
    reset_rate_limit_buckets()
    app.dependency_overrides.clear()


def test_auth_disabled_allows_conversations_without_token():
    settings.AI_AUTH_ENABLED = False
    res = client.get("/health_check")
    assert res.status_code == 200
    start = client.post("/conversations", json={"config": MINIMAL_CONFIG})
    assert start.status_code == 200


def test_auth_enabled_health_stays_open_without_token():
    settings.AI_AUTH_ENABLED = True
    res = client.get("/health")
    assert res.status_code in (200, 503)
    check = client.get("/health_check")
    assert check.status_code == 200


def test_auth_enabled_rejects_missing_token():
    settings.AI_AUTH_ENABLED = True
    res = client.post("/conversations", json={"config": MINIMAL_CONFIG})
    assert res.status_code == 401
    body = res.json()
    assert body["message_id"] == "unauthorized"


def test_auth_enabled_rejects_bad_token():
    settings.AI_AUTH_ENABLED = True
    res = client.post(
        "/conversations",
        json={"config": MINIMAL_CONFIG},
        headers={"Authorization": "Bearer not-a-real-token"},
    )
    assert res.status_code == 401
    assert res.json()["message_id"] == "unauthorized"


def test_auth_enabled_accepts_valid_token():
    settings.AI_AUTH_ENABLED = True
    token = _make_token()
    res = client.post(
        "/conversations",
        json={"config": MINIMAL_CONFIG},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert "conversation_id" in res.json()


def test_auth_enabled_rejects_expired_token():
    settings.AI_AUTH_ENABLED = True
    token = _make_token(exp_offset=-10)
    res = client.post(
        "/conversations",
        json={"config": MINIMAL_CONFIG},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 401


def test_force_hint_requires_professor_role_when_auth_on():
    settings.AI_AUTH_ENABLED = True
    student = _make_token(sub="student-1", role="student")
    start = client.post(
        "/conversations",
        json={"config": MINIMAL_CONFIG},
        headers={"Authorization": f"Bearer {student}"},
    )
    assert start.status_code == 200
    cid = start.json()["conversation_id"]

    denied = client.post(
        f"/conversations/{cid}/hints/force",
        json={"reason": "try"},
        headers={"Authorization": f"Bearer {student}"},
    )
    assert denied.status_code == 403
    assert denied.json()["detail"]["message_id"] == "forbidden"

    professor = _make_token(sub="prof-1", role="professor")
    allowed = client.post(
        f"/conversations/{cid}/hints/force",
        json={"reason": "lab help"},
        headers={"Authorization": f"Bearer {professor}"},
    )
    assert allowed.status_code == 200
    assert allowed.json()["forced"] is True


def test_student_cannot_access_another_students_conversation():
    settings.AI_AUTH_ENABLED = True
    a = _make_token(sub="student-a")
    b = _make_token(sub="student-b")
    start = client.post(
        "/conversations",
        json={"config": MINIMAL_CONFIG},
        headers={"Authorization": f"Bearer {a}"},
    )
    cid = start.json()["conversation_id"]

    other = client.get(
        f"/conversations/{cid}",
        headers={"Authorization": f"Bearer {b}"},
    )
    assert other.status_code == 404


def test_metrics_require_auth_when_enabled():
    settings.AI_AUTH_ENABLED = True
    assert client.get("/metrics").status_code == 401
    student = _make_token(sub="student-1", role="student")
    assert client.get(
        "/metrics",
        headers={"Authorization": f"Bearer {student}"},
    ).status_code == 403
    professor = _make_token(sub="prof-1", role="professor")
    assert client.get(
        "/metrics",
        headers={"Authorization": f"Bearer {professor}"},
    ).status_code == 200


def test_ip_rate_limit_returns_429_with_retry_after():
    settings.AI_AUTH_ENABLED = False
    settings.RATE_LIMIT_PER_MINUTE = 2
    reset_rate_limit_buckets()

    r1 = client.post("/conversations", json={"config": MINIMAL_CONFIG})
    r2 = client.post("/conversations", json={"config": MINIMAL_CONFIG})
    r3 = client.post("/conversations", json={"config": MINIMAL_CONFIG})

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r3.status_code == 429
    body = r3.json()
    assert body["message_id"] == "rate_limit_exceeded"
    assert "Retry-After" in r3.headers


class AlwaysRateLimitedLlm(LlmPort):
    def is_configured(self) -> bool:
        return True

    def generate_json(
        self,
        system_prompt: str,
        messages: List[Dict[str, str]],
        model_override: Optional[str] = None,
    ) -> LlmResult:
        raise LlmRateLimitError("429 Too Many Requests")


def test_exhausted_llm_rate_limit_maps_to_503():
    settings.AI_AUTH_ENABLED = False
    app.dependency_overrides[get_llm_port] = lambda: AlwaysRateLimitedLlm()

    start = client.post("/conversations", json={"config": MINIMAL_CONFIG})
    assert start.status_code == 200
    conv_id = start.json()["conversation_id"]

    res = client.post(
        f"/conversations/{conv_id}/messages",
        json={"question": "Jak dodać RestController?"},
    )
    assert res.status_code == 503
    body = res.json()
    assert body["message_id"] == "llm_rate_limited"
    assert "Retry-After" in res.headers
