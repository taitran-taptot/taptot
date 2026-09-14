"""Pack / unpack per-slot meal notes and per-section exercise notes on a plan day.

Stored in UserDailyPlanDay.notes_vi as JSON:

  {"v": 1, "meal_notes": {...}, "section_notes": {...}, "split_role": "...", "text": "..."}

"""

from __future__ import annotations

import json
from typing import Any

_SECTION_KEYS = ("warmup", "main", "cooldown", "cardio")
_MEAL_NOTE_KEYS = ("breakfast", "lunch", "dinner")


def clamp_note(text: Any, *, max_len: int = 120) -> str | None:
    if text is None:
        return None
    s = str(text).strip()
    if not s:
        return None
    return s[:max_len]


def sanitize_section_notes(raw: Any) -> dict[str, str]:
    if not isinstance(raw, dict):
        return {}
    out: dict[str, str] = {}
    for key in _SECTION_KEYS:
        note = clamp_note(raw.get(key))
        if note:
            out[key] = note
    return out


def sanitize_meal_notes(raw: Any) -> dict[str, str]:
    if not isinstance(raw, dict):
        return {}
    out: dict[str, str] = {}
    for key in _MEAL_NOTE_KEYS:
        note = clamp_note(raw.get(key))
        if note:
            out[key] = note
    return out


def sanitize_advice(raw: Any, *, max_items: int = 5) -> list[str]:
    if not isinstance(raw, list):
        return []
    tips: list[str] = []
    for item in raw:
        note = clamp_note(item)
        if note:
            tips.append(note)
        if len(tips) >= max_items:
            break
    return tips


def pack_day_notes(
    meal_notes: dict[str, str] | None = None,
    section_notes: dict[str, str] | None = None,
    free_text: str | None = None,
    split_role: str | None = None,
) -> str | None:
    payload: dict[str, Any] = {"v": 1}
    mn = {
        str(k): str(v).strip()
        for k, v in (meal_notes or {}).items()
        if v is not None and str(v).strip()
    }
    sn = {
        str(k): str(v).strip()
        for k, v in (section_notes or {}).items()
        if v is not None and str(v).strip()
    }
    if mn:
        payload["meal_notes"] = mn
    if sn:
        payload["section_notes"] = sn
    if split_role and str(split_role).strip():
        payload["split_role"] = str(split_role).strip()
    if free_text and str(free_text).strip():
        payload["text"] = str(free_text).strip()
    if len(payload) == 1:
        return None
    return json.dumps(payload, ensure_ascii=False)


def unpack_day_notes(
    notes_vi: str | None,
) -> tuple[dict[str, str], dict[str, str], str | None, str | None]:
    """Return meal_notes, section_notes, free_text, split_role."""
    if not notes_vi:
        return {}, {}, None, None
    try:
        data = json.loads(notes_vi)
    except (json.JSONDecodeError, TypeError):
        return {}, {}, notes_vi, None
    if not isinstance(data, dict) or data.get("v") != 1:
        return {}, {}, notes_vi, None
    meal_notes = {
        str(k): str(v)
        for k, v in (data.get("meal_notes") or {}).items()
        if v is not None and str(v).strip()
    }
    section_notes = {
        str(k): str(v)
        for k, v in (data.get("section_notes") or {}).items()
        if v is not None and str(v).strip()
    }
    text = data.get("text")
    free = str(text).strip() if text else None
    role = data.get("split_role")
    split_role = str(role).strip() if role else None
    return meal_notes, section_notes, free or None, split_role or None
