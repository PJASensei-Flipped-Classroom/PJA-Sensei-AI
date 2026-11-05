"""Features 2,3,4,6,7,8,9,11,12,18,19 smoke tests."""
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.api.middleware import reset_rate_limit_buckets
from app.domain.sensei import SenseiConfig
from app.application.similarity import best_solution_match
from app.application.config_dry_run import run_config_dry_run

client = TestClient(app)

BASE = {
    "language": "en",
    "evaluationCriteria": "REST",
    "learningContext": {"goals": [{"id": "g1", "description": "Goal 1"}]},
    "agentPersona": {"name": "Sensei", "tone": "helpful"},
    "agentBehavior": {"mode": "theory"},
    "preLab": {"enabled": False},
}


def setup_function():
    settings.AI_AUTH_ENABLED = False
    settings.FRUSTRATION_EVENT_COOLDOWN_SECONDS = 0.0
    reset_rate_limit_buckets()


def test_dry_run_and_hint_ladder_in_config():
    cfg = {
        **BASE,
        "hintLadder": [
            {"level": "nudge", "text": "Check the annotation name."},
            {"level": "concept", "text": "RestController combines Controller+ResponseBody."},
            {"level": "almost", "text": "Put @RestController on the class."},
        ],
        "maxHints": 3,
        "focusModeSeconds": 120,
        "solutionPack": ["@RestController\npublic class Demo {}"],
    }
    sc = SenseiConfig(**cfg)
    assert len(sc.hint_ladder) == 3
    assert sc.resolved_hint_texts()[0].startswith("Check")

    dry = client.post("/config/dry-run", json={"config": cfg})
    assert dry.status_code == 200
    body = dry.json()
    assert body["steps_total"] >= 5
    assert "hint_ladder_preview" in body


def test_focus_mode_set_on_compile_error():
    cid = client.post("/conversations", json={"config": {**BASE, "focusModeSeconds": 180}}).json()[
        "conversation_id"
    ]
    ev = client.post(
        f"/conversations/{cid}/events",
        json={"type": "compile_error", "meta": {}},
    )
    assert ev.status_code == 200
    assert ev.json()["in_focus_mode"] is True
    assert ev.json()["focus_until"] is not None


def test_hint_ladder_reveal_returns_level():
    cfg = {
        **BASE,
        "frustrationThreshold": 1,
        "maxHints": 2,
        "hintLadder": [
            {"level": "nudge", "text": "Look at imports."},
            {"level": "almost", "text": "Add RestController."},
        ],
    }
    cid = client.post("/conversations", json={"config": cfg}).json()["conversation_id"]
    client.post(f"/conversations/{cid}/events", json={"type": "compile_error"})
    rev = client.post(f"/conversations/{cid}/hints/reveal")
    assert rev.status_code == 200
    assert rev.json()["hint_level"] == "nudge"
    assert "imports" in rev.json()["hint"]


def test_force_custom_hint_and_note_and_observe():
    cid = client.post("/conversations", json={"config": BASE}).json()["conversation_id"]
    forced = client.post(
        f"/conversations/{cid}/hints/force",
        json={"reason": "office-hours", "customHint": "Think about @GetMapping.", "hintLevel": "concept"},
    )
    assert forced.status_code == 200
    assert forced.json()["forced"] is True
    assert forced.json()["hint_level"] == "concept"
    assert "GetMapping" in forced.json()["hint"]

    note = client.post(f"/conversations/{cid}/notes", json={"text": "Student confused about DI"})
    assert note.status_code == 200
    assert note.json()["notes_count"] == 1

    obs = client.get(f"/conversations/{cid}/observe")
    assert obs.status_code == 200
    assert obs.json()["intervention_notes"]
    assert obs.json()["conversation_id"] == cid


def test_dashboard_and_similarity_and_grade_payload():
    cfg = {
        **BASE,
        "labId": "lab-spring",
        "solutionPack": ["public class Demo { @RestController }"],
    }
    # labId is not on SenseiConfig — set via JWT normally; for dashboard filter use session lab_id
    start = client.post("/conversations", json={"config": {**BASE, "solutionPack": cfg["solutionPack"]}})
    cid = start.json()["conversation_id"]
    # manually set lab_id through repo
    from app.api.deps import repo

    conv = repo.get(cid)
    conv.lab_id = "lab-spring"
    repo.save(conv)

    dash = client.get("/conversations/professor/dashboard", params={"lab_id": "lab-spring"})
    assert dash.status_code == 200
    assert dash.json()["active_sessions"] >= 1

    sim = client.post(
        f"/conversations/{cid}/similarity",
        json={"code": "public class Demo { @RestController }"},
    )
    assert sim.status_code == 200
    assert sim.json()["best_score"] is not None
    assert "disclaimer" in sim.json()

    summary = client.post(f"/conversations/{cid}/summary")
    assert summary.status_code == 200
    assert "grade_payload" in summary.json()
    assert summary.json()["grade_payload"]["schema_version"] == "1.0"
    assert summary.json()["grade_payload"]["event"] == "grade_sync_prepared"


def test_similarity_helper_flags_high_overlap():
    r = best_solution_match(
        "def calculateTotal(items):\n    return sum(items)",
        ["def calculateTotal(items):\n    return sum(items)\n"],
    )
    assert r["flagged"] is True


def test_dry_run_helper_direct():
    sc = SenseiConfig(**BASE)
    out = run_config_dry_run(sc)
    assert out["valid"] is True
