"""Keep-list for exercises that may exist without a video file."""

from __future__ import annotations

from sqlalchemy import bindparam, text
from sqlalchemy.engine import Connection

# Hidden from public catalog; rows stay in DB (plans may still reference them).
RETIRED_CATALOG_NAME_EN = frozenset(
    {
        "Inverted Row",
        "Pull-up Bar Inverted Row",
        "Band Pull-Apart",
        "Band Good Morning",
        "Band Hip Thrust",
        "Band Pallof Press",
        "Band Assisted Pull-Up",
        "Band Deadlift",
        "Barbell Banded Back Squat",
        "Ring L-Sit",
        "Skin the Cat",
        "Ring Face-down Row",
        "Chin-over-bar Hold Negative",
        "Barbell Spinal Jefferson Curl",
        "Kettlebell Spinal Jefferson Curl",
        "Dumbbell Spinal Jefferson Curl",
    }
)

# Library rows allowed to stay without video_url (may still be inactive if retired).
KEEP_NO_VIDEO_NAME_EN = frozenset(
    {
        "Band Lunge",
        "Band Glute Kickback",
        "Band Tricep Kickback",
        "Band Lateral Walk",
        "Band Overhead Tricep Extension",
        "Band Chest Press",
        "Band Upright Row",
        "Band Pull-Apart",
        "Band Chest Fly",
        "Band Deadlift",
        "Band Clamshell",
        "Band Row",
        "Band Seated Pulldown",
        "Band Squat",
        "Band Overhead Press",
        "Band Curl",
        "Band Wood Chopper",
        "Band Pallof Press",
        "Band Good Morning",
        "Band Glute Bridge",
        "Band External Rotation",
        "Band Lateral Raise",
        "Band Leg Curl",
        "Band Calf Raise",
        "Band Kneeling Pulldown",
        "Chin-over-bar Hold Negative",
        "Ring Hamstring Curl",
        "Ring Hanging Knee Raise",
        "Ring Hanging Leg Raise",
        "Ring L-Sit",
        "Ring Dip",
        "Ring Hold",
        "Skin the Cat",
        "Ring Face-down Row",
        "Band Seated Row",
        "Bulgarian Ring Squat",
        "Pike Push-Up",
        "Wall Push-up",
        "Bent-Over Backpack Row",
        "One-Arm Backpack Row",
    }
)


def _has_table(conn: Connection, name: str) -> bool:
    if conn.dialect.name == "sqlite":
        row = conn.execute(
            text("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = :n"),
            {"n": name},
        ).fetchone()
        return bool(row)
    row = conn.execute(
        text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = current_schema() AND table_name = :n"
        ),
        {"n": name},
    ).fetchone()
    return bool(row)


def _exercise_columns(conn: Connection) -> set[str]:
    if not _has_table(conn, "exercises"):
        return set()
    return set(conn.execute(text("SELECT * FROM exercises LIMIT 0")).keys())


def deactivate_retired_catalog_exercises(conn: Connection, *, is_sqlite: bool) -> int:
    """Force-hide retired catalog names after seed/purge/reactivate."""
    if "is_active" not in _exercise_columns(conn):
        return 0
    names = sorted(RETIRED_CATALOG_NAME_EN)
    result = conn.execute(
        text("UPDATE exercises SET is_active = :inactive WHERE name_en IN :names").bindparams(
            bindparam("names", expanding=True)
        ),
        {"inactive": 0 if is_sqlite else False, "names": names},
    )
    return int(result.rowcount or 0)


def purge_exercises_missing_video(conn: Connection, *, is_sqlite: bool) -> int:
    """Activate keep-list rows; delete every other exercise with empty video_url."""
    cols = _exercise_columns(conn)
    if "video_url" not in cols:
        return 0
    active = 1 if is_sqlite else True
    keep_live = sorted(KEEP_NO_VIDEO_NAME_EN - RETIRED_CATALOG_NAME_EN)
    protected = sorted(KEEP_NO_VIDEO_NAME_EN | RETIRED_CATALOG_NAME_EN)
    if keep_live:
        conn.execute(
            text("UPDATE exercises SET is_active = :active WHERE name_en IN :names").bindparams(
                bindparam("names", expanding=True)
            ),
            {"active": active, "names": keep_live},
        )
    doomed = conn.execute(
        text(
            """
            SELECT id FROM exercises
            WHERE NULLIF(TRIM(COALESCE(video_url, '')), '') IS NULL
              AND (name_en IS NULL OR name_en NOT IN :names)
            """
        ).bindparams(bindparam("names", expanding=True)),
        {"names": protected},
    ).fetchall()
    dropped = 0
    for row in doomed:
        drop_id = int(row[0])
        if _has_table(conn, "user_daily_plan_exercises"):
            conn.execute(
                text("DELETE FROM user_daily_plan_exercises WHERE exercise_id = :id"),
                {"id": drop_id},
            )
        if _has_table(conn, "exercise_equipment"):
            conn.execute(
                text("DELETE FROM exercise_equipment WHERE exercise_id = :id"),
                {"id": drop_id},
            )
        conn.execute(text("DELETE FROM exercises WHERE id = :id"), {"id": drop_id})
        dropped += 1
    deactivate_retired_catalog_exercises(conn, is_sqlite=is_sqlite)
    return dropped
