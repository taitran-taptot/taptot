"""Import the local complete-exercise-library metadata into exercises."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.entities import Equipment, Exercise, ExerciseEquipment, MuscleGroup
from app.services.exercise_copy_seed import load_exercise_copy_seed, mistakes_text
from app.services.exercise_muscle_region import classify_region_slug
from app.services.exercise_video_policy import RETIRED_CATALOG_NAME_EN
from app.services.exercise_name_vi import preferred_name_vi

MUSCLE_TO_SLUG = {
    "glutes": "glutes",
    "quadriceps": "quads",
    "back": "back-lats",
    "shoulders": "shoulders-lateral",
    "core": "core-upper",
    "chest": "chest-mid",
    "hamstrings": "hamstrings",
    "trapezius": "shoulders-traps",
    "biceps": "biceps",
    "triceps": "triceps",
    "calves": "calves",
    "forearms": "forearms",
    "lower back": "back-lower",
    "adductors": "quads",
    "neck": "shoulders-traps",
    "tibialis": "calves",
}

EQUIPMENT_TO_SLUG = {
    "dumbbell": "dumbbell",
    "bodyweight": None,
    "barbell": "barbell",
    "machine": "machine",
    "cable machine": "cable",
    "kettlebell": "kettlebell",
    "band": "resistance-band-1",
    "weight plate": "plate",
    "stability ball": "swiss-ball-stability-ball",
    "sled": "sled",
    "bicycle": "bicycle",
    "battle ropes": "battle-ropes",
    "bench": "bench",
    "wrist roller": None,
}

EQUIPMENT_CREATE = {
    "barbell": ("Tạ đòn", "Barbell"),
    "machine": ("Máy tập", "Machine"),
    "cable": ("Cáp", "Cable"),
    "kettlebell": ("Tạ ấm", "Kettlebell"),
    "plate": ("Đĩa tạ", "Weight plate"),
    "sled": ("Xe trượt", "Sled"),
    "bicycle": ("Xe đạp", "Bicycle"),
    "battle-ropes": ("Dây battle rope", "Battle ropes"),
    "bench": ("Ghế tập", "Bench"),
}

PATTERN_MAP = {
    "isolation": "isolation",
    "pull": "pull",
    "push": "push",
    "hinge": "hinge",
    "cardio": "cardio",
    "squat": "squat",
    "lunge": "lunge",
    "core": "core",
    "mobility": "mobility",
    "plyometric": "plyometric",
    "rotation": "rotation",
    "stretch": "mobility",
    "hip abduction": "hinge",
    "carry": "carry",
}

DIFFICULTY = {"beginner": 2, "intermediate": 3, "advanced": 4}


def _meta_path() -> Path:
    return Path(get_settings().upload_dir) / "media" / "complete-exercise-library-metadata" / "metadata.json"


def _media_root() -> Path:
    return Path(get_settings().upload_dir) / "media"


def _copy_by_name() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in load_exercise_copy_seed():
        key = str(row.get("name_en") or "").strip().lower()
        if key:
            out[key] = row
    return out


def _ensure_equipment(db: Session, slug: str, name_en: str) -> Equipment:
    row = db.query(Equipment).filter(Equipment.slug == slug).first()
    if row:
        return row
    vi, en = EQUIPMENT_CREATE.get(slug, (name_en, name_en))
    row = Equipment(slug=slug, name_vi=vi, name_en=en, is_active=True, sort_order=80)
    db.add(row)
    db.flush()
    return row


def _muscle_id(
    db: Session,
    primary: list[str],
    fallback: dict[str, int],
    *,
    pattern: str | None,
    name_en: str,
    name_vi: str | None = None,
) -> int:
    n = name_en.lower()
    if pattern == "cardio" or "cardio" in {str(x).strip().lower() for x in primary}:
        if "cardio" in fallback:
            return fallback["cardio"]
    if pattern == "mobility" or "stretch" in n:
        if "stretch" in fallback:
            return fallback["stretch"]
    old_slug = ""
    for raw in primary:
        slug = MUSCLE_TO_SLUG.get(str(raw).strip().lower())
        if slug:
            old_slug = slug
            break
    classified = classify_region_slug(
        name_vi=name_vi,
        name_en=name_en,
        old_slug=old_slug,
        movement_pattern=pattern,
    )
    if classified.new_slug in fallback:
        return fallback[classified.new_slug]
    if old_slug and old_slug in fallback:
        return fallback[old_slug]
    return fallback.get("core-upper") or next(iter(fallback.values()))


def seed_complete_exercise_library(db: Session) -> int:
    path = _meta_path()
    if not path.is_file():
        return 0
    items = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(items, list):
        return 0
    copies = _copy_by_name()
    media = _media_root()
    muscles = {m.slug: m.id for m in db.query(MuscleGroup).all()}
    if not muscles:
        return 0
    now = datetime.now(UTC).replace(tzinfo=None)
    n = 0
    for item in items:
        slug = str(item.get("slug") or "").strip()
        name_en = str(item.get("name") or "").strip()
        if not slug or not name_en:
            continue
        copy = copies.get(name_en.lower()) or copies.get(name_en.lower().replace("bodyweight ", "")) or {}
        name_vi = preferred_name_vi(
            name_en=name_en,
            name_vi=None,
            copy_vi=str(copy.get("name_vi") or "").strip() or None,
        )
        video_file = str(item.get("videoFile") or "").strip()
        poster_file = str(item.get("posterFile") or "").strip()
        video_rel = f"complete-exercise-library/{video_file}" if video_file else None
        poster_rel = f"complete-exercise-library-posters/{poster_file}" if poster_file else None
        if video_rel and not (media / video_rel).is_file():
            video_rel = None
        if poster_rel and not (media / poster_rel).is_file():
            poster_rel = None
        raw_steps = copy.get("instruction_steps_vi")
        steps = [str(x).strip() for x in raw_steps if str(x).strip()] if isinstance(raw_steps, list) else []
        instruction = str(copy.get("instruction_vi") or "").strip() or None
        mistakes = mistakes_text(copy.get("common_mistakes_vi")) or mistakes_text(
            item.get("commonMistakes")
        )
        tips = str(copy.get("tips_vi") or "").strip() or None
        patterns = item.get("movementPattern") or []
        pattern = PATTERN_MAP.get(str(patterns[0]).strip().lower()) if patterns else None
        diff = DIFFICULTY.get(str(item.get("difficulty") or "").lower(), 2)
        marker = f"seed:cel:{slug}"
        row = (
            db.query(Exercise).filter(Exercise.notes_vi == marker).first()
            or db.query(Exercise).filter(Exercise.name_en == name_en).first()
        )
        mg_id = _muscle_id(
            db,
            list(item.get("primaryMuscles") or []),
            muscles,
            pattern=pattern,
            name_en=name_en,
            name_vi=name_vi,
        )
        secondaries = [str(x) for x in (item.get("secondaryMuscles") or []) if str(x).strip()]
        is_stretch = "stretch" in name_en.lower() or any(
            token in name_en.lower()
            for token in (
                "child's pose",
                "chest opener",
                "cat-cow",
                "spinal twist",
                "jefferson curl",
            )
        )
        if pattern == "cardio":
            exercise_type = "cardio"
            movement_role = None
        elif is_stretch:
            exercise_type = "cooldown"
            movement_role = "mobility"
        else:
            exercise_type = "main"
            movement_role = None
        if row is None:
            row = Exercise(
                name_vi=name_vi,
                name_en=name_en,
                muscle_group_id=mg_id,
                exercise_type=exercise_type,
                movement_role=movement_role,
                movement_pattern=pattern,
                difficulty=diff,
                notes_vi=marker,
                secondary_muscles=secondaries,
                instruction_vi=instruction,
                instruction_steps_vi=steps or None,
                common_mistakes_vi=mistakes,
                tips_vi=tips,
                gif_url=poster_rel,
                image_url=poster_rel,
                video_url=video_rel,
                is_active=bool(video_rel) and name_en not in RETIRED_CATALOG_NAME_EN,
                created_at=now,
                updated_at=now,
            )
            db.add(row)
            db.flush()
        else:
            row.name_vi = name_vi
            row.name_en = name_en
            row.muscle_group_id = mg_id
            row.exercise_type = exercise_type
            if movement_role:
                row.movement_role = movement_role
            row.movement_pattern = pattern or row.movement_pattern
            row.difficulty = diff
            row.notes_vi = marker
            row.secondary_muscles = secondaries
            row.instruction_vi = instruction or row.instruction_vi
            row.instruction_steps_vi = steps or row.instruction_steps_vi
            row.common_mistakes_vi = mistakes or row.common_mistakes_vi
            row.tips_vi = tips or row.tips_vi
            if poster_rel:
                row.gif_url = poster_rel
                row.image_url = poster_rel
            if video_rel:
                row.video_url = video_rel
                row.is_active = name_en not in RETIRED_CATALOG_NAME_EN
            row.updated_at = now
        eq_names = item.get("equipment") or []
        for raw in eq_names:
            eq_slug = EQUIPMENT_TO_SLUG.get(str(raw).strip().lower())
            if not eq_slug:
                continue
            eq = _ensure_equipment(db, eq_slug, str(raw))
            exists = (
                db.query(ExerciseEquipment)
                .filter(
                    ExerciseEquipment.exercise_id == row.id,
                    ExerciseEquipment.equipment_id == eq.id,
                )
                .first()
            )
            if not exists:
                db.add(ExerciseEquipment(exercise_id=row.id, equipment_id=eq.id))
        n += 1
    return n
