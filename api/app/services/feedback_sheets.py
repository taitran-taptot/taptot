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
        logger.warning("Feedback sheet skipped: FEEDBACK_SHEETS_WEBHOOK_URL is empty")
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
        ok = False
        if response.status_code < 400:
            try:
                ok = response.json().get("ok") is True
            except Exception:
                ok = False
        if not ok:
            logger.warning(
                "Feedback sheet webhook HTTP %s body %s",
                response.status_code,
                (getattr(response, "text", "") or "")[:180],
            )
    except Exception:
        logger.exception("Feedback sheet webhook failed")
