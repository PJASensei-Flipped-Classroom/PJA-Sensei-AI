from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["ui"])
STATIC_DIR = Path(__file__).resolve().parent.parent.parent / "static"


@router.get("/", response_class=HTMLResponse)
def serve_index() -> HTMLResponse:
    index_path = STATIC_DIR / "index.html"
    return HTMLResponse(content=index_path.read_text(encoding="utf-8"))


@router.get("/scenarios", response_class=HTMLResponse)
def serve_scenarios() -> HTMLResponse:
    scenarios_path = STATIC_DIR / "scenarios.html"
    return HTMLResponse(content=scenarios_path.read_text(encoding="utf-8"))