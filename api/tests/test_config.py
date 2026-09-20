from app.core.config import Settings, normalize_database_url


def test_normalize_railway_postgres_url():
    assert (
        normalize_database_url("postgres://u:p@host:5432/railway")
        == "postgresql+psycopg://u:p@host:5432/railway"
    )


def test_normalize_postgresql_url():
    assert (
        normalize_database_url("postgresql://u:p@host:5432/db")
        == "postgresql+psycopg://u:p@host:5432/db"
    )


def test_normalize_keeps_psycopg_url():
    url = "postgresql+psycopg://u:p@localhost:5432/taptot"
    assert normalize_database_url(url) == url


def test_production_trusts_forwarded_for():
    settings = Settings(
        app_env="production",
        debug=False,
        secret_key="a" * 32,
        cors_origins="https://taptot.vn",
        database_url="postgresql://u:p@host:5432/db",
    )
    assert settings.rate_limit_trust_x_forwarded_for is True
    assert settings.database_url.startswith("postgresql+psycopg://")
