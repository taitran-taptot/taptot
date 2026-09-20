"""Upsert beginner-friendly Vietnamese how-to copy onto existing exercises."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SEED_PATH = PROJECT_ROOT / "seeds" / "exercise_copy_vi.json"

FORBIDDEN_SUBSTR = (
    "pully",
    "pulley",
    "placeholder",
    "cơ delta",
    "cơ bẫy",
    "cô lập nghiêm ngặt",
    "hình thức hơn",
)


def load_exercise_copy_seed() -> list[dict[str, Any]]:
    if not SEED_PATH.is_file():
        return []
    raw = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    return raw if isinstance(raw, list) else []


def mistakes_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, list):
        joined = "\n".join(str(x).strip() for x in value if str(x).strip())
        return joined or None
    text_val = str(value).strip()
    return text_val or None


def _as_steps(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def validate_copy_entry(item: dict[str, Any]) -> list[str]:
    """Return hygiene problems for one seed row (empty list = ok)."""
    problems: list[str] = []
    name = str(item.get("name_en") or item.get("id") or "?")
    steps = _as_steps(item.get("instruction_steps_vi"))
    if not (4 <= len(steps) <= 6):
        problems.append(f"{name}: need 4–6 steps, got {len(steps)}")
    mistakes = item.get("common_mistakes_vi") or []
    if isinstance(mistakes, str):
        mistakes_list = [m for m in mistakes.split("\n") if m.strip()]
    else:
        mistakes_list = [str(m).strip() for m in mistakes if str(m).strip()]
    if not (2 <= len(mistakes_list) <= 4):
        problems.append(f"{name}: need 2–4 mistakes, got {len(mistakes_list)}")
    if any(str(m).lstrip().startswith("[") for m in mistakes_list):
        problems.append(f"{name}: mistakes look like a raw list")
    tips = str(item.get("tips_vi") or "").strip()
    prose = str(item.get("instruction_vi") or "").strip()
    if not tips:
        problems.append(f"{name}: missing tips")
    if not prose:
        problems.append(f"{name}: missing instruction_vi")
    blob = " ".join(steps) + " " + " ".join(mistakes_list) + " " + tips + " " + prose
    low = blob.lower()
    for token in FORBIDDEN_SUBSTR:
        if token in low:
            problems.append(f"{name}: forbidden token {token!r}")
    if " inch" in low or low.startswith("inch"):
        problems.append(f"{name}: leftover inch unit")
    return problems


def validate_copy_seed(items: list[dict[str, Any]] | None = None) -> list[str]:
    rows = items if items is not None else load_exercise_copy_seed()
    problems: list[str] = []
    seen: set[str] = set()
    for item in rows:
        name = str(item.get("name_en") or "").strip()
        if not name:
            problems.append("entry missing name_en")
            continue
        if name in seen:
            problems.append(f"duplicate name_en: {name}")
        seen.add(name)
        problems.extend(validate_copy_entry(item))
    return problems


def _table_exists(conn: Connection, table: str, *, is_sqlite: bool) -> bool:
    if is_sqlite:
        row = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name=:t"),
            {"t": table},
        ).fetchone()
        return bool(row)
    row = conn.execute(
        text(
            "SELECT EXISTS ("
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = :t"
            ")"
        ),
        {"t": table},
    ).scalar()
    return bool(row)


def _find_exercise_id(conn: Connection, *, name_en: str, exercise_id: int | None) -> int | None:
    row = conn.execute(
        text("SELECT id FROM exercises WHERE name_en = :name_en LIMIT 1"),
        {"name_en": name_en},
    ).fetchone()
    if row:
        return int(row[0])
    if exercise_id is None:
        return None
    row = conn.execute(
        text("SELECT id FROM exercises WHERE id = :id LIMIT 1"),
        {"id": exercise_id},
    ).fetchone()
    return int(row[0]) if row else None


def seed_exercise_copy(conn: Connection, *, is_sqlite: bool) -> int:
    """Update instruction fields only. Returns number of matched rows."""
    items = load_exercise_copy_seed()
    if not items or not _table_exists(conn, "exercises", is_sqlite=is_sqlite):
        return 0

    now = datetime.now(UTC)
    updated = 0
    for item in items:
        name_en = str(item.get("name_en") or "").strip()
        if not name_en:
            continue
        raw_id = item.get("id")
        try:
            exercise_id = int(raw_id) if raw_id is not None else None
        except (TypeError, ValueError):
            exercise_id = None
        eid = _find_exercise_id(conn, name_en=name_en, exercise_id=exercise_id)
        if eid is None:
            continue

        steps = _as_steps(item.get("instruction_steps_vi"))
        params = {
            "id": eid,
            "instruction_vi": str(item.get("instruction_vi") or "").strip() or None,
            "instruction_steps_vi": json.dumps(steps, ensure_ascii=False),
            "common_mistakes_vi": mistakes_text(item.get("common_mistakes_vi")),
            "tips_vi": str(item.get("tips_vi") or "").strip() or None,
            "updated_at": now,
        }
        if is_sqlite:
            conn.execute(
                text(
                    """
                    UPDATE exercises SET
                        instruction_vi = :instruction_vi,
                        instruction_steps_vi = :instruction_steps_vi,
                        common_mistakes_vi = :common_mistakes_vi,
                        tips_vi = :tips_vi,
                        updated_at = :updated_at
                    WHERE id = :id
                    """
                ),
                params,
            )
        else:
            conn.execute(
                text(
                    """
                    UPDATE exercises SET
                        instruction_vi = :instruction_vi,
                        instruction_steps_vi = CAST(:instruction_steps_vi AS jsonb),
                        common_mistakes_vi = :common_mistakes_vi,
                        tips_vi = :tips_vi,
                        updated_at = :updated_at
                    WHERE id = :id
                    """
                ),
                params,
            )
        updated += 1
    return updated
