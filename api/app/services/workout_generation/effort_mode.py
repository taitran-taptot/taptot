"""Classify how an exercise is prescribed: repetitions, timed hold, or continuous work."""

from __future__ import annotations

from typing import Any

HOLD_NAME_KEYS = (
    "plank",
    "hollow hold",
    "wall sit",
    "dead hang",
    "active hang",
    "hang plank",
    "treo người",
    "treo nguoi",
    "treo thả",
    "chống khuỷu",
    "chong khuyu",
    "chống người",
    "chong nguoi",
    "giữ ",
    "giu ",
)
# Pull-up / chin-up / row are reps even if the Vietnamese name mentions xà / treo.
REP_OVERRIDE_KEYS = (
    "pull-up",
    "pullup",
    "pull up",
    "chin-up",
    "chinup",
    "chin up",
    "kéo xà",
    "keo xa",
    "hít xà",
    "hit xa",
    "ring row",
    "inverted row",
    "push-up",
    "push up",
    "chống đẩy",
    "chong day",
)


def exercise_effort_mode(
    exercise: Any = None,
    *,
    name_vi: str | None = None,
    name_en: str | None = None,
    movement_role: str | None = None,
    plan_section: str | None = None,
) -> str:
    """Return ``reps``, ``hold``, or ``continuous`` without requiring a schema migration."""
    if exercise is not None:
        if isinstance(exercise, dict):
            name_vi = name_vi or exercise.get("name_vi")
            name_en = name_en or exercise.get("name_en")
            movement_role = movement_role or exercise.get("movement_role")
        else:
            name_vi = name_vi or getattr(exercise, "name_vi", None)
            name_en = name_en or getattr(exercise, "name_en", None)
            movement_role = movement_role or getattr(exercise, "movement_role", None)

    section = str(plan_section or "").strip().lower()
    role = str(movement_role or "").strip().lower()
    if section == "cardio" or role in {"cardio", "conditioning"}:
        return "continuous"

    names = f"{name_vi or ''} {name_en or ''}".strip().lower()
    hang = any(k in names for k in ("dead hang", "treo thả", "treo tha", "plank", "wall sit"))
    pullupish = any(key in names for key in REP_OVERRIDE_KEYS) or (
        ("xà" in names or "xa don" in names)
        and any(k in names for k in ("kéo", "keo", "hít", "hit", "chin", "pull"))
    )
    if pullupish and not hang:
        return "reps"
    if any(key in names for key in HOLD_NAME_KEYS):
        return "hold"
    if section in {"warmup", "cooldown"} and role in {"mobility", "warmup", "cooldown", ""}:
        return "hold"
    if section in {"warmup", "cooldown"} and role not in {
        "compound",
        "isolation",
        "resistance",
    }:
        return "hold"
    return "reps"
