from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["ui"])
STATIC_DIR = Path(__file__).resolve().parent.parent.parent / "static"

# OLD: return HTMLResponse(content=...) with default caching
# Why: browsers can keep an old scenarios.html; S4 fix never loads → false FAIL.
# Wrong: stale JS fires two /events with no 16s wait.
# Better: no-store so / and /scenarios always pick up static edits.
_NO_STORE = {"Cache-Control": "no-store, max-age=0"}


@router.get("/", response_class=HTMLResponse)
def serve_index() -> HTMLResponse:
    index_path = STATIC_DIR / "index.html"
    return HTMLResponse(content=index_path.read_text(encoding="utf-8"), headers=_NO_STORE)


@router.get("/scenarios", response_class=HTMLResponse)
def serve_scenarios() -> HTMLResponse:
    scenarios_path = STATIC_DIR / "scenarios.html"
    return HTMLResponse(content=scenarios_path.read_text(encoding="utf-8"), headers=_NO_STORE)
