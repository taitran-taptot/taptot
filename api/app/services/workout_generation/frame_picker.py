"""Pick workout schedule frame — Master spec (runtime) or legacy DB."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.services.exercise_prescription import clamp_experience_level
from app.services.schedule_spec_master import ResolvedFrame, resolve_master_frame


def pick_master_frame(
    db: Session,  # noqa: ARG001 — kept for API symmetry
    *,
    experience_level: int | None,
    sessions_per_week: int,
    gender: str,
    location: str,
    no_equipment: bool,
    week_code: str | None = None,
) -> tuple[ResolvedFrame, list]:
    """Resolve week template from Master matrix (gender × location × home equip)."""
    level = clamp_experience_level(experience_level)
    frame = resolve_master_frame(
        experience_level=level,
        sessions_per_week=sessions_per_week,
        gender=gender,
        location=location,
        no_equipment=no_equipment,
        week_code=week_code,
    )
    return frame, list(frame.days)
