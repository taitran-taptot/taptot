"""Upsert gymnastic-rings exercises + exercise_equipment links for home schedule gen."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SEED_PATH = PROJECT_ROOT / "seeds" / "gymnastic_rings_exercises.json"
EQUIPMENT_SLUG = "gymnastic-rings"
SEED_MARKER_PREFIX = "seed:gymnastic-rings:"
_REQUIRED_MUSCLES: dict[str, tuple[str, str, str | None, int]] = {
    # slug: (name_vi, name_en, parent_slug, sort_order)
    "chest-mid": ("Ngực giữa", "Mid chest", "chest", 12),
    "back-lats": ("Xô (lat)", "Lats", "back", 21),
    "core-upper": ("Bụng trên", "Upper abs", "core", 41),
    "quads": ("Đùi trước", "Quadriceps", "legs", 51),
    "biceps": ("Bắp tay trước", "Biceps", "arms", 61),
    "triceps": ("Bắp tay sau", "Triceps", "arms", 62),
    "forearms": ("Cẳng tay", "Forearms", "arms", 63),
    "shoulders-front": ("Vai trước", "Front delts", "shoulders", 31),
    "shoulders-rear": ("Vai sau", "Rear delts", "shoulders", 33),
    "shoulders-lateral": ("Vai giữa", "Lateral delts", "shoulders", 32),
    "hamstrings": ("Đùi sau", "Hamstrings", "legs", 52),
    "glutes": ("Mông", "Glutes", "legs", 53),
}


def load_ring_exercise_seed() -> list[dict[str, Any]]:
    if not SEED_PATH.is_file():
        return []
    raw = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    return raw if isinstance(raw, list) else []


def _difficulty_label(difficulty: int) -> str:
    from app.services.exercise_catalog_classify import DIFFICULTY_LABELS

    return DIFFICULTY_LABELS.get(int(difficulty), str(difficulty))


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


def _muscle_id_by_slug(conn: Connection) -> dict[str, int]:
    rows = conn.execute(text("SELECT id, slug FROM muscle_groups")).fetchall()
    return {str(r[1]): int(r[0]) for r in rows}


def _ensure_required_muscles(conn: Connection, *, is_sqlite: bool) -> dict[str, int]:
    """Ensure arm leaf groups used by ring seeds exist (fresh DBs may lack them)."""
    muscle_ids = _muscle_id_by_slug(conn)
    for slug, (name_vi, name_en, parent_slug, sort_order) in _REQUIRED_MUSCLES.items():
        if slug in muscle_ids:
            continue
        parent_id = muscle_ids.get(parent_slug) if parent_slug else None
        if is_sqlite:
            conn.execute(
                text(
                    "INSERT INTO muscle_groups "
                    "(slug, name_vi, name_en, sort_order, parent_id, is_filter_only) "
                    "VALUES (:slug, :name_vi, :name_en, :sort_order, :parent_id, 0)"
                ),
                {
                    "slug": slug,
                    "name_vi": name_vi,
                    "name_en": name_en,
                    "sort_order": sort_order,
                    "parent_id": parent_id,
                },
            )
            muscle_ids[slug] = int(conn.execute(text("SELECT last_insert_rowid()")).scalar())
        else:
            muscle_ids[slug] = int(
                conn.execute(
                    text(
                        "INSERT INTO muscle_groups "
                        "(slug, name_vi, name_en, sort_order, parent_id, is_filter_only) "
                        "VALUES (:slug, :name_vi, :name_en, :sort_order, :parent_id, FALSE) "
                        "RETURNING id"
                    ),
                    {
                        "slug": slug,
                        "name_vi": name_vi,
                        "name_en": name_en,
                        "sort_order": sort_order,
                        "parent_id": parent_id,
                    },
                ).scalar()
            )
    return muscle_ids


def _equipment_id(conn: Connection, equipment_slug: str) -> int | None:
    row = conn.execute(
        text("SELECT id FROM equipment WHERE slug = :slug LIMIT 1"),
        {"slug": equipment_slug},
    ).fetchone()
    return int(row[0]) if row else None


def _find_exercise_id(
    conn: Connection, *, slug: str, name_en: str, marker_prefix: str, notes_vi: str | None = None
) -> int | None:
    marker = str(notes_vi or f"{marker_prefix}{slug}").strip()
    row = conn.execute(
        text("SELECT id FROM exercises WHERE notes_vi = :marker LIMIT 1"),
        {"marker": marker},
    ).fetchone()
    if row:
        return int(row[0])
    row = conn.execute(
        text("SELECT id FROM exercises WHERE name_en = :name_en LIMIT 1"),
        {"name_en": name_en},
    ).fetchone()
    return int(row[0]) if row else None


def _link_equipment(conn: Connection, *, exercise_id: int, equipment_id: int) -> None:
    exists = conn.execute(
        text(
            "SELECT 1 FROM exercise_equipment "
            "WHERE exercise_id = :eid AND equipment_id = :eqid LIMIT 1"
        ),
        {"eid": exercise_id, "eqid": equipment_id},
    ).fetchone()
    if exists:
        return
    conn.execute(
        text(
            "INSERT INTO exercise_equipment (exercise_id, equipment_id) "
            "VALUES (:eid, :eqid)"
        ),
        {"eid": exercise_id, "eqid": equipment_id},
    )


def _mistakes_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, list):
        joined = "\n".join(str(x) for x in value if str(x).strip())
        return joined or None
    text_val = str(value).strip()
    return text_val or None


def seed_equipment_exercises(
    conn: Connection,
    *,
    is_sqlite: bool,
    items: list[dict[str, Any]],
    equipment_slug: str | None,
    marker_prefix: str,
) -> int:
    """Insert/update exercises and optionally link to one equipment slug."""
    if not items:
        return 0
    if not _table_exists(conn, "exercises", is_sqlite=is_sqlite):
        return 0
    if equipment_slug and not _table_exists(conn, "equipment", is_sqlite=is_sqlite):
        return 0

    eq_id = _equipment_id(conn, equipment_slug) if equipment_slug else None
    if equipment_slug and eq_id is None:
        return 0

    muscle_ids = _ensure_required_muscles(conn, is_sqlite=is_sqlite)
    now = datetime.now(UTC)
    count = 0

    for item in items:
        slug = str(item.get("slug") or "").strip()
        name_en = str(item.get("name_en") or "").strip()
        name_vi = str(item.get("name_vi") or "").strip()
        muscle_slug = str(item.get("muscle_slug") or "").strip()
        if not slug or not name_en or not name_vi or not muscle_slug:
            continue
        mg_id = muscle_ids.get(muscle_slug)
        if mg_id is None:
            continue

        difficulty = int(item.get("difficulty") or 2)
        secondary = item.get("secondary_muscles") or []
        steps = item.get("instruction_steps_vi") or []
        notes = str(item.get("notes_vi") or f"{marker_prefix}{slug}")
        params = {
            "name_vi": name_vi,
            "name_en": name_en,
            "muscle_group_id": mg_id,
            "exercise_type": str(item.get("exercise_type") or "main"),
            "movement_role": str(item.get("movement_role") or "compound"),
            "movement_pattern": str(item.get("movement_pattern") or "other"),
            "venue": str(item.get("venue") or "home"),
            "difficulty": difficulty,
            "difficulty_label": _difficulty_label(difficulty),
            "secondary_muscles": (
                json.dumps(secondary, ensure_ascii=False) if is_sqlite else secondary
            ),
            "instruction_steps_vi": (
                json.dumps(steps, ensure_ascii=False) if is_sqlite else steps
            ),
            "common_mistakes_vi": _mistakes_text(item.get("common_mistakes_vi")),
            "tips_vi": item.get("tips_vi"),
            "notes_vi": notes,
            "is_active": (
                (1 if item.get("is_active", True) else 0)
                if is_sqlite
                else bool(item.get("is_active", True))
            ),
            "updated_at": now,
        }
        if not is_sqlite:
            params["secondary_muscles"] = json.dumps(secondary, ensure_ascii=False)
            params["instruction_steps_vi"] = json.dumps(steps, ensure_ascii=False)

        eid = _find_exercise_id(
            conn,
            slug=slug,
            name_en=name_en,
            marker_prefix=marker_prefix,
            notes_vi=str(item.get("notes_vi") or "") or None,
        )
        if eid is None:
            insert_sql = """
                INSERT INTO exercises (
                    name_vi, name_en, muscle_group_id, exercise_type,
                    movement_role, movement_pattern, venue, difficulty, difficulty_label,
                    secondary_muscles, instruction_steps_vi, common_mistakes_vi,
                    tips_vi, notes_vi, is_active, created_at, updated_at
                ) VALUES (
                    :name_vi, :name_en, :muscle_group_id, :exercise_type,
                    :movement_role, :movement_pattern, :venue, :difficulty, :difficulty_label,
                    {sec}, {steps},
                    :common_mistakes_vi, :tips_vi, :notes_vi, :is_active, :created_at, :updated_at
                )
            """
            if is_sqlite:
                sql = insert_sql.format(sec=":secondary_muscles", steps=":instruction_steps_vi")
                conn.execute(text(sql), {**params, "created_at": now})
                eid = int(conn.execute(text("SELECT last_insert_rowid()")).scalar())
            else:
                sql = insert_sql.format(
                    sec="CAST(:secondary_muscles AS jsonb)",
                    steps="CAST(:instruction_steps_vi AS jsonb)",
                )
                eid = int(
                    conn.execute(
                        text(sql + " RETURNING id"),
                        {**params, "created_at": now},
                    ).scalar()
                )
        else:
            update_sql = """
                UPDATE exercises SET
                    name_vi = :name_vi,
                    name_en = :name_en,
                    muscle_group_id = :muscle_group_id,
                    exercise_type = :exercise_type,
                    movement_role = :movement_role,
                    movement_pattern = :movement_pattern,
                    venue = :venue,
                    difficulty = :difficulty,
                    difficulty_label = :difficulty_label,
                    secondary_muscles = {sec},
                    instruction_steps_vi = {steps},
                    common_mistakes_vi = :common_mistakes_vi,
                    tips_vi = :tips_vi,
                    notes_vi = :notes_vi,
                    is_active = :is_active,
                    updated_at = :updated_at
                WHERE id = :id
            """
            if is_sqlite:
                sql = update_sql.format(sec=":secondary_muscles", steps=":instruction_steps_vi")
            else:
                sql = update_sql.format(
                    sec="CAST(:secondary_muscles AS jsonb)",
                    steps="CAST(:instruction_steps_vi AS jsonb)",
                )
            conn.execute(text(sql), {**params, "id": eid})

        item_eq_slug = str(item.get("equipment_slug") or equipment_slug or "").strip()
        item_eq_id = _equipment_id(conn, item_eq_slug) if item_eq_slug else eq_id
        if item_eq_id is not None and _table_exists(conn, "exercise_equipment", is_sqlite=is_sqlite):
            _link_equipment(conn, exercise_id=eid, equipment_id=item_eq_id)
        count += 1

    return count


def seed_gymnastic_rings_exercises(conn: Connection, *, is_sqlite: bool) -> int:
    """Insert/update ring exercises and link to gymnastic-rings equipment."""
    return seed_equipment_exercises(
        conn,
        is_sqlite=is_sqlite,
        items=load_ring_exercise_seed(),
        equipment_slug=EQUIPMENT_SLUG,
        marker_prefix=SEED_MARKER_PREFIX,
    )


def load_band2_exercise_seed() -> list[dict[str, Any]]:
    path = PROJECT_ROOT / "seeds" / "resistance_band_2_exercises.json"
    if not path.is_file():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    return raw if isinstance(raw, list) else []


def seed_resistance_band_2_exercises(conn: Connection, *, is_sqlite: bool) -> int:
    """Insert/update tube-band exercises and link to resistance-band-2."""
    return seed_equipment_exercises(
        conn,
        is_sqlite=is_sqlite,
        items=load_band2_exercise_seed(),
        equipment_slug="resistance-band-2",
        marker_prefix="seed:resistance-band-2:",
    )