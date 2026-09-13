"""ASGI tests without a live OpenRouter — gates, contract, metrics."""



from __future__ import annotations



import pytest

from fastapi.testclient import TestClient



from tests.conftest import build_valid_config, mock_llm_json





def test_health_and_metrics_endpoints(client: TestClient) -> None:

    health = client.get("/health")

    assert health.status_code == 200

    assert health.json()["status"] == "ok"

    assert "X-Request-Id" in health.headers



    metrics = client.get("/metrics")

    assert metrics.status_code == 200

    assert "requests_total" in metrics.json()



    prom = client.get("/metrics/prometheus")

    assert prom.status_code == 200

    assert "pja_sensei_requests_total" in prom.text





def test_validate_config_contract(client: TestClient) -> None:

    bad = client.post("/validate-config", json={"config": {}})

    assert bad.status_code == 200

    assert bad.json()["valid"] is False



    good = client.post("/validate-config", json={"config": build_valid_config()})

    assert good.status_code == 200

    assert good.json()["valid"] is True





def test_conversation_lifecycle_and_events(client: TestClient) -> None:

    res = client.post(

        "/conversations",

        json={"problem_description": "Test setup", "config": build_valid_config()},

    )

    assert res.status_code == 200

    cid = res.json()["conversation_id"]



    assert client.get(f"/conversations/{cid}").status_code == 200

    assert client.get(f"/conversations/{cid}/export").json()["conversation_id"] == cid

    assert client.get(f"/conversations/{cid}/checkpoints").status_code == 200



    event_res = client.post(

        f"/conversations/{cid}/events",

        json={"type": "copy_blocked", "meta": {}},

    )

    assert event_res.status_code == 200



    assert client.delete(f"/conversations/{cid}").status_code == 200

    assert client.get(f"/conversations/{cid}").status_code == 404





def test_prelab_gate_blocks_and_unlocks(client: TestClient) -> None:

    cfg = build_valid_config(

        preLab={

            "enabled": True,

            "max_attempts": 2,

            "hint_after_fail": "spróbuj HTTP",

            "questions": [

                {"id": "q1", "prompt": "REST?", "expected_keywords": ["http"]}

            ],

        }

    )

    cid = client.post(

        "/conversations", json={"problem_description": "T", "config": cfg}

    ).json()["conversation_id"]



    blocked = client.post(

        f"/conversations/{cid}/messages",

        json={

            "question": "cześć",

            "code_context": {

                "current_file_name": "A.java",

                "current_code": "class A {}",

            },

        },

    )

    assert blocked.status_code == 403



    fail = client.post(

        f"/conversations/{cid}/prelab",

        json={"answers": [{"id": "q1", "answer": "nie wiem"}]},

    )

    assert fail.status_code == 200

    body = fail.json()

    assert body["passed"] is False

    assert body["score"] == 0.0

    assert "hint_after_fail" in body



    success = client.post(

        f"/conversations/{cid}/prelab",

        json={"answers": [{"id": "q1", "answer": "REST to HTTP API"}]},

    )

    assert success.status_code == 200

    assert success.json()["passed"] is True





def test_client_message_id_idempotency_prevents_duplicate_processing(

    client: TestClient, monkeypatch: pytest.MonkeyPatch

) -> None:

    """Identical client_message_id reuses prior response without calling LLM twice."""

    mock_llm_call = mock_llm_json(monkeypatch)



    cid = client.post(

        "/conversations",

        json={"problem_description": "T", "config": build_valid_config()},

    ).json()["conversation_id"]



    payload = {

        "question": "q",

        "client_message_id": "unique-idempotency-key",

        "code_context": {"current_file_name": "A.java", "current_code": "x"},

    }



    r1 = client.post(f"/conversations/{cid}/messages", json=payload)

    r2 = client.post(f"/conversations/{cid}/messages", json=payload)



    assert r1.status_code == 200

    assert r2.status_code == 200

    assert r1.json()["answer"] == r2.json()["answer"]

    assert mock_llm_call.call_count == 1


