"""Seed the public fixed Nhập môn plan at /lich/nhapmon."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.models.entities import (
    Exercise,
    MuscleGroup,
    UserDailyPlan,
    UserDailyPlanDay,
    UserDailyPlanExercise,
)
from app.services.exercise_copy_seed import load_exercise_copy_seed, mistakes_text

logger = logging.getLogger(__name__)

NHAPMON_SHARE_TOKEN = "nhapmon"
NHAPMON_EXPECTED_DAYS = 28
NHAPMON_MIN_TRAIN_DAYS = 12
NHAPMON_MARKER = "seed:nhapmon-household:"

_HOUSEHOLD_ROWS = (
    {
        "name_en": "Wall Push-up",
        "name_vi": "Chống đẩy tường",
        "pattern": "h_push",
        "muscle_slugs": ("chest", "chest-mid", "pectorals"),
        "media_slug": "wall-push-up",
    },
    {
        "name_en": "Bent-Over Backpack Row",
        "name_vi": "Chèo cặp sách hai tay",
        "pattern": "h_pull",
        "muscle_slugs": ("back", "back-lats", "lats"),
        "media_slug": "bent-over-backpack-row",
    },
    {
        "name_en": "One-Arm Backpack Row",
        "name_vi": "Chèo cặp sách một tay",
        "pattern": "h_pull",
        "muscle_slugs": ("back", "back-lats", "lats"),
        "media_slug": "one-arm-backpack-row",
    },
)


def ensure_nhapmon_public_plan(engine: Engine) -> None:
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        _ensure_household_exercises(db)
        if _plan_is_ready(db):
            return
        _delete_existing(db)
        from app.services.workout_generation.familiarization_curriculum import (
            generate_familiarization_workout,
        )

        generate_familiarization_workout(
            db,
            None,
            {
                "familiarization_path": "first_push_pull",
                "gender": "male",
                "experience_level": 1,
                "location": "home",
                "food_ids": [],
                "share_slug": NHAPMON_SHARE_TOKEN,
                "is_template": True,
            },
            persist=True,
        )
        if not _plan_is_ready(db):
            logger.warning("Nhập môn public plan seed finished but is incomplete")
    except Exception:
        db.rollback()
        logger.exception("Nhập môn public plan seed skipped")
    finally:
        db.close()


def _muscle_id(db: Session, slugs: tuple[str, ...]) -> int:
    for slug in slugs:
        row = db.query(MuscleGroup).filter(MuscleGroup.slug == slug).first()
        if row is not None:
            return int(row.id)
    fallback = db.query(MuscleGroup).order_by(MuscleGroup.id).first()
    if fallback is None:
        raise RuntimeError("No muscle groups to attach Nhập môn household exercises")
    return int(fallback.id)


def _library_media(slug: str) -> tuple[str | None, str | None]:
    media = Path(get_settings().upload_dir) / "media"
    video_rel = f"complete-exercise-library/{slug}.mp4"
    poster_rel = f"complete-exercise-library-posters/posters/{slug}.webp"
    video = video_rel if (media / video_rel).is_file() else None
    poster = poster_rel if (media / poster_rel).is_file() else None
    return video, poster


def _copy_by_name() -> dict[str, dict]:
    out: dict[str, dict] = {}
    for row in load_exercise_copy_seed():
        key = str(row.get("name_en") or "").strip().lower()
        if key:
            out[key] = row
    return out


def _ensure_household_exercises(db: Session) -> None:
    now = datetime.now(UTC).replace(tzinfo=None)
    copy_map = _copy_by_name()
    for item in _HOUSEHOLD_ROWS:
        row = (
            db.query(Exercise)
            .filter(Exercise.name_en == item["name_en"])
            .first()
        )
        mg = _muscle_id(db, item["muscle_slugs"])
        video, poster = _library_media(item["media_slug"])
        copy = copy_map.get(item["name_en"].lower(), {})
        steps = copy.get("instruction_steps_vi")
        steps = [str(x).strip() for x in steps if str(x).strip()] if isinstance(steps, list) else []
        instruction = str(copy.get("instruction_vi") or "").strip() or None
        tips = str(copy.get("tips_vi") or "").strip() or None
        mistakes = mistakes_text(copy.get("common_mistakes_vi"))
        if row is None:
            row = Exercise(
                name_en=item["name_en"],
                name_vi=item["name_vi"],
                muscle_group_id=mg,
                exercise_type="main",
                movement_role="compound",
                movement_pattern=item["pattern"],
                venue="both",
                difficulty=1,
                difficulty_label="1",
                notes_vi=NHAPMON_MARKER + item["name_en"],
                secondary_muscles=[],
                instruction_vi=instruction,
                instruction_steps_vi=steps or None,
                common_mistakes_vi=mistakes,
                tips_vi=tips,
                gif_url=poster,
                image_url=poster,
                video_url=video,
                is_active=True,
                created_at=now,
                updated_at=now,
            )
            db.add(row)
        else:
            row.name_vi = item["name_vi"]
            row.muscle_group_id = mg
            row.movement_pattern = item["pattern"]
            row.venue = "both"
            row.is_active = True
            row.owner_user_id = None
            row.notes_vi = NHAPMON_MARKER + item["name_en"]
            if instruction:
                row.instruction_vi = instruction
            if steps:
                row.instruction_steps_vi = steps
            if tips:
                row.tips_vi = tips
            if mistakes:
                row.common_mistakes_vi = mistakes
            if video:
                row.video_url = video
            if poster:
                row.gif_url = poster
                row.image_url = poster
            row.updated_at = now
    db.commit()


def _delete_existing(db: Session) -> None:
    plan = (
        db.query(UserDailyPlan)
        .filter(UserDailyPlan.share_token == NHAPMON_SHARE_TOKEN)
        .first()
    )
    if plan is None:
        return
    db.delete(plan)
    db.commit()


def _plan_is_ready(db: Session) -> bool:
    plan = (
        db.query(UserDailyPlan)
        .filter(UserDailyPlan.share_token == NHAPMON_SHARE_TOKEN)
        .first()
    )
    if plan is None:
        return False
    day_ids = [
        int(row[0])
        for row in db.query(UserDailyPlanDay.id)
        .filter(UserDailyPlanDay.plan_id == plan.id)
        .all()
    ]
    if len(day_ids) < NHAPMON_EXPECTED_DAYS:
        return False
    titled = (
        db.query(UserDailyPlanDay)
        .filter(UserDailyPlanDay.plan_id == plan.id)
        .order_by(UserDailyPlanDay.day_number)
        .all()
    )
    if not titled:
        return False
    first_title = str(titled[0].title_vi or "")
    second_title = str(titled[1].title_vi or "") if len(titled) > 1 else ""
    if not first_title.startswith("Buổi 1"):
        return False
    if "Buổi 2- Nghỉ phục hồi" not in second_title:
        return False
    band_names = (
        db.query(Exercise.name_en, Exercise.name_vi)
        .join(
            UserDailyPlanExercise,
            UserDailyPlanExercise.exercise_id == Exercise.id,
        )
        .filter(UserDailyPlanExercise.plan_day_id.in_(day_ids))
        .all()
        if day_ids
        else []
    )
    for name_en, name_vi in band_names:
        blob = f"{name_en or ''} {name_vi or ''}".lower()
        if any(
            token in blob
            for token in ("band", "với dây", "voi day", "kháng lực", "khang luc")
        ):
            return False
    trained = (
        db.query(UserDailyPlanExercise.id)
        .filter(UserDailyPlanExercise.plan_day_id.in_(day_ids))
        .count()
        if day_ids
        else 0
    )
    return trained >= NHAPMON_MIN_TRAIN_DAYS
