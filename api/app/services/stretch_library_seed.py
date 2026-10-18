"""Restore cooldown stretches from complete-library clips that metadata.json skipped."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.entities import Equipment, Exercise, ExerciseEquipment, MuscleGroup
from app.services.exercise_copy_seed import load_exercise_copy_seed, mistakes_text
from app.services.exercise_name_vi import preferred_name_vi
from app.services.exercise_video_policy import RETIRED_CATALOG_NAME_EN

MARKER_PREFIX = "seed:stretch-video:"
VIDEO_DIR = "complete-exercise-library"
POSTER_DIR = "complete-exercise-library-posters"

# Clips present on disk but absent from complete-exercise-library metadata.json.
STRETCH_CLIPS: tuple[dict[str, Any], ...] = (
    {
        "slug": "cat-cow-stretch",
        "name_en": "Cat-Cow Stretch",
        "secondary_muscles": ["back-lower"],
        "equipment": (),
    },
    {
        "slug": "childs-pose",
        "name_en": "Child's Pose",
        "secondary_muscles": ["back-lower"],
        "equipment": (),
    },
    {
        "slug": "cross-body-shoulder-stretch",
        "name_en": "Cross-Body Shoulder Stretch",
        "secondary_muscles": ["shoulders-lateral"],
        "equipment": (),
    },
    {
        "slug": "doorway-chest-stretch",
        "name_en": "Doorway Chest Stretch",
        "secondary_muscles": ["chest-mid"],
        "equipment": (),
    },
    {
        "slug": "floor-chest-stretch",
        "name_en": "Floor Chest Stretch",
        "secondary_muscles": ["chest-mid"],
        "equipment": (),
    },
    {
        "slug": "overhead-shoulder-triceps-stretch",
        "name_en": "Overhead Shoulder/Triceps Stretch",
        "secondary_muscles": ["triceps"],
        "equipment": (),
    },
    {
        "slug": "ring-lat-stretch",
        "name_en": "Ring Lat Stretch",
        "secondary_muscles": ["back-lats"],
        "equipment": ("gymnastic-rings",),
        "venue": "home",
    },
    {
        "slug": "ring-pec-stretch",
        "name_en": "Ring Pec Stretch",
        "secondary_muscles": ["chest-mid"],
        "equipment": ("gymnastic-rings",),
        "venue": "home",
    },
    {
        "slug": "seated-spinal-twist",
        "name_en": "Seated Spinal Twist",
        "secondary_muscles": ["core-obliques"],
        "equipment": (),
    },
    {
        "slug": "standing-calf-stretch",
        "name_en": "Standing Calf Stretch",
        "secondary_muscles": ["calves"],
        "equipment": (),
    },
    {
        "slug": "standing-chest-opener",
        "name_en": "Standing Chest Opener",
        "secondary_muscles": ["chest-mid"],
        "equipment": (),
    },
    {
        "slug": "standing-quad-stretch",
        "name_en": "Standing Quad Stretch",
        "secondary_muscles": ["quads"],
        "equipment": (),
    },
    {
        "slug": "standing-seated-hamstring-stretch",
        "name_en": "Standing/Seated Hamstring Stretch",
        "secondary_muscles": ["hamstrings"],
        "equipment": (),
    },
    {
        "slug": "wrist-flexor-extensor-stretch",
        "name_en": "Wrist Flexor/Extensor Stretch",
        "secondary_muscles": ["forearms"],
        "equipment": (),
    },
)

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slugify(value: str) -> str:
    return _SLUG_RE.sub("-", value.strip().lower()).strip("-")


def _media_root(override: Path | None = None) -> Path:
    if override is not None:
        return override
    return Path(get_settings().upload_dir) / "media"


def _copy_by_name() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in load_exercise_copy_seed():
        key = str(row.get("name_en") or "").strip().lower()
        if key:
            out[key] = row
    return out


def _copy_by_slug(copies: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {_slugify(name): row for name, row in copies.items()}


def _assigned_video_stems(db: Session) -> set[str]:
    stems: set[str] = set()
    for (url,) in db.query(Exercise.video_url).filter(Exercise.video_url.isnot(None)).all():
        raw = str(url or "").replace("\\", "/").strip()
        if not raw:
            continue
        stem = Path(raw.split("?")[0]).stem.lower()
        if stem:
            stems.add(stem)
    return stems


def is_stretch_named(name_en: str) -> bool:
    n = (name_en or "").strip().lower()
    if "stretch" in n:
        return True
    return any(
        token in n
        for token in (
            "child's pose",
            "chest opener",
            "cat-cow",
            "spinal twist",
            "jefferson curl",
        )
    )


def _looks_like_stretch(stem: str) -> bool:
    n = stem.lower()
    if "stretch" in n:
        return True
    return any(
        token in n
        for token in (
            "childs-pose",
            "child-s-pose",
            "chest-opener",
            "cat-cow",
            "spinal-twist",
            "jefferson-curl",
        )
    )


def extra_unassigned_stretch_clips(db: Session, media: Path) -> list[dict[str, Any]]:
    """Any leftover stretch-like mp4 not already in STRETCH_CLIPS or assigned."""
    video_dir = media / VIDEO_DIR
    if not video_dir.is_dir():
        return []
    known = {str(item["slug"]) for item in STRETCH_CLIPS}
    assigned = _assigned_video_stems(db)
    copies = _copy_by_slug(_copy_by_name())
    extras: list[dict[str, Any]] = []
    for path in sorted(video_dir.glob("*.mp4")):
        slug = path.stem.strip().lower()
        if slug in known or slug in assigned:
            continue
        if not _looks_like_stretch(slug):
            continue
        copy = copies.get(slug) or {}
        name_en = str(copy.get("name_en") or "").strip() or slug.replace("-", " ").title()
        extras.append(
            {
                "slug": slug,
                "name_en": name_en,
                "secondary_muscles": [],
                "equipment": (),
            }
        )
    return extras


def _link_equipment(db: Session, exercise_id: int, slugs: tuple[str, ...]) -> None:
    for slug in slugs:
        eq = db.query(Equipment).filter(Equipment.slug == slug).first()
        if eq is None:
            continue
        exists = (
            db.query(ExerciseEquipment)
            .filter(
                ExerciseEquipment.exercise_id == exercise_id,
                ExerciseEquipment.equipment_id == eq.id,
            )
            .first()
        )
        if not exists:
            db.add(ExerciseEquipment(exercise_id=exercise_id, equipment_id=eq.id))


def seed_stretch_library_from_videos(db: Session, *, media_root: Path | None = None) -> int:
    media = _media_root(media_root)
    video_dir = media / VIDEO_DIR
    if not video_dir.is_dir():
        return 0
    muscles = {m.slug: m.id for m in db.query(MuscleGroup).all()}
    stretch_id = muscles.get("stretch") or muscles.get("gian-co")
    if stretch_id is None:
        return 0
    copies = _copy_by_name()
    now = datetime.now(UTC).replace(tzinfo=None)
    n = 0
    items = list(STRETCH_CLIPS) + extra_unassigned_stretch_clips(db, media)
    for item in items:
        slug = str(item["slug"]).strip()
        name_en = str(item["name_en"]).strip()
        video_rel = f"{VIDEO_DIR}/{slug}.mp4"
        if not (media / video_rel).is_file():
            continue
        poster_rel = None
        for candidate in (
            f"{POSTER_DIR}/posters/{slug}.webp",
            f"{POSTER_DIR}/{slug}.webp",
            f"{POSTER_DIR}/posters/{slug}.jpg",
        ):
            if (media / candidate).is_file():
                poster_rel = candidate
                break
        copy = copies.get(name_en.lower()) or {}
        name_vi = preferred_name_vi(
            name_en=name_en,
            name_vi=None,
            copy_vi=str(copy.get("name_vi") or "").strip() or None,
        )
        raw_steps = copy.get("instruction_steps_vi")
        steps = [str(x).strip() for x in raw_steps if str(x).strip()] if isinstance(raw_steps, list) else []
        instruction = str(copy.get("instruction_vi") or "").strip() or None
        mistakes = mistakes_text(copy.get("common_mistakes_vi"))
        tips = str(copy.get("tips_vi") or "").strip() or None
        marker = f"{MARKER_PREFIX}{slug}"
        row = (
            db.query(Exercise).filter(Exercise.notes_vi == marker).first()
            or db.query(Exercise).filter(Exercise.name_en == name_en).first()
        )
        secondaries = [str(x) for x in (item.get("secondary_muscles") or []) if str(x).strip()]
        venue = str(item.get("venue") or "") or None
        if row is None:
            row = Exercise(
                name_vi=name_vi,
                name_en=name_en,
                muscle_group_id=stretch_id,
                exercise_type="cooldown",
                movement_role="mobility",
                movement_pattern="mobility",
                venue=venue,
                difficulty=2,
                notes_vi=marker,
                secondary_muscles=secondaries,
                instruction_vi=instruction,
                instruction_steps_vi=steps or None,
                common_mistakes_vi=mistakes,
                tips_vi=tips,
                gif_url=poster_rel,
                image_url=poster_rel,
                video_url=video_rel,
                is_active=name_en not in RETIRED_CATALOG_NAME_EN,
                created_at=now,
                updated_at=now,
            )
            db.add(row)
            db.flush()
        else:
            row.name_vi = name_vi
            row.name_en = name_en
            row.muscle_group_id = stretch_id
            row.exercise_type = "cooldown"
            row.movement_role = "mobility"
            row.movement_pattern = "mobility"
            if venue:
                row.venue = venue
            row.notes_vi = marker
            row.secondary_muscles = secondaries
            row.instruction_vi = instruction or row.instruction_vi
            row.instruction_steps_vi = steps or row.instruction_steps_vi
            row.common_mistakes_vi = mistakes or row.common_mistakes_vi
            row.tips_vi = tips or row.tips_vi
            row.video_url = video_rel
            row.is_active = name_en not in RETIRED_CATALOG_NAME_EN
            if poster_rel:
                row.gif_url = poster_rel
                row.image_url = poster_rel
            row.updated_at = now
        _link_equipment(db, row.id, tuple(item.get("equipment") or ()))
        n += 1
    for row in db.query(Exercise).filter(Exercise.is_active.is_(True)).all():
        if not is_stretch_named(str(row.name_en or "")):
            continue
        row.exercise_type = "cooldown"
        row.movement_role = "mobility"
        if stretch_id is not None:
            row.muscle_group_id = stretch_id
    return n
