from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.api import deps
from app.api.deps import get_webhook_port
from app.application.access import require_professor
from app.application.metrics import metrics
from app.core.config import settings
from app.domain.ports import WebhookPort

router = APIRouter(tags=["Health"])

@router.get("/health_check")
def health_check():
    return {"status": "ok"}


@router.get("/health")
def health(response: Response):
    llm_configured = deps.get_llm_port().is_configured()
    chroma_ok = deps.get_rag_port().is_healthy()
    cache_size = deps.get_cache_port().size()
    active_convs = deps.repo.count_active()

    if not llm_configured:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ok" if llm_configured else "error",
        "llm_configured": llm_configured,
        "chroma_ok": chroma_ok,
        "conversations": active_convs,
        "cache_size": cache_size,
    }


def _require_ops_access(request: Request) -> None:
    if not settings.AI_AUTH_ENABLED:
        return
    claims = getattr(request.state, "jwt_claims", None)
    if not require_professor(claims):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message_id": "forbidden",
                "detail": "Professor role required for metrics/webhooks.",
            },
        )
@router.get("/metrics")
def metrics_json(request: Request):
    _require_ops_access(request)
    snap = metrics.snapshot()
    snap["active_conversations"] = deps.repo.count_active()
    return snap

@router.get("/metrics/prometheus")
def prometheus_metrics(request: Request):
    _require_ops_access(request)
    snap = metrics.snapshot()
    active = deps.repo.count_active()
    metrics_data = (
        "# TYPE pja_sensei_requests_total counter\n"
        f"pja_sensei_requests_total {snap['requests_total']}\n"
        "# TYPE pja_sensei_errors_total counter\n"
        f"pja_sensei_errors_total {snap['errors_total']}\n"
        "# TYPE pja_sensei_messages_total counter\n"
        f"pja_sensei_messages_total {snap['messages_total']}\n"
        "# TYPE pja_sensei_llm_rate_limited_total counter\n"
        f"pja_sensei_llm_rate_limited_total {snap['llm_rate_limited_total']}\n"
        "# TYPE pja_sensei_active_conversations gauge\n"
        f"pja_sensei_active_conversations {active}\n"
    )
    return Response(content=metrics_data, media_type="text/plain")


@router.get("/webhooks/recent")
def recent_webhooks(
    request: Request,
    limit: int = 20,
    webhooks: WebhookPort = Depends(get_webhook_port),
):
    _require_ops_access(request)
    recent_fn = getattr(webhooks, "recent", None)
    if not callable(recent_fn):
        return {"events": [], "count": 0}
    events = recent_fn(limit=limit)
    return {"events": events, "count": len(recent_fn(limit=0))}
