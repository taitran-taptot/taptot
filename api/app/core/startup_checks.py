"""Startup security checks for production-safe defaults."""

from __future__ import annotations

import logging
import secrets

from app.core.config import Settings

logger = logging.getLogger(__name__)

WEAK_SECRETS = frozenset(
    {
        "",
        "change-me",
        "change-me-to-a-long-random-secret-key-min-32-chars",
        "secret",
        "password",
        "vietfit",
        "tfit",
        "taptot",
    }
)


def assert_security_settings(settings: Settings) -> None:
    """Fail hard in production; warn loudly in development."""
    is_prod = settings.app_env.lower() in {"production", "prod"}
    weak_secret = (
        settings.secret_key in WEAK_SECRETS
        or len(settings.secret_key) < 32
    )

    if weak_secret:
        msg = (
            "SECRET_KEY is weak or default. Set a random secret (>=32 chars) in api/.env. "
            f"Example: SECRET_KEY={secrets.token_urlsafe(48)}"
        )
        if is_prod:
            raise RuntimeError(msg)
        logger.warning("SECURITY: %s", msg)

    if is_prod and settings.debug:
        raise RuntimeError("DEBUG must be false when APP_ENV=production")

    if is_prod and ("*" in settings.cors_origins or not settings.cors_origin_list):
        raise RuntimeError("CORS_ORIGINS must be an explicit allow-list in production")
