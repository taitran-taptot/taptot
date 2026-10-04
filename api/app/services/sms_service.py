"""Outbound SMS for shop order confirmations (console stub or HTTP webhook)."""

from __future__ import annotations

import logging

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class SmsService:
    def send(self, to: str, body: str) -> None:
        settings = get_settings()
        provider = (settings.sms_provider or "console").lower().strip()
        phone = (to or "").strip()
        text = (body or "").strip()
        if not phone or not text:
            return
        if provider == "console" or settings.debug:
            logger.info("[sms] to=%s body=%s", phone, text)
            return
        if provider == "http":
            self._send_http(phone, text)
            return
        logger.warning("Unknown SMS provider: %s", provider)

    def _send_http(self, to: str, body: str) -> None:
        settings = get_settings()
        url = (settings.sms_http_url or "").strip()
        if not url:
            raise RuntimeError("SMS_HTTP_URL not configured")
        headers = {"Content-Type": "application/json"}
        token = (settings.sms_http_token or "").strip()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        with httpx.Client(timeout=15) as client:
            resp = client.post(url, headers=headers, json={"to": to, "body": body})
            resp.raise_for_status()

    def send_order_placed(self, phone: str, public_code: str, total_vnd: int) -> None:
        amount = f"{int(total_vnd):,}".replace(",", ".")
        body = (
            f"TAPTOT: Dat don thanh cong. Ma don {public_code}. "
            f"Tong {amount}d. Tra cuu: SĐT + ma don tren taptot.vn/tra-cuu-don"
        )
        self.send(phone, body)
