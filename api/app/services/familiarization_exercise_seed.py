"""Familiarization seed helpers: hide legacy rows; keep beginner BW/bar placeholders."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

MARKER_PREFIX = "seed:familiarization:"
BEGINNER_MARKER_PREFIX = "seed:beginner-bw:"

# bodyweight / bar placeholders used by the 60-day first_push_pull path
_BEGINNER_EXERCISES: tuple[dict[str, Any], ...] = (
    {
        "slug": "wall-push-up",
        "name_vi": "Chống đẩy tường",
        "name_en": "Wall Push-up",
        "legacy_en": "TAPTOT Wall Push-up",
        "muscle_slugs": ("chest-mid", "chest", "pectorals"),
        "movement_pattern": "h_push",
        "equipment_slug": None,
        "steps": [
            "Đứng cách tường khoảng nửa bước, hai bàn tay đặt trên tường ngang ngực, rộng bằng vai.",
            "Chân đứng vững, thân từ tai đến mắt cá thành một đường thẳng. Siết bụng.",
            "Gập khuỷu, hạ ngực về tường chậm; khuỷu chếch ra khoảng 45 độ.",
            "Đẩy tường ra để duỗi tay. Không nhún vai lên tai. Thở ra khi đẩy.",
        ],
        "tips": "Càng lùi chân ra sau bài càng nặng. Còn dễ thì chuyển sang chống đẩy tay trên ghế hoặc bàn.",
    },
    {
        "slug": "bar-inverted-row",
        "name_vi": "Kéo người nằm trên xà",
        "name_en": "Pull-up Bar Inverted Row",
        "legacy_en": "Inverted Row",
        "muscle_slugs": ("back-lats", "back", "lats"),
        "movement_pattern": "h_pull",
        "equipment_slug": "pull-up-bar",
        "steps": [
            "Nắm xà thấp, nằm ngửa bên dưới, thân thẳng, gót chống sàn.",
            "Kéo bả vai xuống xa tai rồi kéo ngực về xà, khuỷu sát sườn.",
            "Dừng ngắn khi ngực gần xà, hạ chậm đến tay gần thẳng.",
            "Giữ hông thẳng với vai; không để mông sệ.",
        ],
        "tips": "Muốn dễ hơn: đứng cao hơn (thân gần đứng). Muốn khó hơn: hạ xà hoặc đưa chân ra xa.",
    },
    {
        "slug": "hollow-body-hold",
        "name_vi": "Giữ thân rỗng",
        "name_en": "Hollow Body Hold",
        "muscle_slugs": ("abs", "core", "abdominals"),
        "movement_pattern": "core",
        "equipment_slug": None,
        "steps": [
            "Nằm ngửa, ép thắt lưng sát sàn (không còn khe hở).",
            "Tay với ra sau đầu, chân duỗi thấp. Nhấc vai và chân khỏi sàn một chút.",
            "Giữ hình thuyền, thở đều. Nếu lưng bật khỏi sàn, nâng chân cao hơn.",
            "Giữ đến hết thời gian; hạ khi không còn ép được lưng sát sàn.",
        ],
        "tips": "Ưu tiên lưng dán sàn hơn chân thấp. Người mới có thể gập gối 90 độ.",
    },
    {
        "slug": "backpack-good-morning",
        "name_vi": "Cúi người ôm balo",
        "name_en": "Backpack Good Morning",
        "muscle_slugs": ("hamstrings", "glutes", "back"),
        "movement_pattern": "hinge",
        "equipment_slug": None,
        "steps": [
            "Ôm balo trước ngực (an toàn hơn để sau gáy). Chân rộng bằng vai, gối hơi mềm.",
            "Siết bụng, lưng thẳng như một tấm ván.",
            "Đẩy hông ra sau, thân cúi đến khi sau đùi căng. Không cong lưng.",
            "Đẩy hông ra trước để đứng lên, siết mông ở đỉnh.",
        ],
        "tips": "Chỉ cúi đến mức lưng còn thẳng. Balo nhẹ trước; tăng dần khi động tác đã sạch.",
    },
    {
        "slug": "backpack-single-leg-rdl",
        "name_vi": "Gập hông một chân ôm balo",
        "name_en": "Backpack Single-leg Romanian Deadlift",
        "muscle_slugs": ("hamstrings", "glutes", "back"),
        "movement_pattern": "hinge",
        "equipment_slug": None,
        "steps": [
            "Đứng một chân trụ, gối trụ hơi mềm. Ôm balo trước ngực.",
            "Đẩy hông ra sau, chân sau duỗi ra sau, lưng thẳng, hông vuông.",
            "Hạ đến khi thân gần song song hoặc đến lúc mất thăng bằng có kiểm soát.",
            "Đẩy gót trụ xuống sàn để đứng lên, siết mông chân trụ.",
        ],
        "tips": "Giữ nhẹ ngón chân sau trên sàn nếu chưa giữ được thăng bằng một chân.",
    },
)

_REACTIVATE: tuple[tuple[str, str], ...] = (
    ("Kéo xà 1/3", "1/3 Pull-up"),
    # Live catalog row #820 — keep active for L2 elevated inverted row.
    ("Kéo người dưới bàn (chân trên ghế)", "Elevated Feet Table Inverted Row"),
)
# Prefer new names; fall back to legacy labels if a DB was never renamed.
_REACTIVATE_ALIASES: dict[tuple[str, str], tuple[tuple[str, str], ...]] = {
    ("Kéo xà 1/3", "1/3 Pull-up"): (
        ("Kéo xà bằng bả vai", "TAPTOT Scapular Pull-up"),
        ("Kéo xà bằng bả vai", "Scapular Pull-up"),
    ),
}


def _ensure_pull_up_bar(conn: Connection, *, is_sqlite: bool) -> int | None:
    row = conn.execute(
        text("SELECT id FROM equipment WHERE slug = 'pull-up-bar' LIMIT 1")
    ).fetchone()
    if row:
        eid = int(row[0])
        conn.execute(
            text("UPDATE equipment SET is_active = :active WHERE id = :id"),
            {"active": 1 if is_sqlite else True, "id": eid},
        )
        return eid
    if is_sqlite:
        conn.execute(
            text(
                """
                INSERT INTO equipment
                    (slug, name_vi, name_en, category, is_active, sort_order)
                VALUES
                    ('pull-up-bar', 'Xà đơn', 'Pull-up bar', 'home', 1, 40)
                """
            )
        )
        return int(conn.execute(text("SELECT last_insert_rowid()")).scalar())
    return int(
        conn.execute(
            text(
                """
                INSERT INTO equipment
                    (slug, name_vi, name_en, category, is_active, sort_order)
                VALUES
                    ('pull-up-bar', 'Xà đơn', 'Pull-up bar', 'home', TRUE, 40)
                RETURNING id
                """
            )
        ).scalar()
    )


def _muscle_id(conn: Connection, slugs: tuple[str, ...]) -> int | None:
    for slug in slugs:
        row = conn.execute(
            text("SELECT id FROM muscle_groups WHERE slug = :slug LIMIT 1"),
            {"slug": slug},
        ).fetchone()
        if row:
            return int(row[0])
    row = conn.execute(text("SELECT id FROM muscle_groups ORDER BY id LIMIT 1")).fetchone()
    return int(row[0]) if row else None


def _link_bar(conn: Connection, *, exercise_id: int, equipment_id: int) -> None:
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


def _find_exercise_id(conn: Connection, item: dict[str, Any]) -> int | None:
    marker = f"{BEGINNER_MARKER_PREFIX}{item['slug']}"
    row = conn.execute(
        text("SELECT id FROM exercises WHERE notes_vi = :marker LIMIT 1"),
        {"marker": marker},
    ).fetchone()
    if row:
        return int(row[0])
    legacy_marker = item.get("legacy_marker")
    if legacy_marker:
        row = conn.execute(
            text("SELECT id FROM exercises WHERE notes_vi = :marker LIMIT 1"),
            {"marker": legacy_marker},
        ).fetchone()
        if row:
            return int(row[0])
    legacy_slug = f"{MARKER_PREFIX}{item['slug']}"
    row = conn.execute(
        text("SELECT id FROM exercises WHERE notes_vi = :marker LIMIT 1"),
        {"marker": legacy_slug},
    ).fetchone()
    if row:
        return int(row[0])
    names = [item["name_en"]]
    if item.get("legacy_en"):
        names.append(str(item["legacy_en"]))
    for name_en in names:
        row = conn.execute(
            text(
                "SELECT id FROM exercises "
                "WHERE name_vi = :name_vi OR name_en = :name_en "
                "ORDER BY id LIMIT 1"
            ),
            {"name_vi": item["name_vi"], "name_en": name_en},
        ).fetchone()
        if row:
            return int(row[0])
    return None


def _upsert_beginner_exercise(
    conn: Connection,
    *,
    is_sqlite: bool,
    item: dict[str, Any],
    bar_id: int | None,
) -> int:
    muscle_id = _muscle_id(conn, tuple(item["muscle_slugs"]))
    if muscle_id is None:
        return 0
    if item.get("equipment_slug") == "pull-up-bar" and bar_id is None:
        return 0

    marker = f"{BEGINNER_MARKER_PREFIX}{item['slug']}"
    eid = _find_exercise_id(conn, item)
    now = datetime.now(UTC)
    active = 1 if is_sqlite else True
    steps_json = json.dumps(item["steps"], ensure_ascii=False)
    params = {
        "name_vi": item["name_vi"],
        "name_en": item["name_en"],
        "mg": muscle_id,
        "pattern": item["movement_pattern"],
        "steps": steps_json,
        "tips": item.get("tips") or "Tập chậm, còn dư 3–4 cái.",
        "marker": marker,
        "active": active,
        "updated_at": now,
    }

    if eid is not None:
        params["id"] = eid
        if is_sqlite:
            conn.execute(
                text(
                    """
                    UPDATE exercises SET
                        name_vi = :name_vi,
                        name_en = :name_en,
                        muscle_group_id = :mg,
                        exercise_type = 'main',
                        movement_role = 'compound',
                        movement_pattern = :pattern,
                        venue = 'both',
                        difficulty = 1,
                        difficulty_label = '1',
                        instruction_steps_vi = :steps,
                        tips_vi = :tips,
                        notes_vi = :marker,
                        is_active = :active,
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
                        name_vi = :name_vi,
                        name_en = :name_en,
                        muscle_group_id = :mg,
                        exercise_type = 'main',
                        movement_role = 'compound',
                        movement_pattern = :pattern,
                        venue = 'both',
                        difficulty = 1,
                        difficulty_label = '1',
                        instruction_steps_vi = CAST(:steps AS json),
                        tips_vi = :tips,
                        notes_vi = :marker,
                        is_active = :active,
                        updated_at = :updated_at
                    WHERE id = :id
                    """
                ),
                params,
            )
    else:
        params["created_at"] = now
        if is_sqlite:
            conn.execute(
                text(
                    """
                    INSERT INTO exercises (
                        name_vi, name_en, muscle_group_id, exercise_type,
                        movement_role, movement_pattern, venue, difficulty,
                        difficulty_label, instruction_steps_vi, tips_vi, notes_vi,
                        is_active, created_at, updated_at
                    ) VALUES (
                        :name_vi, :name_en, :mg, 'main',
                        'compound', :pattern, 'both', 1,
                        '1', :steps, :tips, :marker,
                        :active, :created_at, :updated_at
                    )
                    """
                ),
                params,
            )
            eid = int(conn.execute(text("SELECT last_insert_rowid()")).scalar())
        else:
            eid = int(
                conn.execute(
                    text(
                        """
                        INSERT INTO exercises (
                            name_vi, name_en, muscle_group_id, exercise_type,
                            movement_role, movement_pattern, venue, difficulty,
                            difficulty_label, instruction_steps_vi, tips_vi, notes_vi,
                            is_active, created_at, updated_at
                        ) VALUES (
                            :name_vi, :name_en, :mg, 'main',
                            'compound', :pattern, 'both', 1,
                            '1', CAST(:steps AS json), :tips, :marker,
                            :active, :created_at, :updated_at
                        )
                        RETURNING id
                        """
                    ),
                    params,
                ).scalar()
            )

    if item.get("equipment_slug") == "pull-up-bar" and bar_id is not None:
        _link_bar(conn, exercise_id=int(eid), equipment_id=int(bar_id))
    else:
        conn.execute(
            text("DELETE FROM exercise_equipment WHERE exercise_id = :id"),
            {"id": int(eid)},
        )
    return 1


def ensure_wall_pushup(conn: Connection, *, is_sqlite: bool) -> int:
    """Back-compat: ensure the wall push-up placeholder exists."""
    bar_id = _ensure_pull_up_bar(conn, is_sqlite=is_sqlite)
    return _upsert_beginner_exercise(
        conn, is_sqlite=is_sqlite, item=_BEGINNER_EXERCISES[0], bar_id=bar_id
    )


def _activate_existing_home_moves(conn: Connection, *, is_sqlite: bool) -> int:
    total = 0
    active = 1 if is_sqlite else True
    for name_vi, name_en in _REACTIVATE:
        candidates = ((name_vi, name_en),) + _REACTIVATE_ALIASES.get(
            (name_vi, name_en), ()
        )
        row = None
        for cand_vi, cand_en in candidates:
            row = conn.execute(
                text(
                    "SELECT id FROM exercises "
                    "WHERE name_vi = :name_vi OR name_en = :name_en "
                    "ORDER BY id LIMIT 1"
                ),
                {"name_vi": cand_vi, "name_en": cand_en},
            ).fetchone()
            if row:
                break
        if not row:
            continue
        conn.execute(
            text(
                "UPDATE exercises SET is_active = :active, notes_vi = :marker, "
                "name_vi = :name_vi, name_en = :name_en "
                "WHERE id = :id"
            ),
            {
                "active": active,
                "marker": f"{BEGINNER_MARKER_PREFIX}reactivate",
                "name_vi": name_vi,
                "name_en": name_en,
                "id": int(row[0]),
            },
        )
        total += 1
    return total


def _deactivate_retired_placeholders(conn: Connection, *, is_sqlite: bool) -> None:
    """Hide retired familiarization moves (chin-hold / backpack RDL)."""
    inactive = 0 if is_sqlite else False
    conn.execute(
        text(
            "UPDATE exercises SET is_active = :inactive "
            "WHERE notes_vi IN (:beginner, :legacy) "
            "OR name_en IN (:en1, :en2)"
        ),
        {
            "inactive": inactive,
            "beginner": f"{BEGINNER_MARKER_PREFIX}chin-hold-negative",
            "legacy": f"{MARKER_PREFIX}flexed-arm-hang",
            "en1": "Chin-over-bar Hold Negative",
            "en2": "TAPTOT Flexed Arm Hang",
        },
    )
    conn.execute(
        text(
            "UPDATE exercises SET is_active = :inactive "
            "WHERE name_vi = :name_vi OR name_en = :name_en"
        ),
        {
            "inactive": inactive,
            "name_vi": "Romanian deadlift ba lô",
            "name_en": "Backpack Romanian Deadlift",
        },
    )


def _rename_trail_run_to_endurance(conn: Connection) -> None:
    """Display Trail Run as endurance run / brisk walk."""
    conn.execute(
        text(
            "UPDATE exercises SET name_vi = :name_vi "
            "WHERE name_en = :name_en "
            "OR name_vi IN (:old1, :old2)"
        ),
        {
            "name_vi": "Chạy bền/Đi bộ nhanh",
            "name_en": "Trail Run",
            "old1": "Chạy địa hình",
            "old2": "Chạy bền",
        },
    )


def ensure_beginner_placeholders(conn: Connection, *, is_sqlite: bool) -> int:
    bar_id = _ensure_pull_up_bar(conn, is_sqlite=is_sqlite)
    _deactivate_retired_placeholders(conn, is_sqlite=is_sqlite)
    _rename_trail_run_to_endurance(conn)
    total = _activate_existing_home_moves(conn, is_sqlite=is_sqlite)
    for item in _BEGINNER_EXERCISES:
        total += _upsert_beginner_exercise(
            conn, is_sqlite=is_sqlite, item=item, bar_id=bar_id
        )
    return total


def deactivate_familiarization_exercises(conn: Connection, *, is_sqlite: bool) -> int:
    """Hide legacy seed:familiarization:* rows; keep beginner placeholders active."""
    result = conn.execute(
        text(
            "UPDATE exercises SET is_active = :inactive "
            "WHERE notes_vi LIKE :marker"
        ),
        {
            "inactive": 0 if is_sqlite else False,
            "marker": f"{MARKER_PREFIX}%",
        },
    )
    ensure_beginner_placeholders(conn, is_sqlite=is_sqlite)
    return int(result.rowcount or 0)


# Back-compat alias used by older imports/tests.
def seed_familiarization_exercises(conn: Connection, *, is_sqlite: bool) -> int:
    return deactivate_familiarization_exercises(conn, is_sqlite=is_sqlite)
