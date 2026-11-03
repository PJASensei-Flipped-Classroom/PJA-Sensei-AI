from fastapi import APIRouter, Response, status

from app.api.routers import conversations

router = APIRouter(tags=["Health"])

@router.get("/health_check")
def health_check():
    return {"status": "ok"}


@router.get("/health")
def health(response: Response):
    from app.api.routers import conversations
    llm_configured = conversations.get_llm_port().is_configured()
    chroma_ok = conversations.get_rag_port().is_healthy()
    cache_size = conversations.get_cache_port().size()
    active_convs = sum(
        1 for c in conversations.repo._store.values() if not getattr(c, "is_deleted", False)
    )

    if not llm_configured:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ok" if llm_configured else "error",
        "llm_configured": llm_configured,
        "chroma_ok": chroma_ok,
        "conversations": len(conversations.repo._store),
        "cache_size": cache_size,
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