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
        "Band Pallof Press",
        "Band Assisted Pull-Up",
        "Band Deadlift",
        "Band Overhead Tricep Extension",
        "Band Calf Raise",
        "Ring Hanging Knee Raise",
        "Barbell Banded Back Squat",
        "Ring L-Sit",
        "Skin the Cat",
        "Ring Face-down Row",
        "Chin-over-bar Hold Negative",
        "Band Clamshell",
        "Barbell Spinal Jefferson Curl",
        "Kettlebell Spinal Jefferson Curl",
        "Dumbbell Spinal Jefferson Curl",
        "Hiking",
        "Swim Kick Drill",
        "Swim Pull Drill",
        "Breaststroke Swim",
        "Freestyle Swim",
        "Butterfly Swim",
        "Swim Sprint Intervals",
        "Running Cooldown",
        "Good Mornings",
        "Neck Curl",
        "Towel Slide Leg Curl",
        "Neck Extension",
        "Back Extension",
        "Decline Crunch",
        "Single Legged Romanian Deadlifts",
        "Bodyweight Deadlift",
        "Romanian Deadlift Hamstring Sweeps",
        "Captain's Chair Knee Raise",
        "Backstroke Swim",
        "Single-Leg Step-Down",
        "Bodyweight Elevated Push Up",
        "Stability Ball Leg Curl",
        "B-Stance Hip Thrust",
        "Reverse Hyperextension",
        "B-stance Back Extension",
        "Parallel Bar Dips",
        "Wall Ball",
        "Weighted Pull Ups",
        "Bodyweight Reverse Lunge",
        "Forward Lunge",
        "Dumbbell Row Unilateral",
        "Dumbbell Feet Elevated Glute Bridge",
        "Dumbbell Goblet Forward Lunge",
        "Dumbbell Preacher Curl",
        "Dumbbell Wrist Curl",
        "Dumbbell Standing Single Arm Hammer Curl",
        "Dumbbell Standing Single Arm Curl",
        "Dumbbell Decline Skullcrusher",
        "Single-Arm Dumbbell Overhead Press",
        "Dumbbell Single Arm Chest Press",
        "Dumbbell Seated Shrug",
        "Dumbbell Superman",
        "Dumbbell Goblet Split Squat",
        "Dumbbell Figure Four Heels Elevated Hip Thrust",
        "Cuban Press",
        "Front-Foot-Elevated Split Squat",
        "Dumbbell Cross Body Romanian Deadlift",
        "Deficit Dumbbell Romanian Deadlift",
        "Kickstand Dumbbell Romanian Deadlift",
        "Dumbbell Single Arm Clean And Press",
        "Single-Leg Dumbbell Romanian Deadlift (Deficit)",
        "Bodyweight Donkey Calf Raise",
        "Neutral-Grip Pull-Up",
        "Wide-Grip Pull-Up",
        "Nordic Hamstring Curl",
        "Band Single Arm Lateral Raise",
        "Dumbbell Incline Hammer Curl",
        "Dumbbell Decline Bench Press",
        "Tate Press",
        "Dumbbell Decline Chest Fly",
        "Arnold Press",
        "Bodyweight Spinal Jefferson Curl",
        "Bodyweight Hip Abduction",
        "Hand Plank",
        "Spider Curl",
        "Dumbbell Heels Elevated Hip Thrust",
        "Dumbbell Wrist Extension",
        "Decline Sit-Up",
        "Dumbbell Laying Reverse Fly",
        "Dumbbell Incline Front Raise",
        "Dumbbell Single Leg Calf Raise",
        "Dumbbell Goblet Alternating Curtsy Lunge",
        "Zottman Curl",
        "Dumbbell Back Extension",
        "Z Press",
        "Dumbbell Overhead Squat",
        "Single-Leg Dumbbell Romanian Deadlift",
    }
)

# Public catalog stays active only for these gear filters (plus unlinked bodyweight).
HOME_GEAR_SLUGS = (
    "dumbbell",
    "resistance-band",
    "resistance-band-1",
    "resistance-band-2",
    "day-mini-band",
    "pull-up-bar",
    "gymnastic-rings",
)

# Library rows allowed to stay without video_url (may still be inactive if retired).
KEEP_NO_VIDEO_NAME_EN = frozenset(
    {
        "Band Lunge",
        "Band Glute Kickback",
        "Band Hip Thrust",
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
    """Activate keep-list rows; delete other catalog exercises with empty video_url.

    Rows owned by an HLV stay, including ones that are already on a plan.
    """
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
    # HLV private rows often have no clip yet. A restart must not drop them
    # or the plan lines that still name them.
    owner_clause = " AND owner_user_id IS NULL" if "owner_user_id" in cols else ""
    doomed = conn.execute(
        text(
            f"""
            SELECT id FROM exercises
            WHERE NULLIF(TRIM(COALESCE(video_url, '')), '') IS NULL
              AND (name_en IS NULL OR name_en NOT IN :names)
              {owner_clause}
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


def deactivate_exercises_outside_home_gear(conn: Connection, *, is_sqlite: bool) -> int:
    """Hide public exercises that are not bodyweight or the five home-gear filters.

    An exercise linked to both a gym machine and a dumbbell stays, because it
    still appears under tạ đơn. Trainer-owned rows are left alone.
    """
    cols = _exercise_columns(conn)
    if "is_active" not in cols or not _has_table(conn, "exercise_equipment"):
        return 0
    if not _has_table(conn, "equipment"):
        return 0
    owner_clause = " AND e.owner_user_id IS NULL" if "owner_user_id" in cols else ""
    inactive = 0 if is_sqlite else False
    rows = conn.execute(
        text(
            f"""
            SELECT e.id
            FROM exercises e
            WHERE EXISTS (
                SELECT 1 FROM exercise_equipment ee
                WHERE ee.exercise_id = e.id
            )
            AND NOT EXISTS (
                SELECT 1
                FROM exercise_equipment ee
                JOIN equipment eq ON eq.id = ee.equipment_id
                WHERE ee.exercise_id = e.id
                  AND lower(eq.slug) IN :slugs
            )
            {owner_clause}
            """
        ).bindparams(bindparam("slugs", expanding=True)),
        {"slugs": list(HOME_GEAR_SLUGS)},
    ).fetchall()
    ids = [int(row[0]) for row in rows]
    if not ids:
        return 0
    result = conn.execute(
        text("UPDATE exercises SET is_active = :inactive WHERE id IN :ids").bindparams(
            bindparam("ids", expanding=True)
        ),
        {"inactive": inactive, "ids": ids},
    )
    return int(result.rowcount or 0)
