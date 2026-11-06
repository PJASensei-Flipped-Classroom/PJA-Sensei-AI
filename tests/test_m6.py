import json
import pytest
from typing import List, Dict, Optional
from fastapi.testclient import TestClient
from app.main import app
from app.domain.ports import LlmPort, LlmResult
from app.domain.exceptions import SsrfBlockedError
from unittest.mock import patch
import socket

from app.infrastructure.rag_chroma import (
    validate_safe_url,
    _strip_html,
    _decode_fetched_content,
    _extract_pdf_text,
)
from app.api.deps import get_llm_port, get_cache_port, get_rag_port

client = TestClient(app)


class CountingRagMockLlm(LlmPort):
    def __init__(self):
        self.calls = 0
        self.last_system_prompt = ""

    def is_configured(self) -> bool:
        return True

    def generate_json(
        self,
        system_prompt: str,
        messages: List[Dict[str, str]],
        model_override: Optional[str] = None,
    ) -> LlmResult:
        self.calls += 1
        self.last_system_prompt = system_prompt
        user_msg = messages[-1]["content"]
        g1_status = "done" if "@RestController" in user_msg else "in_progress"
        payload = {
            "answer": "Sprawdź w dokumentacji Springa jak działa adnotacja @RestController. Czy potrafisz połączyć to z endpointem?",
            "prompt_score": 8,
            "prompt_feedback": "Bardzo dobre pytanie studenta",
            "penalty_applied": False,
            "suggested_next_step": "Dodaj metodę GET",
            "goal_progress": [
                {"goal": "g1", "status": g1_status},
                {"goal": "g2", "status": "not_started"},
            ],
        }
        return LlmResult(
            raw_content=json.dumps(payload),
            tokens_used=60,
            model="m6-mock-llm",
        )


def test_m6_ssrf_protection_blocks_unsafe_urls():
    unsafe_urls = [
        "http://127.0.0.1:8000/admin",
        "http://localhost/secret",
        "http://169.254.169.254/latest/meta-data/",
        "http://192.168.1.1/router",
        "http://10.0.0.5/internal",
        "file:///etc/passwd",
    ]
    for bad_url in unsafe_urls:
        with pytest.raises(SsrfBlockedError):
            validate_safe_url(bad_url)

    bad_config = {
        "language": "pl",
        "evaluationCriteria": "REST API",
        "referenceMaterials": [
            {"title": "Internal AWS Meta", "link": "http://169.254.169.254/latest/meta-data/"}
        ],
        "learningContext": {"goals": [{"id": "g1", "description": "Cel 1"}]},
        "agentPersona": {"name": "Sensei", "tone": "sokratyczny"},
        "agentBehavior": {"mode": "theory"},
        "preLab": {"enabled": False},
    }
    res = client.post("/conversations", json={"config": bad_config})
    assert res.status_code == 400
    assert res.json()["message_id"] == "ssrf_blocked"


def test_m6_ssrf_dns_failure_is_fail_closed():
    with patch(
        "app.infrastructure.rag_chroma.socket.getaddrinfo",
        side_effect=socket.gaierror("Name or service not known"),
    ):
        with pytest.raises(SsrfBlockedError) as exc_info:
            validate_safe_url("https://example.com/docs")
    assert "Cannot resolve hostname" in exc_info.value.reason


def test_m6_html_and_pdf_material_extraction():
    html = "<html><script>alert(1)</script><body><p>Spring <b>REST</b></p></body></html>"
    cleaned = _strip_html(html)
    assert "alert" not in cleaned
    assert "Spring" in cleaned
    assert "REST" in cleaned

    html_bytes = b"<html><body><h1>Controller Guide</h1></body></html>"
    decoded = _decode_fetched_content(
        "https://example.com/guide.html", html_bytes, "text/html; charset=utf-8"
    )
    assert "Controller Guide" in decoded

    # Minimal PDF containing the text HelloRAG
    pdf_bytes = b"""%PDF-1.1
1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj
2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj
3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] /Contents 4 0 R /Resources<< /Font<< /F1 5 0 R >> >> >>endobj
4 0 obj<< /Length 44 >>stream
BT /F1 12 Tf 10 100 Td (HelloRAG) Tj ET
endstream
endobj
5 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000266 00000 n 
0000000361 00000 n 
trailer<< /Size 6 /Root 1 0 R >>
startxref
440
%%EOF
"""
    assert "HelloRAG" in _extract_pdf_text(pdf_bytes)
    pdf_decoded = _decode_fetched_content(
        "https://example.com/lab.pdf", pdf_bytes, "application/pdf"
    )
    assert "HelloRAG" in pdf_decoded


def test_m6_rag_sources_cache_hit_and_checkpoint_unlock():
    mock_llm = CountingRagMockLlm()
    get_cache_port().clear()
    app.dependency_overrides[get_llm_port] = lambda: mock_llm

    config = {
        "language": "pl",
        "evaluationCriteria": "Kontroler Spring",
        "referenceMaterials": [
            {
                "title": "Spring Boot REST Docs",
                "link": "https://spring.io/guides/gs/rest-service",
                "content": "Adnotacja @RestController w Spring Boot łączy @Controller oraz @ResponseBody.",
            }
        ],
        "learningContext": {
            "goals": [
                {"id": "g1", "description": "Utworzenie klasy @RestController"},
                {"id": "g2", "description": "Dodanie endpointu GET"},
            ]
        },
        "checkpoints": [
            {"id": "cp1", "afterGoal": "g1", "hint": "Teraz dodaj @GetMapping('/api')."},
            {"id": "cp2", "afterGoal": "g2", "hint": "Brawo, całe API gotowe!"},
        ],
        "agentPersona": {"name": "Sensei", "tone": "sokratyczny"},
        "agentBehavior": {"mode": "theory"},
        "preLab": {"enabled": False},
    }

    try:
        start_res = client.post("/conversations", json={"config": config})
        assert start_res.status_code == 200
        conv_id = start_res.json()["conversation_id"]

        msg1 = client.post(
            f"/conversations/{conv_id}/messages",
            json={"question": "Jak działa @RestController w Spring Boot?"},
        )
        assert msg1.status_code == 200
        data1 = msg1.json()
        assert len(data1["sources"]) == 1
        assert "Spring Boot REST Docs" in data1["sources"][0]
        assert "MATERIAŁY REFERENCYJNE LABU (RAG)" in mock_llm.last_system_prompt
        assert data1["debug_info"]["cache_hit"] is False
        assert mock_llm.calls == 1

        assert data1["next_checkpoint"]["id"] == "cp1"
        assert data1["next_checkpoint"]["unlocked"] is True
        assert data1["next_checkpoint"]["hint"] == "Teraz dodaj @GetMapping('/api')."

        conv_id_2 = client.post("/conversations", json={"config": config}).json()["conversation_id"]
        msg2 = client.post(
            f"/conversations/{conv_id_2}/messages",
            json={"question": "Jak działa @RestController w Spring Boot?"},
        )
        assert msg2.status_code == 200
        data2 = msg2.json()
        assert data2["debug_info"]["cache_hit"] is True
        assert mock_llm.calls == 1

        health_res = client.get("/health").json()
        assert health_res["chroma_ok"] is True
        assert health_res["cache_size"] >= 1

        del_res = client.delete(f"/conversations/{conv_id}")
        assert del_res.status_code == 200
        assert get_rag_port().retrieve(conv_id, "RestController") == []
    finally:
        app.dependency_overrides.clear()