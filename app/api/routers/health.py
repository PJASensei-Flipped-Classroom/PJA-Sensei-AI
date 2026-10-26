from fastapi import APIRouter, Response, status

from app.api.routers import conversations

router = APIRouter(tags=["Health"])

@router.get("/health_check")
def health_check():
    return {"status": "ok"}

@router.get("/health")
def health(response: Response):
    llm_configured = conversations.get_llm_port().is_configured()

    if not llm_configured:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ok" if llm_configured else "error",
        "llm_configured": llm_configured,
        "chroma_ok": False,
        "conversations": len(conversations.repo._store),
        "cache_size": 0
    }

@router.get("/metrics")
def metrics():
    return {
        "requests_total": 0,
        "errors_total": 0,
        "active_conversations": 0
    }

@router.get("/metrics/prometheus")
def prometheus_metrics():
    metrics_data = (
        "# TYPE pja_sensei_requests_total counter\n"
        "pja_sensei_requests_total 0\n"
        "# TYPE pja_sensei_active_conversations gauge\n"
        "pja_sensei_active_conversations 0\n"
    )
    return Response(content=metrics_data, media_type="text/plain")