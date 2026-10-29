"""Upsert shop orders to a Google Sheet via Apps Script.

Payload ``kind`` is ``order``. The script finds the row by ``public_code`` and
updates it, or appends a row when the code is new. See
``api/scripts/google_order_sheet.gs``.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import get_settings
from app.models.entities import ShopOrder, ShopOrderItem

logger = logging.getLogger(__name__)

_STATUS_LABELS = {
    "awaiting_confirm": "Chờ xác nhận",
    "placed": "Chờ xác nhận",
    "packing": "Đang đóng gói",
    "shipping": "Đang giao",
    "completed": "Hoàn thành",
    "cancelled": "Đã hủy",
}

_PAYMENT_LABELS = {
    "cod": "COD",
    "bank_transfer": "Chuyển khoản",
    "unpaid": "Chưa thanh toán",
    "awaiting_transfer": "Chờ chuyển khoản",
    "paid": "Đã thanh toán",
}


def sync_order_row(order: ShopOrder, items: list[ShopOrderItem]) -> None:
    settings = get_settings()
    url = (settings.order_sheets_webhook_url or "").strip()
    if not url:
        return
    payload = _payload(order, items, settings.order_sheets_secret or "")
    try:
        response = httpx.post(url, json=payload, timeout=15.0, follow_redirects=True)
        if response.status_code >= 400:
            logger.warning("Order sheet webhook HTTP %s", response.status_code)
    except Exception:
        logger.exception("Order sheet webhook failed")


def _payload(order: ShopOrder, items: list[ShopOrderItem], secret: str) -> dict[str, Any]:
    method = _PAYMENT_LABELS.get(order.payment_method or "", order.payment_method or "")
    pay = _PAYMENT_LABELS.get(order.payment_status or "", order.payment_status or "")
    payment = " · ".join(part for part in (method, pay) if part)
    address = ", ".join(
        part
        for part in (
            order.address_line,
            order.ward_name,
            order.district_name,
            order.province_name,
        )
        if part
    )
    products = "; ".join(f"{item.name_vi} × {item.quantity}" for item in items)
    created = order.created_at.isoformat(timespec="seconds") if order.created_at else ""
    return {
        "secret": secret,
        "kind": "order",
        "time": created,
        "public_code": order.public_code or "",
        "status": _STATUS_LABELS.get(order.order_status or "", order.order_status or ""),
        "recipient_name": order.recipient_name or "",
        "phone": order.phone or "",
        "address": address,
        "products": products,
        "total_vnd": int(order.total_vnd or 0),
        "discount_vnd": int(order.discount_vnd or 0),
        "promo_code": order.promo_code or "",
        "promo_discount_vnd": int(order.promo_discount_vnd or 0),
        "payment": payment,
        "note": order.note or "",
    }
