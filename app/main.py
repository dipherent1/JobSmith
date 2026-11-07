import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

from app import __version__
from app.api.routes.health import router as health_router
from app.core.config import Settings, get_settings
from app.core.logging import (
    bind_trace_id,
    configure_logging,
    get_logger,
    reset_trace_id,
)
from app.core.metrics import configure_metrics
from app.core.tracing import (
    configure_tracing,
    get_span_trace_id,
    span,
)

logger = get_logger(__name__)
_httpx_instrumented = False


def create_app(settings: Settings | None = None) -> FastAPI:
    global _httpx_instrumented

    settings = settings or get_settings()
    configure_logging(settings)
    configure_tracing(settings)
    configure_metrics(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info(
            "app.started",
            extra={"fields": {"environment": settings.app_env, "version": __version__}},
        )
        yield
        logger.info("app.stopped")

    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        lifespan=lifespan,
    )
    app.state.settings = settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        started = time.perf_counter()
        with span(
            "http.request",
            {
                "http.method": request.method,
                "http.route": request.url.path,
                "jobsmith.correlation_id": request.headers.get(settings.trace_id_header),
            },
        ) as current_span:
            trace_id = get_span_trace_id(current_span) or uuid.uuid4().hex
            token = bind_trace_id(trace_id)
            status_code = 500
            try:
                response = await call_next(request)
                status_code = response.status_code
                response.headers[settings.trace_id_header] = trace_id
                return response
            except Exception:
                logger.exception(
                    "http.request.failed",
                    extra={
                        "fields": {
                            "method": request.method,
                            "path": request.url.path,
                        }
                    },
                )
                raise
            finally:
                duration_ms = (time.perf_counter() - started) * 1000
                logger.info(
                    "http.request.completed",
                    extra={
                        "fields": {
                            "method": request.method,
                            "path": request.url.path,
                            "status_code": status_code,
                            "duration_ms": round(duration_ms, 3),
                        }
                    },
                )
                reset_trace_id(token)

    app.include_router(health_router)

    if settings.otel_enabled:
        FastAPIInstrumentor.instrument_app(app)
        if not _httpx_instrumented:
            HTTPXClientInstrumentor().instrument()
            _httpx_instrumented = True

    return app


app = create_app()
