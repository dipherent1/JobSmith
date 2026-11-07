import json
import logging
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar, Token
from datetime import UTC, datetime
from typing import Any

from app.core.config import Settings

_trace_id: ContextVar[str | None] = ContextVar("jobsmith_trace_id", default=None)
_node: ContextVar[str | None] = ContextVar("jobsmith_node", default=None)
_source: ContextVar[str | None] = ContextVar("jobsmith_source", default=None)

_SENSITIVE_KEYS = {
    "api_key",
    "apikey",
    "authorization",
    "contact",
    "email",
    "password",
    "phone",
    "resume",
    "resume_text",
    "secret",
    "token",
}
_MAX_STRING_LENGTH = 500
_MAX_DEPTH = 6


def bind_trace_id(value: str | None) -> Token[str | None]:
    return _trace_id.set(value)


def reset_trace_id(token: Token[str | None]) -> None:
    _trace_id.reset(token)


def current_trace_id() -> str | None:
    value = _trace_id.get()
    if value:
        return value
    from app.core.tracing import get_current_trace_id

    return get_current_trace_id()


def current_node() -> str | None:
    return _node.get()


def current_source() -> str | None:
    return _source.get()


@contextmanager
def log_context(
    *,
    node: str | None = None,
    source: str | None = None,
    trace_id: str | None = None,
) -> Iterator[None]:
    tokens: list[tuple[ContextVar[Any], Token[Any]]] = []
    if node is not None:
        tokens.append((_node, _node.set(node)))
    if source is not None:
        tokens.append((_source, _source.set(source)))
    if trace_id is not None:
        tokens.append((_trace_id, _trace_id.set(trace_id)))
    try:
        yield
    finally:
        for variable, token in reversed(tokens):
            variable.reset(token)


def _is_sensitive(key: str) -> bool:
    normalized = key.lower()
    if normalized in _SENSITIVE_KEYS:
        return True
    return normalized.endswith(("_api_key", "_secret", "_password", "_token"))


def sanitize(value: Any, *, key: str | None = None, depth: int = 0) -> Any:
    if key is not None and _is_sensitive(key):
        return "[REDACTED]"
    if depth >= _MAX_DEPTH:
        return "[TRUNCATED]"
    if isinstance(value, dict):
        return {
            str(item_key): sanitize(item_value, key=str(item_key), depth=depth + 1)
            for item_key, item_value in value.items()
        }
    if isinstance(value, (list, tuple, set)):
        items = list(value)
        truncated = items[:_MAX_STRING_LENGTH]
        sanitized = [sanitize(item, depth=depth + 1) for item in truncated]
        if len(items) > len(truncated):
            sanitized.append(f"[TRUNCATED {len(items) - len(truncated)} ITEMS]")
        return sanitized
    if isinstance(value, str):
        if len(value) > _MAX_STRING_LENGTH:
            return f"{value[:_MAX_STRING_LENGTH]}...[TRUNCATED]"
        return value
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return str(value)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "trace_id": current_trace_id(),
            "node": current_node(),
            "source": current_source(),
        }
        fields = getattr(record, "fields", None)
        if fields is not None:
            payload["fields"] = sanitize(fields)
        if record.exc_info:
            exception = record.exc_info[1]
            payload["error"] = {
                "type": type(exception).__name__ if exception else record.exc_info[0].__name__,
                "message": str(exception) if exception else None,
                "stack": self.formatException(record.exc_info),
            }
        return json.dumps(payload, default=str)


class ConsoleFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        prefix = (
            f"{self.formatTime(record)} {record.levelname} {record.name} "
            f"[trace={current_trace_id() or '-'} node={current_node() or '-'} "
            f"source={current_source() or '-'}]"
        )
        message = record.getMessage()
        fields = getattr(record, "fields", None)
        if fields is not None:
            message = f"{message} {json.dumps(sanitize(fields), default=str)}"
        result = f"{prefix} {message}"
        if record.exc_info:
            result = f"{result}\n{self.formatException(record.exc_info)}"
        return result


def configure_logging(settings: Settings) -> None:
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(settings.log_level.upper())

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter() if settings.log_format == "json" else ConsoleFormatter())
    root.addHandler(handler)

    for noisy in ("uvicorn.access", "httpx", "httpcore", "opentelemetry"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
