from fastapi import APIRouter, Request

from app import __version__
from app.core.tracing import get_current_trace_id

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(request: Request) -> dict[str, str]:
    settings = request.app.state.settings
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": __version__,
        "trace_id": get_current_trace_id() or "unavailable",
    }
