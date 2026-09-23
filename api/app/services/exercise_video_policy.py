"""Keep-list for exercises that may exist without a video file."""

from __future__ import annotations

from sqlalchemy import bindparam, text
from sqlalchemy.engine import Connection

# Library rows allowed to stay live without video_url.
KEEP_NO_VIDEO_NAME_EN = frozenset(
    {
        "Band Push-Up",
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
        "Chin-over-bar Hold Negative",
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


def purge_exercises_missing_video(conn: Connection, *, is_sqlite: bool) -> int:
    """Activate keep-list rows; delete every other exercise with empty video_url."""
    cols = _exercise_columns(conn)
    if "video_url" not in cols:
        return 0
    active = 1 if is_sqlite else True
    names = sorted(KEEP_NO_VIDEO_NAME_EN)
    conn.execute(
        text("UPDATE exercises SET is_active = :active WHERE name_en IN :names").bindparams(
            bindparam("names", expanding=True)
        ),
        {"active": active, "names": names},
    )
    doomed = conn.execute(
        text(
            """
            SELECT id FROM exercises
            WHERE NULLIF(TRIM(COALESCE(video_url, '')), '') IS NULL
              AND (name_en IS NULL OR name_en NOT IN :names)
            """
        ).bindparams(bindparam("names", expanding=True)),
        {"names": names},
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
    return dropped
