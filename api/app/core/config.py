from functools import lru_cache
from pathlib import Path

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

API_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = API_DIR.parent
UPLOAD_DIR = PROJECT_ROOT / "uploads"


def normalize_database_url(url: str) -> str:
    """Accept Railway/Supabase `postgres://` URLs for SQLAlchemy + psycopg3."""
    raw = (url or "").strip()
    if raw.startswith("postgres://"):
        raw = "postgresql://" + raw[len("postgres://") :]
    if raw.startswith("postgresql://"):
        raw = "postgresql+psycopg://" + raw[len("postgresql://") :]
    return raw


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=API_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "TAPTOT API"
    app_env: str = "development"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"

    # Prefer PostgreSQL via api/.env; no local SQLite default.
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/taptot"
    db_pool_size: int = 10
    db_max_overflow: int = 20

    secret_key: str = "change-me-to-a-long-random-secret-key-min-32-chars"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    algorithm: str = "HS256"

    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60
    # Guest AI generate + public POST /plans (per IP / window). Auth endpoints use 20.
    ai_generate_rate_limit: int = 8
    public_plan_create_rate_limit: int = 12
    # Only enable behind a reverse proxy that overwrites X-Forwarded-For.
    rate_limit_trust_x_forwarded_for: bool = False
    redis_url: str = ""

    frontend_url: str = "http://localhost:3000"
    password_reset_expire_hours: int = 1
    email_verify_expire_hours: int = 24

    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:3000/auth/google/callback"

    facebook_client_id: str = ""
    facebook_client_secret: str = ""
    facebook_redirect_uri: str = "http://localhost:3000/auth/facebook/callback"

    # Email (smtp | resend | console)
    email_provider: str = "console"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@taptot.vn"
    resend_api_key: str = ""

    # AI (OpenAI Chat Completions)
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_base_url: str = "https://api.openai.com/v1"
    openai_timeout_seconds: int = 90
    openai_temperature: float = 0.4
    openai_max_tokens: int = 4096
    # Deterministic-first off: exercise picks require OpenAI (hard fail if unavailable).
    workout_gen_use_openai: bool = True
    workout_gen_coach_advice: bool = True
    # Cổng điều tiết gọi OpenAI (chống 429 khi nhiều người gen cùng lúc).
    # Redis (nếu có REDIS_URL) điều tiết xuyên process; không có thì semaphore trong process.
    ai_max_concurrent: int = 2
    ai_gate_wait_seconds: int = 45
    ai_retry_attempts: int = 3
    ai_retry_base_seconds: float = 2.0
    # False = không giới hạn tạo lịch AI; True = dùng ai_free_generations_per_month + subscription.
    ai_quota_enabled: bool = False
    # Chỉ có hiệu lực khi ai_quota_enabled=True. 0 = hết lượt free (cần sub/credit).
    ai_free_generations_per_month: int = 0
    # Giá tham chiếu (đồng bộ seed pay_per_generate)
    ai_generate_price_vnd: int = 49000
    # True = bắt buộc mã tem sản phẩm khi gen lịch. False = tạm bỏ cổng (dev/test).
    require_redeem_code_for_generate: bool = True

    feedback_sheets_webhook_url: str = ""
    feedback_sheets_secret: str = ""

    # Payments
    payment_webhook_secret: str = ""
    vnpay_tmn_code: str = ""
    vnpay_hash_secret: str = ""
    momo_partner_code: str = ""
    momo_access_key: str = ""
    momo_secret_key: str = ""
    momo_endpoint: str = "https://test-payment.momo.vn/v2/gateway/api/create"
    momo_query_endpoint: str = "https://test-payment.momo.vn/v2/gateway/api/query"
    momo_ipn_url: str = ""

    @property
    def momo_configured(self) -> bool:
        return bool(
            (self.momo_partner_code or "").strip()
            and (self.momo_access_key or "").strip()
            and (self.momo_secret_key or "").strip()
        )

    # Media
    upload_dir: str = str(UPLOAD_DIR)
    max_upload_mb: int = 10
    media_base_url: str = "http://localhost:8000/media"

    @field_validator("database_url")
    @classmethod
    def _normalize_database_url(cls, value: str) -> str:
        return normalize_database_url(value)

    @field_validator("upload_dir")
    @classmethod
    def _anchor_upload_dir(cls, value: str) -> str:
        """Resolve relative UPLOAD_DIR against the repo root, not the process cwd.

        Otherwise `../uploads` points somewhere different for uvicorn (run from api/)
        than for scripts run from the repo root.
        """
        path = Path(value).expanduser()
        if not path.is_absolute():
            path = (API_DIR / path).resolve()
        return str(path)

    @model_validator(mode="after")
    def _trust_proxy_in_production(self):
        if self.app_env.lower() in {"production", "prod"}:
            self.rate_limit_trust_x_forwarded_for = True
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def use_redis_rate_limit(self) -> bool:
        return bool(self.redis_url)


@lru_cache
def get_settings() -> Settings:
    return Settings()
