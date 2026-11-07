from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "JobSmith"
    app_env: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"
    log_format: Literal["json", "console"] = "json"

    database_url: str = "postgresql+asyncpg://jobsmith:jobsmith@localhost:5432/jobsmith"

    openrouter_api_key: SecretStr | None = None
    openrouter_decisions_url: str = "https://openrouter.ai/api/alpha/decisions"
    jev_model: str = "typesafe/jev-1.14"

    groq_api_key: SecretStr | None = None
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_model: str = "llama-3.3-70b-versatile"

    remotive_base_url: str = "https://remotive.com/api/remote-jobs"

    http_timeout_seconds: float = 15.0
    retry_max_attempts: int = 3
    retry_backoff_seconds: float = 0.5

    otel_enabled: bool = True
    otel_service_name: str = "jobsmith-api"
    otel_exporter: Literal["console", "otlp", "none"] = "console"
    otel_exporter_otlp_endpoint: str = "http://localhost:4317"

    metrics_enabled: bool = True
    metrics_exporter: Literal["console", "none"] = "none"
    metrics_export_interval_ms: int = 60_000

    cors_origins: str = "http://localhost:3000"
    trace_id_header: str = "X-Trace-ID"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
