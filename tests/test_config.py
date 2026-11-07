from app.core.config import Settings


def test_database_url_is_built_from_postgres_settings() -> None:
    settings = Settings(
        _env_file=None,
        postgres_user="alice",
        postgres_password="s3cret",
        postgres_db="jobs",
        postgres_host="db",
        postgres_port=5433,
    )

    assert settings.database_url == "postgresql+asyncpg://alice:s3cret@db:5433/jobs"


def test_database_url_escapes_password() -> None:
    settings = Settings(
        _env_file=None,
        postgres_user="alice",
        postgres_password="p@ss word",
    )

    assert "p%40ss+word" in settings.database_url


def test_database_url_override_is_used() -> None:
    override = "postgresql+asyncpg://user:pass@example.com:6543/custom"
    settings = Settings(_env_file=None, database_url=override)

    assert settings.database_url == override
