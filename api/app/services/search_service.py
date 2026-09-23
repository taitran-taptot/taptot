from sqlalchemy import and_, case, func, or_
from sqlalchemy.orm import Session
import json

from app.core.pagination import PaginationParams
from app.models.entities import Equipment, Exercise, ExerciseEquipment, Food, FoodAlias, MuscleGroup
from app.services.equipment_media import local_image_relpath
from app.services.workout_generation.shortlist import (
    apply_catalog_location_sql,
    exercise_passes_location_gear,
    location_from_venue,
    normalize_location_gear,
    venue_sql_filter,
    _equipment_slugs_by_exercise,
)


# Public "Dây kháng lực" matches loop, tube, mini-band, and the legacy generic slug.
_BAND_SEARCH_SLUGS = (
    "resistance-band",
    "resistance-band-1",
    "resistance-band-2",
    "day-mini-band",
)
_BAND_SEARCH_SET = frozenset(_BAND_SEARCH_SLUGS)


def expand_search_equipment_keys(raw: list[str] | None) -> tuple[list[str], bool]:
    """Expand wizard/public band keys to the full catalog family."""
    expanded: list[str] = []
    seen: set[str] = set()
    has_band = False
    for item in raw or ():
        key = str(item or "").strip()
        if not key:
            continue
        if key in _BAND_SEARCH_SET:
            has_band = True
            continue
        if key in seen:
            continue
        seen.add(key)
        expanded.append(key)
    if has_band:
        for slug in _BAND_SEARCH_SLUGS:
            if slug in seen:
                continue
            seen.add(slug)
            expanded.append(slug)
    return expanded, has_band


def _band_name_match():
    """Name fallback so untagged Band / Pallof / dây kháng lực rows still appear."""
    return or_(
        Exercise.name_en.ilike("band %"),
        Exercise.name_en.ilike("% band %"),
        Exercise.name_en.ilike("% band"),
        Exercise.name_en.ilike("pallof %"),
        Exercise.name_en.ilike("%pallof press%"),
        Exercise.name_vi.ilike("%dây kháng%"),
        Exercise.name_vi.ilike("%day khang%"),
        Exercise.name_vi.ilike("%với dây%"),
        Exercise.name_en.ilike("%mini band%"),
        Exercise.name_en.ilike("%loop band%"),
    )


_CALISTHENIC_SLUGS = ("gymnastic-rings", "pull-up-bar", "parallel-bars")
_BAND_SPEC_SLUGS = (
    "resistance-band",
    "resistance-band-1",
    "resistance-band-2",
    "day-mini-band",
)
_GYM_MACHINE_CATEGORIES = ("Máy tập", "Thiết bị Cardio")
_OTHER_NAME_KEYS = ("yoga", "pilates", "dance")
_SPORT_NAME_KEYS = (
    "swim",
    "hiking",
    "hike",
    "trail run",
    "bơi",
    "đi bộ đường dài",
)
_MARTIAL_NAME_KEYS = (
    "boxing",
    "shadow boxing",
    "võ thuật",
    "đấm",
    "muay",
    "kickboxing",
    "karate",
    "judo",
    "taekwondo",
    "bjj",
    "mma",
)


def _name_key_match(keys: tuple[str, ...]):
    parts = []
    for key in keys:
        like = f"%{key}%"
        parts.append(Exercise.name_en.ilike(like))
        parts.append(Exercise.name_vi.ilike(like))
    return or_(*parts)


def _linked_exercise_ids(db: Session, *, slugs: tuple[str, ...] | None = None, categories: tuple[str, ...] | None = None):
    q = db.query(ExerciseEquipment.exercise_id).join(
        Equipment, Equipment.id == ExerciseEquipment.equipment_id
    )
    conds = []
    if slugs:
        conds.append(Equipment.slug.in_(slugs))
    if categories:
        conds.append(Equipment.category.in_(categories))
    if conds:
        q = q.filter(or_(*conds) if len(conds) > 1 else conds[0])
    return q


def specialization_filter(db: Session, spec: str | None):
    """Return a SQLAlchemy clause for public kho-bài-tập specialization tabs."""
    key = (spec or "").strip().lower()
    if key not in {"gym", "calisthenic", "other", "sport", "martial"}:
        return None
    all_linked = db.query(ExerciseEquipment.exercise_id)
    if key == "gym":
        return venue_sql_filter("gym")
    if key == "calisthenic":
        cal_ids = _linked_exercise_ids(db, slugs=_CALISTHENIC_SLUGS)
        gym_machine_ids = _linked_exercise_ids(db, categories=_GYM_MACHINE_CATEGORIES)
        unlinked_strength = and_(
            ~Exercise.id.in_(all_linked),
            func.lower(func.coalesce(Exercise.exercise_type, "main")) != "cardio",
            func.lower(func.coalesce(Exercise.venue, "both")) != "gym",
        )
        linked_bodyweight = and_(
            Exercise.id.in_(cal_ids),
            ~Exercise.id.in_(gym_machine_ids),
        )
        return or_(unlinked_strength, linked_bodyweight)
    if key == "other":
        band_ids = _linked_exercise_ids(db, slugs=_BAND_SPEC_SLUGS)
        return or_(Exercise.id.in_(band_ids), _band_name_match(), _name_key_match(_OTHER_NAME_KEYS))
    if key == "sport":
        gym_ids = _linked_exercise_ids(db, categories=_GYM_MACHINE_CATEGORIES)
        cardio = func.lower(func.coalesce(Exercise.exercise_type, "")) == "cardio"
        return or_(
            _name_key_match(_SPORT_NAME_KEYS),
            and_(cardio, ~_name_key_match(_MARTIAL_NAME_KEYS), ~Exercise.id.in_(gym_ids)),
        )
    return _name_key_match(_MARTIAL_NAME_KEYS)


# Skill difficulty labels (1–4); experience bands filter separately in the UI.
DIFFICULTY_VI = {
    1: "Rất cơ bản",
    2: "Cơ bản",
    3: "Trung cấp",
    4: "Nâng cao",
}

EXERCISE_TYPE_VI = {
    "warmup": "Khởi động",
    "main": "Bài chính",
    "cooldown": "Giãn cơ",
    "cardio": "Cardio",
}


def expand_muscle_group_ids(db: Session, ids: list[int] | None) -> list[int] | None:
    """Expand parent muscle_group ids to include all direct children."""
    if not ids:
        return ids
    base = {int(i) for i in ids}
    children = (
        db.query(MuscleGroup.id)
        .filter(MuscleGroup.parent_id.in_(list(base)))
        .all()
    )
    for (cid,) in children:
        base.add(int(cid))
    return list(base)


def _as_steps(value) -> list[str] | None:
    if value is None:
        return None
    if isinstance(value, list):
        steps = [str(s).strip() for s in value if str(s).strip()]
        return steps or None
    text = str(value).strip()
    return [text] if text else None


def _as_str_list(value) -> list[str]:
    """Normalize JSON/list/string secondary_muscles to list[str]."""
    if value is None:
        return []
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return []
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            return [raw] if raw and raw != "[]" else []
    if isinstance(value, list):
        return [str(s).strip() for s in value if str(s).strip()]
    return []


class SearchService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _serialize_exercise(self, ex: Exercise, mg: MuscleGroup, *, detail: bool = False) -> dict:
        eq_names = self._equipment_names(ex.id)
        muscle_label = mg.name_vi
        if mg.name_en:
            muscle_label = f"{mg.name_vi} - {mg.name_en}"
        item = {
            "id": ex.id,
            "name_en": ex.name_en or "",
            "name_vi": ex.name_vi,
            "body_part": mg.slug,
            "muscle_group": muscle_label,
            "muscle_group_id": mg.id,
            "equipment": ", ".join(eq_names) if eq_names else "—",
            "equipment_slugs": self._equipment_slugs(ex.id),
            "exercise_type": ex.exercise_type,
            "exercise_type_label": EXERCISE_TYPE_VI.get(ex.exercise_type, ex.exercise_type),
            "movement_role": getattr(ex, "movement_role", None),
            "movement_pattern": getattr(ex, "movement_pattern", None),
            "venue": getattr(ex, "venue", None) or "both",
            "difficulty": ex.difficulty,
            "difficulty_label": DIFFICULTY_VI.get(ex.difficulty, ex.difficulty_label or ""),
            "notes_vi": ex.notes_vi,
            "is_beginner_friendly": ex.difficulty <= 2,
            "gif_url": ex.gif_url,
            "image_url": getattr(ex, "image_url", None),
            "video_url": getattr(ex, "video_url", None),
        }
        if not detail:
            return item

        steps = _as_steps(getattr(ex, "instruction_steps_vi", None))
        instruction = getattr(ex, "instruction_vi", None)
        if not steps and instruction:
            steps = [instruction]
        item.update(
            {
                "target_muscle": muscle_label,
                "secondary_muscles": _as_str_list(getattr(ex, "secondary_muscles", None)),
                "image_url": getattr(ex, "image_url", None),
                "video_url": getattr(ex, "video_url", None),
                "instruction_vi": instruction,
                "instruction_steps_vi": steps,
                "instruction_en": None,
                "instruction_steps_en": None,
                "common_mistakes_vi": getattr(ex, "common_mistakes_vi", None),
                "tips_vi": getattr(ex, "tips_vi", None),
            }
        )
        return item

    def search_exercises(
        self,
        pagination: PaginationParams,
        q: str | None = None,
        body_part: str | None = None,
        equipment: str | None = None,
        difficulty: str | None = None,
        beginner_only: bool = False,
        exercise_type: str | None = None,
        muscle_group_id: int | None = None,
        muscle_group_ids: list[int] | None = None,
        difficulties: list[int] | None = None,
        equipment_categories: list[str] | None = None,
        movement_roles: list[str] | None = None,
        movement_patterns: list[str] | None = None,
        location: str | None = None,
        specialization: str | None = None,
    ) -> tuple[list[dict], int]:
        query = (
            self.db.query(Exercise, MuscleGroup)
            .join(MuscleGroup, MuscleGroup.id == Exercise.muscle_group_id)
            .filter(Exercise.is_active.is_(True))
        )

        if q:
            pattern = f"%{q}%"
            query = query.filter(
                or_(
                    Exercise.name_vi.ilike(pattern),
                    Exercise.name_en.ilike(pattern),
                    MuscleGroup.name_vi.ilike(pattern),
                    Exercise.notes_vi.ilike(pattern),
                )
            )

        if muscle_group_ids:
            expanded = expand_muscle_group_ids(self.db, muscle_group_ids)
            query = query.filter(Exercise.muscle_group_id.in_(expanded or muscle_group_ids))
        elif muscle_group_id:
            expanded = expand_muscle_group_ids(self.db, [int(muscle_group_id)])
            query = query.filter(Exercise.muscle_group_id.in_(expanded or [muscle_group_id]))
        elif body_part:
            # accept slug or Vietnamese label
            query = query.filter(
                or_(
                    MuscleGroup.slug == body_part,
                    MuscleGroup.name_vi == body_part,
                )
            )

        if equipment:
            keys, has_band = expand_search_equipment_keys(
                [e.strip() for e in equipment.split(",") if e.strip()]
            )
            if keys:
                # keys may be slug or numeric id
                eq_q = self.db.query(ExerciseEquipment.exercise_id).join(
                    Equipment, Equipment.id == ExerciseEquipment.equipment_id
                )
                id_keys = [int(k) for k in keys if k.isdigit()]
                slug_keys = [k for k in keys if not k.isdigit()]
                conds = []
                if id_keys:
                    conds.append(Equipment.id.in_(id_keys))
                if slug_keys:
                    conds.append(Equipment.slug.in_(slug_keys))
                    conds.append(Equipment.name_vi.in_(slug_keys))
                match_conds = []
                if conds:
                    eq_q = eq_q.filter(or_(*conds))
                    match_conds.append(Exercise.id.in_(eq_q))
                if has_band:
                    match_conds.append(_band_name_match())
                if match_conds:
                    query = query.filter(or_(*match_conds) if len(match_conds) > 1 else match_conds[0])

        if equipment_categories:
            no_equipment = "Không dụng cụ" in equipment_categories
            real_categories = [c for c in equipment_categories if c != "Không dụng cụ"]
            all_linked = self.db.query(ExerciseEquipment.exercise_id)
            category_conditions = []
            if real_categories:
                cat_q = (
                    self.db.query(ExerciseEquipment.exercise_id)
                    .join(Equipment, Equipment.id == ExerciseEquipment.equipment_id)
                    .filter(Equipment.category.in_(real_categories))
                )
                category_conditions.append(Exercise.id.in_(cat_q))
            if no_equipment:
                category_conditions.append(~Exercise.id.in_(all_linked))
            if category_conditions:
                query = query.filter(or_(*category_conditions))

        if difficulties:
            query = query.filter(Exercise.difficulty.in_(difficulties))
        elif difficulty:
            if difficulty.isdigit():
                query = query.filter(Exercise.difficulty == int(difficulty))
            else:
                # map legacy labels
                legacy = {
                    "beginner": (1, 2),
                    "intermediate": (3,),
                    "advanced": (4, 5),
                    "expert": (5,),
                }
                vals = legacy.get(difficulty)
                if vals:
                    query = query.filter(Exercise.difficulty.in_(vals))

        if beginner_only:
            query = query.filter(Exercise.difficulty <= 2)

        if exercise_type:
            query = query.filter(Exercise.exercise_type == exercise_type)

        if movement_roles:
            query = query.filter(Exercise.movement_role.in_(movement_roles))
        if movement_patterns:
            query = query.filter(Exercise.movement_pattern.in_(movement_patterns))

        loc = (location or "").strip().lower()
        if loc in {"gym", "home"}:
            query = query.filter(venue_sql_filter(loc))

        spec_clause = specialization_filter(self.db, specialization)
        if spec_clause is not None:
            query = query.filter(spec_clause)

        total = query.count()
        venue_norm = func.lower(func.coalesce(Exercise.venue, "both"))
        prefer_gym = not equipment and not equipment_categories
        gym_rank = case(
            (venue_norm == "gym", 0),
            (venue_norm == "both", 1),
            else_=2,
        )
        order = (
            (gym_rank.asc(), Exercise.difficulty.asc(), Exercise.name_vi.asc())
            if prefer_gym
            else (Exercise.difficulty.asc(), Exercise.name_vi.asc())
        )
        rows = query.order_by(*order).offset(pagination.offset).limit(pagination.page_size).all()

        items = [self._serialize_exercise(ex, mg, detail=False) for ex, mg in rows]
        return items, total

    def get_exercise_detail(self, exercise_id: str | int) -> dict | None:
        try:
            eid = int(exercise_id)
        except (TypeError, ValueError):
            return None
        row = (
            self.db.query(Exercise, MuscleGroup)
            .join(MuscleGroup, MuscleGroup.id == Exercise.muscle_group_id)
            .filter(Exercise.id == eid)
            .first()
        )
        if not row:
            return None
        ex, mg = row
        return self._serialize_exercise(ex, mg, detail=True)

    def exercise_alternatives(
        self,
        exercise_id: int,
        limit: int = 5,
        *,
        location: str | None = None,
        no_equipment: bool = False,
        equipment: list[str] | None = None,
    ) -> list[dict]:
        try:
            eid = int(exercise_id)
        except (TypeError, ValueError):
            return []
        row = (
            self.db.query(Exercise, MuscleGroup)
            .join(MuscleGroup, MuscleGroup.id == Exercise.muscle_group_id)
            .filter(Exercise.id == eid)
            .first()
        )
        if not row:
            return []
        ex, mg = row
        if not (location or "").strip():
            location = location_from_venue(ex.venue)
        loc, no_eq, raw = normalize_location_gear(
            location, no_equipment=no_equipment, equipment_slugs=equipment
        )
        diff = int(ex.difficulty or 3)
        fetch_n = max(20, limit * 8)

        def _base_q():
            q = (
                self.db.query(Exercise, MuscleGroup)
                .join(MuscleGroup, MuscleGroup.id == Exercise.muscle_group_id)
                .filter(
                    Exercise.is_active.is_(True),
                    Exercise.id != eid,
                    MuscleGroup.id == mg.id,
                )
            )
            q, _, _, _, _ = apply_catalog_location_sql(
                q,
                self.db,
                location=loc,
                no_equipment=no_eq,
                equipment_slugs=raw,
            )
            return q

        candidates = (
            _base_q()
            .filter(
                Exercise.difficulty >= max(1, diff - 1),
                Exercise.difficulty <= min(4, diff + 1),
            )
            .limit(fetch_n)
            .all()
        )
        if len(candidates) < fetch_n:
            more = _base_q().limit(fetch_n).all()
            seen = {c[0].id for c in candidates}
            for c in more:
                if c[0].id not in seen:
                    candidates.append(c)
                    seen.add(c[0].id)

        eq_map = _equipment_slugs_by_exercise(self.db, [int(e.id) for e, _g in candidates])
        out: list[dict] = []
        for e, g in candidates:
            if not exercise_passes_location_gear(
                venue=e.venue,
                equipment_slugs=eq_map.get(int(e.id), set()),
                name_vi=e.name_vi,
                name_en=getattr(e, "name_en", None),
                location=loc,
                no_equipment=no_eq,
                user_slugs=raw,
            ):
                continue
            out.append(self._serialize_exercise(e, g, detail=False))
            if len(out) >= limit:
                break
        return out

    def _equipment_names(self, exercise_id: int) -> list[str]:
        rows = (
            self.db.query(Equipment.name_vi)
            .join(ExerciseEquipment, ExerciseEquipment.equipment_id == Equipment.id)
            .filter(ExerciseEquipment.exercise_id == exercise_id)
            .order_by(Equipment.name_vi.asc())
            .all()
        )
        return [r[0] for r in rows]

    def _equipment_slugs(self, exercise_id: int) -> list[str]:
        rows = (
            self.db.query(Equipment.slug)
            .join(ExerciseEquipment, ExerciseEquipment.equipment_id == Equipment.id)
            .filter(ExerciseEquipment.exercise_id == exercise_id)
            .all()
        )
        return [r[0] for r in rows]

    def list_muscle_group_labels(self) -> list[dict]:
        rows = self.db.query(MuscleGroup).order_by(MuscleGroup.sort_order.asc()).all()
        slug_by_id = {int(r.id): r.slug for r in rows}
        out: list[dict] = []
        for r in rows:
            if getattr(r, "is_filter_only", False):
                continue
            parent_slug = slug_by_id.get(int(r.parent_id)) if r.parent_id else None
            out.append(
                {
                    "key": r.slug,
                    "label_vi": r.name_vi,
                    "id": r.id,
                    "name_en": r.name_en,
                    "parent_id": r.parent_id,
                    "parent_slug": parent_slug,
                    "is_filter_only": bool(getattr(r, "is_filter_only", False)),
                }
            )
        return out

    def list_muscle_group_tree(self) -> list[dict]:
        """Return filter tree: parents with children (single source of truth from DB)."""
        rows = self.db.query(MuscleGroup).order_by(MuscleGroup.sort_order.asc()).all()
        by_parent: dict[int | None, list[MuscleGroup]] = {}
        for r in rows:
            pid = int(r.parent_id) if r.parent_id else None
            by_parent.setdefault(pid, []).append(r)

        def node(mg: MuscleGroup) -> dict:
            kids = by_parent.get(int(mg.id), [])
            return {
                "key": mg.slug,
                "label_vi": mg.name_vi,
                "id": mg.id,
                "name_en": mg.name_en,
                "is_filter_only": bool(getattr(mg, "is_filter_only", False)),
                "children": [node(c) for c in kids if not getattr(c, "is_filter_only", False)],
            }

        roots = by_parent.get(None, [])
        tree: list[dict] = []
        for root in roots:
            children = by_parent.get(int(root.id), [])
            if not children:
                if getattr(root, "is_filter_only", False):
                    continue
                tree.append(
                    {
                        "key": root.slug,
                        "label_vi": root.name_vi,
                        "id": root.id,
                        "name_en": root.name_en,
                        "is_filter_only": False,
                        "children": [],
                    }
                )
                continue
            tree.append(
                {
                    "key": root.slug,
                    "label_vi": root.name_vi,
                    "id": root.id,
                    "name_en": root.name_en,
                    "is_filter_only": bool(getattr(root, "is_filter_only", False)),
                    "children": [
                        {
                            "key": c.slug,
                            "label_vi": c.name_vi,
                            "id": c.id,
                            "name_en": c.name_en,
                            "is_filter_only": False,
                        }
                        for c in children
                        if not getattr(c, "is_filter_only", False)
                    ],
                }
            )
        return tree

    def list_equipment_labels(self) -> list[dict]:
        rows = (
            self.db.query(Equipment)
            .filter(Equipment.is_active.is_(True))
            .order_by(Equipment.sort_order.asc(), Equipment.name_vi.asc())
            .all()
        )
        out: list[dict] = []
        for r in rows:
            local = local_image_relpath(r.slug)
            out.append(
                {
                    "key": r.slug,
                    "label_vi": r.name_vi,
                    "id": r.id,
                    "category": r.category,
                    "name_en": r.name_en,
                    "image_url": local or r.image_url,
                    "image_source": None if local else r.image_source,
                    "image_attribution": None if local else r.image_attribution,
                }
            )
        return out

    def search_equipment_catalog(
        self,
        pagination: PaginationParams,
        q: str | None = None,
        category: str | None = None,
    ) -> tuple[list[dict], int]:
        from sqlalchemy import func

        count_sq = (
            self.db.query(
                ExerciseEquipment.equipment_id.label("equipment_id"),
                func.count(ExerciseEquipment.exercise_id).label("exercise_count"),
            )
            .group_by(ExerciseEquipment.equipment_id)
            .subquery()
        )
        query = (
            self.db.query(Equipment, func.coalesce(count_sq.c.exercise_count, 0))
            .outerjoin(count_sq, count_sq.c.equipment_id == Equipment.id)
            .filter(Equipment.is_active.is_(True))
        )
        if q:
            pattern = f"%{q}%"
            query = query.filter(
                or_(
                    Equipment.name_vi.ilike(pattern),
                    Equipment.name_en.ilike(pattern),
                    Equipment.category.ilike(pattern),
                )
            )
        if category:
            query = query.filter(Equipment.category == category)

        total = query.count()
        rows = (
            query.order_by(Equipment.sort_order.asc(), Equipment.name_vi.asc())
            .offset(pagination.offset)
            .limit(pagination.page_size)
            .all()
        )
        items = []
        for eq, exercise_count in rows:
            local = local_image_relpath(eq.slug)
            items.append(
                {
                    "id": eq.id,
                    "slug": eq.slug,
                    "name_vi": eq.name_vi,
                    "name_en": eq.name_en,
                    "category": eq.category,
                    "image_url": local or eq.image_url,
                    "image_source": None if local else eq.image_source,
                    "image_attribution": None if local else eq.image_attribution,
                    "exercise_count": int(exercise_count or 0),
                }
            )
        return items, total

    def list_equipment_categories(self) -> list[str]:
        rows = (
            self.db.query(Equipment.category)
            .filter(Equipment.is_active.is_(True), Equipment.category.isnot(None))
            .order_by(Equipment.sort_order.asc())
            .all()
        )
        seen: list[str] = []
        for (cat,) in rows:
            if cat and cat not in seen:
                seen.append(cat)
        return seen

    def search_foods(
        self,
        pagination: PaginationParams,
        q: str | None = None,
        category_id: int | None = None,
        is_common: bool | None = None,
        tag: str | None = None,
        diet: str | None = None,
        owner_user_id: str | None = None,
        mine_only: bool = False,
        exclude_raw: bool = False,
        macro_role: str | None = None,
        complete_meal: bool | None = None,
    ) -> tuple[list, int]:
        from sqlalchemy import cast, String

        query = self.db.query(Food)
        # Active catalog (owner null) + caller's custom foods; hide deprecated trash
        if mine_only and owner_user_id:
            query = query.filter(Food.owner_user_id == owner_user_id)
        elif owner_user_id:
            query = query.filter(
                or_(
                    and_(Food.owner_user_id.is_(None), Food.status == "active"),
                    Food.owner_user_id == owner_user_id,
                )
            )
        else:
            query = query.filter(Food.owner_user_id.is_(None), Food.status == "active")

        if q:
            pattern = f"%{q}%"
            alias_ids = (
                self.db.query(FoodAlias.food_id).filter(FoodAlias.alias.ilike(pattern)).subquery()
            )
            query = query.filter(or_(Food.name_vi.ilike(pattern), Food.id.in_(alias_ids)))
        if category_id is not None:
            query = query.filter(Food.category_id == category_id)
        if is_common is not None:
            query = query.filter(Food.is_common.is_(is_common))

        diet_key = (diet or "").strip().lower()
        tag_key = (tag or "").strip().lower()
        if diet_key == "high_protein":
            query = query.filter(or_(Food.protein_g >= 15, cast(Food.tags, String).ilike("%protein%")))
        elif diet_key == "low_carb":
            query = query.filter(Food.carbs_g <= 15)
        elif diet_key == "low_fat":
            query = query.filter(Food.fat_g <= 5)
        elif tag_key:
            query = query.filter(cast(Food.tags, String).ilike(f'%"{tag_key}"%'))
        elif diet_key in {"protein", "carb"}:
            query = query.filter(cast(Food.tags, String).ilike(f'%"{diet_key}"%'))

        if exclude_raw:
            query = query.filter(or_(Food.prep_state.is_(None), Food.prep_state != "raw"))
        if complete_meal:
            query = query.filter(Food.is_complete_meal.is_(True))
        role = (macro_role or "").strip().lower()
        if role == "protein":
            query = query.filter(
                or_(
                    Food.protein_g >= 15,
                    cast(Food.macro_roles, String).ilike("%protein%"),
                    cast(Food.tags, String).ilike("%protein%"),
                )
            )
        elif role == "carb":
            query = query.filter(
                or_(
                    Food.carbs_g >= 15,
                    cast(Food.macro_roles, String).ilike("%carb%"),
                    cast(Food.tags, String).ilike("%carb%"),
                )
            )
        elif role == "produce":
            query = query.filter(cast(Food.macro_roles, String).ilike("%produce%"))
        elif role in {"fat", "dairy"}:
            query = query.filter(cast(Food.macro_roles, String).ilike(f"%{role}%"))

        total = query.count()
        items = (
            query.order_by(
                Food.ai_priority.desc(),
                Food.default_for_ai.desc(),
                Food.is_common.desc(),
                Food.name_vi.asc(),
            )
            .offset(pagination.offset)
            .limit(pagination.page_size)
            .all()
        )
        return items, total
