"""MoMo captureWallet create + IPN signature helpers."""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any


CREATE_SIGN_KEYS = (
    "accessKey",
    "amount",
    "extraData",
    "ipnUrl",
    "orderId",
    "orderInfo",
    "partnerCode",
    "redirectUrl",
    "requestId",
    "requestType",
)

IPN_SIGN_KEYS = (
    "accessKey",
    "amount",
    "extraData",
    "message",
    "orderId",
    "orderInfo",
    "orderType",
    "partnerCode",
    "payType",
    "requestId",
    "responseTime",
    "resultCode",
    "transId",
)

QUERY_SIGN_KEYS = (
    "accessKey",
    "orderId",
    "partnerCode",
    "requestId",
)


def _raw_signature(keys: tuple[str, ...], fields: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in keys:
        value = fields.get(key, "")
        if value is None:
            value = ""
        parts.append(f"{key}={value}")
    return "&".join(parts)


def sign(secret: str, keys: tuple[str, ...], fields: dict[str, Any]) -> str:
    raw = _raw_signature(keys, fields)
    return hmac.new(secret.encode("utf-8"), raw.encode("utf-8"), hashlib.sha256).hexdigest()


def sign_create(secret: str, fields: dict[str, Any]) -> str:
    return sign(secret, CREATE_SIGN_KEYS, fields)


def sign_ipn(secret: str, fields: dict[str, Any]) -> str:
    return sign(secret, IPN_SIGN_KEYS, fields)


def sign_query(secret: str, fields: dict[str, Any]) -> str:
    return sign(secret, QUERY_SIGN_KEYS, fields)


def signature_matches(secret: str, keys: tuple[str, ...], fields: dict[str, Any], given: str | None) -> bool:
    expected = sign(secret, keys, fields)
    return hmac.compare_digest(expected, str(given or ""))


def extra_data_encode(payload: dict[str, Any]) -> str:
    if not payload:
        return ""
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
