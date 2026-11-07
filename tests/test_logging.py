import json
import logging

from app.core.logging import JsonFormatter, log_context


def _record(message: str) -> logging.LogRecord:
    return logging.LogRecord(
        name="jobsmith.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg=message,
        args=(),
        exc_info=None,
    )


def test_json_formatter_includes_context_and_redacts_sensitive_fields() -> None:
    record = _record("node.finished")
    record.fields = {
        "resume_text": "Jane Doe, jane@example.com",
        "api_key": "sk-secret",
        "nested": {"phone": "+1-555-0100", "count": 3},
        "long_text": "x" * 600,
    }

    with log_context(trace_id="trace-123", node="parse_request", source="remotive"):
        payload = json.loads(JsonFormatter().format(record))

    assert payload["trace_id"] == "trace-123"
    assert payload["node"] == "parse_request"
    assert payload["source"] == "remotive"
    assert payload["fields"]["resume_text"] == "[REDACTED]"
    assert payload["fields"]["api_key"] == "[REDACTED]"
    assert payload["fields"]["nested"]["phone"] == "[REDACTED]"
    assert payload["fields"]["nested"]["count"] == 3
    assert payload["fields"]["long_text"].endswith("...[TRUNCATED]")


def test_json_formatter_redacts_token_suffixes() -> None:
    record = _record("llm.call")
    record.fields = {"access_token": "abc", "input_tokens": 120}

    payload = json.loads(JsonFormatter().format(record))

    assert payload["fields"]["access_token"] == "[REDACTED]"
    assert payload["fields"]["input_tokens"] == 120
