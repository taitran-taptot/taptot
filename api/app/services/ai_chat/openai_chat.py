"""Minimal OpenAI Chat Completions client for the Q&A agent (httpx)."""

from __future__ import annotations

import json
import logging
import time
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class OpenAIChatError(Exception):
    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def _parse_tool_calls(raw: Any) -> list[dict[str, Any]] | None:
    if not raw:
        return None
    out: list[dict[str, Any]] = []
    for item in raw:
        fn = (item or {}).get("function") or {}
        name = str(fn.get("name") or "").strip()
        if not name:
            continue
        args_raw = fn.get("arguments") or "{}"
        if isinstance(args_raw, dict):
            arguments = args_raw
        else:
            try:
                parsed = json.loads(args_raw)
                arguments = parsed if isinstance(parsed, dict) else {}
            except (json.JSONDecodeError, TypeError):
                arguments = {}
        out.append(
            {
                "id": str(item.get("id") or f"tool_{len(out)}"),
                "name": name,
                "arguments": arguments,
            }
        )
    return out or None


def chat_completions(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """POST /chat/completions. Returns {content, tool_calls, usage}."""
    settings = get_settings()
    key = (settings.openai_api_key or "").strip()
    if not key:
        raise OpenAIChatError("OpenAI chưa được cấu hình.", status_code=503)

    body: dict[str, Any] = {
        "model": settings.openai_model,
        "temperature": min(0.3, float(settings.openai_temperature or 0.3)),
        "max_completion_tokens": max(128, int(settings.openai_chat_max_tokens or 700)),
        "messages": messages,
    }
    if tools:
        body["tools"] = tools
        body["tool_choice"] = "auto"

    url = settings.openai_base_url.rstrip("/") + "/chat/completions"
    timeout = min(45, int(settings.openai_timeout_seconds or 45))
    attempts = max(1, int(settings.ai_retry_attempts or 3))
    base = float(settings.ai_retry_base_seconds or 2.0)
    last_error: Exception | None = None

    for attempt in range(attempts):
        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {key}",
                        "Content-Type": "application/json",
                    },
                    json=body,
                )
            if response.status_code == 429 and attempt < attempts - 1:
                wait = base * (2**attempt)
                logger.warning("OpenAI chat 429, retry in %.1fs", wait)
                time.sleep(wait)
                continue
            if response.status_code >= 400:
                raise OpenAIChatError(
                    f"OpenAI HTTP {response.status_code}",
                    status_code=response.status_code,
                )
            payload = response.json()
            choice = (payload.get("choices") or [{}])[0]
            message = choice.get("message") or {}
            usage = payload.get("usage")
            return {
                "content": message.get("content"),
                "tool_calls": _parse_tool_calls(message.get("tool_calls")),
                "raw_tool_calls": message.get("tool_calls"),
                "usage": usage if isinstance(usage, dict) else None,
            }
        except OpenAIChatError:
            raise
        except Exception as exc:
            last_error = exc
            if attempt < attempts - 1:
                time.sleep(base * (2**attempt))
                continue
            raise OpenAIChatError(str(exc) or "OpenAI request failed") from exc

    raise OpenAIChatError(str(last_error) or "OpenAI request failed")
