"""Cloudflare Turnstile verification for free workout generation."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request

from app.core.config import get_settings
from app.core.exceptions import ForbiddenError

logger = logging.getLogger(__name__)

MSG_CAPTCHA_REQUIRED = "Vui lòng xác minh bạn không phải robot rồi thử tạo lịch lại."
MSG_CAPTCHA_FAILED = "Xác minh không thành công. Vui lòng tải lại xác minh rồi thử lại."
MSG_CAPTCHA_UNAVAILABLE = "Không kiểm tra được xác minh lúc này. Vui lòng thử lại sau vài giây."


def verify_turnstile(token: str | None, remote_ip: str | None = None) -> None:
    """Verify Turnstile token when secret is configured; no-op if secret empty."""
    settings = get_settings()
    secret = (settings.turnstile_secret_key or "").strip()
    if not secret:
        return

    raw = (token or "").strip()
    if not raw:
        raise ForbiddenError(MSG_CAPTCHA_REQUIRED, code="captcha_required")

    data = urllib.parse.urlencode(
        {
            "secret": secret,
            "response": raw,
            **({"remoteip": remote_ip} if remote_ip else {}),
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        settings.turnstile_verify_url,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except (
        urllib.error.URLError,
        urllib.error.HTTPError,
        TimeoutError,
        json.JSONDecodeError,
        OSError,
    ) as exc:
        logger.warning("Turnstile verify unavailable: %s", exc)
        raise ForbiddenError(MSG_CAPTCHA_UNAVAILABLE, code="captcha_unavailable") from exc

    if not payload.get("success"):
        logger.info("Turnstile verify failed: %s", payload.get("error-codes"))
        raise ForbiddenError(MSG_CAPTCHA_FAILED, code="captcha_failed")
