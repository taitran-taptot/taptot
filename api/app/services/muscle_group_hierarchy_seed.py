"""Seed and maintain muscle_groups hierarchy from seeds/muscle_groups_hierarchy.json."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.services.exercise_muscle_region import classify_region_slug

PROJECT_ROOT = Path(__file__).resolve().parents[3]
HIERARCHY_SEED = PROJECT_ROOT / "seeds" / "muscle_groups_hierarchy.json"

PARENT_LABELS = {
    "chest": ("Ngực", "Chest"),
    "back": ("Lưng", "Back"),
    "shoulders": ("Vai", "Shoulders"),
    "core": ("Bụng", "Core"),
    "legs": ("Chân", "Legs"),
    "arms": ("Tay", "Arms"),
    "cardio": ("Cardio", "Cardio"),
    "stretch": ("Giãn cơ", "Stretch"),
}

LEAF_LABELS = {
    "quads": ("Đùi trước", "Quadriceps"),
    "hamstrings": ("Đùi sau", "Hamstrings"),
    "glutes": ("Mông", "Glutes"),
    "calves": ("Bắp chân", "Calves"),
    "biceps": ("Bắp tay trước", "Biceps"),
    "triceps": ("Bắp tay sau", "Triceps"),
    "forearms": ("Cẳng tay", "Forearms"),
    "co-dui-truoc": ("Đùi trước", "Quads"),
    "co-dui-sau": ("Đùi sau", "Hamstrings"),
    "co-mong": ("Mông", "Glutes"),
    "co-bap-chan": ("Bắp chân", "Calves"),
    "co-tay-truoc": ("Bắp tay trước", "Biceps"),
    "co-tay-sau": ("Bắp tay sau", "Triceps"),
    "chest-mid": ("Ngực giữa", "Mid chest"),
    "core-upper": ("Bụng trên", "Upper abs"),
    "back-lats": ("Xô (lat)", "Lats"),
    "back-lower": ("Thắt lưng", "Lower back"),
    "shoulders-lateral": ("Vai giữa", "Lateral delts"),
    "shoulders-traps": ("Cầu vai", "Traps"),
}


def load_hierarchy_seed() -> dict[str, Any]:
    return json.loads(HIERARCHY_SEED.read_text(encoding="utf-8"))


def _upsert_group(
    conn: Connection,
    *,
    slug: str,
    name_vi: str,
    name_en: str | None,
    sort_order: int,
    parent_id: int | None = None,
    is_filter_only: bool = False,
    is_sqlite: bool,
) -> int:
    row = conn.execute(
        text("SELECT id FROM muscle_groups WHERE slug = :slug"),
        {"slug": slug},
    ).fetchone()
    filter_val = (1 if is_filter_only else 0) if is_sqlite else is_filter_only
    if row:
        conn.execute(
            text(
                "UPDATE muscle_groups SET name_vi = :name_vi, name_en = :name_en, "
                "sort_order = :sort_order, parent_id = :parent_id, is_filter_only = :filter_only "
                "WHERE id = :id"
            ),
            {
                "name_vi": name_vi,
                "name_en": name_en,
                "sort_order": sort_order,
                "parent_id": parent_id,
                "filter_only": filter_val,
                "id": int(row[0]),
            },
        )
        return int(row[0])
    if is_sqlite:
        conn.execute(
            text(
                "INSERT INTO muscle_groups (slug, name_vi, name_en, sort_order, parent_id, is_filter_only) "
                "VALUES (:slug, :name_vi, :name_en, :sort_order, :parent_id, :filter_only)"
            ),
            {
                "slug": slug,
                "name_vi": name_vi,
                "name_en": name_en,
                "sort_order": sort_order,
                "parent_id": parent_id,
                "filter_only": filter_val,
            },
        )
        new_id = conn.execute(text("SELECT last_insert_rowid()")).scalar()
        return int(new_id)
    new_id = conn.execute(
        text(
            "INSERT INTO muscle_groups (slug, name_vi, name_en, sort_order, parent_id, is_filter_only) "
            "VALUES (:slug, :name_vi, :name_en, :sort_order, :parent_id, :filter_only) "
            "RETURNING id"
        ),
        {
            "slug": slug,
            "name_vi": name_vi,
            "name_en": name_en,
            "sort_order": sort_order,
            "parent_id": parent_id,
            "filter_only": filter_val,
        },
    ).scalar()
    return int(new_id)


def seed_muscle_group_hierarchy(conn: Connection, *, is_sqlite: bool) -> None:
    data = load_hierarchy_seed()
    slug_to_id: dict[str, int] = {}

    for parent in data.get("parents", []):
        pid = _upsert_group(
            conn,
            slug=str(parent["slug"]),
            name_vi=str(parent["name_vi"]),
            name_en=parent.get("name_en"),
            sort_order=int(parent.get("sort_order", 0)),
            parent_id=None,
            is_filter_only=bool(parent.get("is_filter_only", False)),
            is_sqlite=is_sqlite,
        )
        slug_to_id[str(parent["slug"])] = pid
        for child in parent.get("children", []):
            cid = _upsert_group(
                conn,
                slug=str(child["slug"]),
                name_vi=str(child["name_vi"]),
                name_en=child.get("name_en"),
                sort_order=int(child.get("sort_order", 0)),
                parent_id=pid,
                is_filter_only=False,
                is_sqlite=is_sqlite,
            )
            slug_to_id[str(child["slug"])] = cid

    for slug, (name_vi, name_en) in PARENT_LABELS.items():
        if slug in slug_to_id:
            continue
        slug_to_id[slug] = _upsert_group(
            conn,
            slug=slug,
            name_vi=name_vi,
            name_en=name_en,
            sort_order=70 if slug == "cardio" else 80 if slug == "stretch" else 90,
            parent_id=None,
            is_filter_only=False,
            is_sqlite=is_sqlite,
        )

    legs_id = slug_to_id.get("legs")
    if legs_id:
        for item in data.get("leg_children", []):
            slug = str(item["slug"])
            row = conn.execute(
                text("SELECT id FROM muscle_groups WHERE slug = :slug"),
                {"slug": slug},
            ).fetchone()
            if not row:
                continue
            sort_order = int(item.get("sort_order", 50))
            conn.execute(
                text(
                    "UPDATE muscle_groups SET parent_id = :pid, sort_order = :sort_order "
                    "WHERE id = :id"
                ),
                {"pid": legs_id, "sort_order": sort_order, "id": int(row[0])},
            )
            slug_to_id[slug] = int(row[0])

    arms_id = slug_to_id.get("arms")
    if arms_id:
        for item in data.get("arm_children", []):
            slug = str(item["slug"])
            row = conn.execute(
                text("SELECT id FROM muscle_groups WHERE slug = :slug"),
                {"slug": slug},
            ).fetchone()
            if not row:
                continue
            sort_order = int(item.get("sort_order", 60))
            conn.execute(
                text(
                    "UPDATE muscle_groups SET parent_id = :pid, sort_order = :sort_order "
                    "WHERE id = :id"
                ),
                {"pid": arms_id, "sort_order": sort_order, "id": int(row[0])},
            )
            slug_to_id[slug] = int(row[0])

    _relabel_known_leaves(conn)
    _fix_mojibake_labels(conn)


def _relabel_known_leaves(conn: Connection) -> None:
    labels = {**PARENT_LABELS, **LEAF_LABELS}
    for slug, (name_vi, name_en) in labels.items():
        conn.execute(
            text(
                "UPDATE muscle_groups SET name_vi = :name_vi, name_en = :name_en "
                "WHERE slug = :slug"
            ),
            {"name_vi": name_vi, "name_en": name_en, "slug": slug},
        )


def _fix_mojibake(value: str) -> str:
    if not value or not any(ch in value for ch in "ÃÂÆÐ"):
        return value
    for enc in ("latin-1", "cp1252"):
        try:
            fixed = value.encode(enc).decode("utf-8")
        except (UnicodeDecodeError, UnicodeEncodeError):
            continue
        if "Ã" not in fixed:
            return fixed
    return value


def _fix_mojibake_labels(conn: Connection) -> None:
    rows = conn.execute(text("SELECT id, name_vi, name_en FROM muscle_groups")).mappings().all()
    for row in rows:
        vi = _fix_mojibake(str(row["name_vi"] or ""))
        en = _fix_mojibake(str(row["name_en"] or ""))
        if vi == row["name_vi"] and en == (row["name_en"] or ""):
            continue
        conn.execute(
            text("UPDATE muscle_groups SET name_vi = :vi, name_en = :en WHERE id = :id"),
            {"vi": vi, "en": en or None, "id": int(row["id"])},
        )


def remap_exercises_to_leaf_regions(conn: Connection, *, is_sqlite: bool) -> int:
    """Reclassify exercises on filter-only or coarse parent slugs."""
    if is_sqlite:
        cols = {
            r[1] for r in conn.execute(text("PRAGMA table_info(exercises)")).fetchall()
        }
    else:
        rows = conn.execute(
            text(
                """
                SELECT column_name FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'exercises'
                """
            )
        ).fetchall()
        cols = {str(r[0]) for r in rows}

    if "muscle_group_id" not in cols:
        return 0

    select_cols = ["e.id", "e.name_vi", "e.muscle_group_id"]
    if "name_en" in cols:
        select_cols.append("e.name_en")
    if "movement_pattern" in cols:
        select_cols.append("e.movement_pattern")
    if "movement_role" in cols:
        select_cols.append("e.movement_role")

    rows = conn.execute(
        text(
            f"""
            SELECT {", ".join(select_cols)}, mg.slug AS old_slug
            FROM exercises e
            JOIN muscle_groups mg ON mg.id = e.muscle_group_id
            """
        )
    ).mappings().all()
    if not rows:
        return 0

    slug_rows = conn.execute(text("SELECT id, slug FROM muscle_groups")).fetchall()
    slug_to_id = {str(r[1]): int(r[0]) for r in slug_rows}
    updated = 0
    for row in rows:
        result = classify_region_slug(
            name_vi=row.get("name_vi"),
            name_en=row.get("name_en"),
            old_slug=str(row.get("old_slug") or ""),
            movement_pattern=row.get("movement_pattern"),
            movement_role=row.get("movement_role"),
        )
        target_id = slug_to_id.get(result.new_slug)
        if target_id is None:
            continue
        if int(target_id) == int(row["muscle_group_id"]):
            continue
        conn.execute(
            text("UPDATE exercises SET muscle_group_id = :mg WHERE id = :id"),
            {"mg": target_id, "id": int(row["id"])},
        )
        updated += 1
    return updated
