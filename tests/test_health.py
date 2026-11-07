from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def test_health_returns_trace_id_header() -> None:
    settings = Settings(
        _env_file=None,
        app_env="test",
        log_level="WARNING",
        log_format="console",
        otel_enabled=False,
        metrics_enabled=False,
    )

    with TestClient(create_app(settings)) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert len(response.headers["X-Trace-ID"]) == 32
