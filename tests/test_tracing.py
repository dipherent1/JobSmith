import pytest
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import StatusCode

from app.core.config import Settings
from app.core.tracing import (
    configure_tracing,
    get_current_trace_id,
    get_span_trace_id,
    span,
)


def _settings() -> Settings:
    return Settings(
        _env_file=None,
        app_env="test",
        otel_enabled=True,
        otel_exporter="none",
        metrics_enabled=False,
        log_format="console",
    )


def test_span_returns_trace_id_and_exports_span() -> None:
    exporter = InMemorySpanExporter()
    configure_tracing(_settings(), exporter=exporter, force=True)

    with span("test.operation", {"key": "value"}) as current:
        trace_id = get_span_trace_id(current)
        assert trace_id is not None
        assert len(trace_id) == 32
        assert get_current_trace_id() == trace_id

    finished = exporter.get_finished_spans()
    assert [item.name for item in finished] == ["test.operation"]
    assert finished[0].attributes["key"] == "value"


def test_span_records_exceptions_as_errors() -> None:
    exporter = InMemorySpanExporter()
    configure_tracing(_settings(), exporter=exporter, force=True)

    with pytest.raises(ValueError), span("test.failure"):
        raise ValueError("boom")

    finished = exporter.get_finished_spans()
    assert finished[0].status.status_code == StatusCode.ERROR
    assert "boom" in finished[0].status.description
