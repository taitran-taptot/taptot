"""Append TAPTOT feedback rows to a Google Sheet via Apps Script web app."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def append_feedback_row(
    *,
    email: str,
    category_label: str,
    content: str,
    plan_url: str | None,
    time_iso: str,
) -> None:
    settings = get_settings()
    url = (settings.feedback_sheets_webhook_url or "").strip()
    if not url:
        return
    payload: dict[str, Any] = {
        "secret": settings.feedback_sheets_secret or "",
        "time": time_iso,
        "email": email,
        "category": category_label,
        "plan_url": plan_url or "",
        "content": content,
    }
    try:
        response = httpx.post(url, json=payload, timeout=15.0, follow_redirects=True)
        if response.status_code >= 400:
            logger.warning("Feedback sheet webhook HTTP %s", response.status_code)
    except Exception:
        logger.exception("Feedback sheet webhook failed")
