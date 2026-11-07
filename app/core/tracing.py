import inspect
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from functools import wraps
from typing import Any, TypeVar

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import Tracer, TracerProvider
from opentelemetry.sdk.trace.export import (
    ConsoleSpanExporter,
    SimpleSpanProcessor,
    SpanExporter,
)
from opentelemetry.trace import Span, Status, StatusCode

from app.core.config import Settings
from app.core.logging import log_context

_provider: TracerProvider | None = None
_tracer: Tracer | None = None

F = TypeVar("F", bound=Callable[..., Any])


def _build_exporter(settings: Settings) -> SpanExporter | None:
    if settings.otel_exporter == "console":
        return ConsoleSpanExporter()
    if settings.otel_exporter == "otlp":
        return OTLPSpanExporter(
            endpoint=settings.otel_exporter_otlp_endpoint,
            insecure=True,
        )
    return None


def configure_tracing(
    settings: Settings,
    *,
    exporter: SpanExporter | None = None,
    force: bool = False,
) -> TracerProvider | None:
    global _provider, _tracer
    if _provider is not None and not force:
        return _provider
    if not settings.otel_enabled and exporter is None:
        return None

    provider = TracerProvider(
        resource=Resource.create(
            {
                SERVICE_NAME: settings.otel_service_name,
                "deployment.environment": settings.app_env,
            }
        )
    )
    selected_exporter = exporter if exporter is not None else _build_exporter(settings)
    if selected_exporter is not None:
        provider.add_span_processor(SimpleSpanProcessor(selected_exporter))

    _provider = provider
    _tracer = provider.get_tracer("jobsmith")
    if not force:
        trace.set_tracer_provider(provider)
    return provider


def get_tracer(name: str = "jobsmith") -> Tracer:
    if _tracer is not None:
        return _tracer
    return trace.get_tracer(name)


def format_trace_id(trace_id: int) -> str:
    return format(trace_id, "032x")


def get_current_trace_id() -> str | None:
    span_context = trace.get_current_span().get_span_context()
    if not span_context.is_valid:
        return None
    return format_trace_id(span_context.trace_id)


def get_span_trace_id(span: Span) -> str | None:
    span_context = span.get_span_context()
    if not span_context.is_valid:
        return None
    return format_trace_id(span_context.trace_id)


@contextmanager
def span(
    name: str,
    attributes: Mapping[str, Any] | None = None,
) -> Iterator[Span]:
    tracer = get_tracer()
    with tracer.start_as_current_span(name, attributes=dict(attributes or {})) as current:
        try:
            yield current
        except Exception as exc:
            current.record_exception(exc)
            current.set_status(Status(StatusCode.ERROR, str(exc)))
            raise


def traced_node(node_name: str) -> Callable[[F], F]:
    def decorator(func: F) -> F:
        if inspect.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                with (
                    log_context(node=node_name),
                    span(f"node.{node_name}", {"jobsmith.node": node_name}),
                ):
                    return await func(*args, **kwargs)

            return async_wrapper  # type: ignore[return-value]

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            with (
                log_context(node=node_name),
                span(f"node.{node_name}", {"jobsmith.node": node_name}),
            ):
                return func(*args, **kwargs)

        return sync_wrapper  # type: ignore[return-value]

    return decorator
