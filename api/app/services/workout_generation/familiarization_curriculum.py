"""Deterministic familiarization curricula built from the live exercise catalog."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import not_, or_
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import BadRequestError
from app.models.entities import Exercise
from app.schemas.plans import CreatePlanRequest, PlanDayIn, PlanExerciseIn
from app.services.plan_service import PlanService
from app.services.workout_generation.fitness_standards import (
    PATH_META,
    evaluate_fitness_baseline,
    familiarization_catalog,
    familiarization_overview_copy,
    normalize_familiarization_path,
)
from app.services.workout_generation.bmi import (
    bmi_band_from_payload,
    build_familiarization_weight_goal,
    goal_from_bmi_band,
    is_heavy_bmi,
    is_overweight_bmi,
)
from app.services.workout_generation.meal_engine import (
    apply_meals_to_days,
    apply_meals_with_schedule,
    generate_meals,
)
from app.services.workout_generation.nutrition_targets import estimate_targets
from app.services.workout_generation.shortlist import apply_catalog_location_sql
from app.services.workout_generation.weekly_volume import (
    fold_lift_name,
    is_knee_pushup_name,
    is_pushup_name,
    is_standard_pushup_name,
)
from app.services.workout_generation.familiarization_data import (
    FAMILIARIZATION_WEEKS,
    FIRST_PUSH_PULL_BAR_START_DAY,
    FIRST_PUSH_PULL_DAYS,
    FIRST_PUSH_PULL_EARLY_BAR_DAY,
    FIRST_PUSH_PULL_INVERTED_ROW_DAY,
    FIRST_PUSH_PULL_SCAPULAR_DAY,
    FIRST_PUSH_PULL_SESSIONS_PER_WEEK,
    FIRST_PUSH_PULL_WEEKS,
    MARKER_PREFIX,
    _EXCLUDE_NEEDLES,
    _PATH_CAPS,
    _WEEK_ADVANCE,
    _WEEK_LOAD,
    _WEEKDAY_VI,
)

_PATH_LABELS = {str(item["key"]): str(item["label_vi"]) for item in PATH_META}


def _blob(ex: Exercise) -> str:
    return fold_lift_name(f"{ex.name_vi or ''} {ex.name_en or ''}")


def _has_any(blob: str, needles: tuple[str, ...]) -> bool:
    return any(n in blob for n in needles)


def _is_excluded(ex: Exercise) -> bool:
    notes = str(ex.notes_vi or "")
    if notes.startswith(MARKER_PREFIX):
        return True
    blob = _blob(ex)
    if _has_any(
        blob,
        ("band assisted", "tro luc day", "hit xa tro luc day", "hít xà trợ lực dây"),
    ) and "machine" not in blob:
        return False
    return _has_any(blob, _EXCLUDE_NEEDLES)


def _first_match(
    pool: list[Exercise],
    *,
    require: tuple[str, ...],
    reject: tuple[str, ...] = (),
    predicate=None,
) -> Exercise | None:
    for ex in pool:
        blob = _blob(ex)
        if reject and _has_any(blob, reject):
            continue
        if require and not _has_any(blob, require):
            continue
        if predicate is not None and not predicate(ex):
            continue
        return ex
    return None


def _unique(rows: list[Exercise | None]) -> list[tuple[int, Exercise]]:
    seen: set[int] = set()
    out: list[tuple[int, Exercise]] = []
    for row in rows:
        if row is None:
            continue
        eid = int(row.id)
        if eid in seen:
            continue
        seen.add(eid)
        out.append((len(out), row))
    return out


def _build_push_ladder(pool: list[Exercise]) -> list[tuple[int, Exercise]]:
    wall = _first_match(
        pool,
        require=("wall", "tuong"),
        predicate=lambda ex: is_pushup_name(ex.name_vi) or is_pushup_name(ex.name_en),
    )
    knee = next(
        (ex for ex in pool if is_knee_pushup_name(ex.name_vi, ex.name_en)),
        None,
    )
    if knee is None:
        knee = _first_match(
            pool,
            require=("quy goi", "chong goi", "knee"),
            predicate=lambda ex: is_pushup_name(ex.name_vi) or is_pushup_name(ex.name_en),
        )
    negative = _first_match(
        pool,
        require=("negative", "pha am", "eccentric"),
        predicate=lambda ex: is_pushup_name(ex.name_vi) or is_pushup_name(ex.name_en),
    )
    standard = next(
        (
            ex
            for ex in pool
            if is_standard_pushup_name(ex.name_vi, ex.name_en)
            and not _has_any(_blob(ex), ("diamond", "kim cuong", "pike", "clap", "plyo"))
        ),
        None,
    )
    if standard is None:
        standard = next(
            (
                ex
                for ex in pool
                if (is_pushup_name(ex.name_vi) or is_pushup_name(ex.name_en))
                and not is_knee_pushup_name(ex.name_vi, ex.name_en)
                and not _has_any(_blob(ex), ("wall", "tuong"))
            ),
            None,
        )
    tempo = _first_match(
        pool,
        require=("tempo",),
        predicate=lambda ex: is_pushup_name(ex.name_vi) or is_pushup_name(ex.name_en),
    )
    return _unique([wall, knee, negative, standard, tempo])


def _build_pull_ladder(pool: list[Exercise]) -> list[tuple[int, Exercise]]:
    hang = _first_match(
        pool,
        require=("dead hang", "treo nguoi"),
        reject=("row", "cheo", "pull", "keo", "chin"),
    )
    if hang is None:
        hang = _first_match(
            pool,
            require=("hang", "treo"),
            reject=("row", "cheo", "pull", "keo", "chin", "active", "chu dong"),
        )
    scapular = _first_match(
        pool,
        require=("scapular", "active hang", "treo nguoi chu dong", "ba vai"),
    )
    inverted = _first_match(
        pool,
        require=("inverted row", "australian", "cheo up", "hanging row"),
    )
    negative = _first_match(
        pool,
        require=("negative", "pha am", "eccentric"),
        predicate=lambda ex: _has_any(_blob(ex), ("pull", "keo xa", "chin")),
    )
    pullup = _first_match(
        pool,
        require=("pull-up", "pull up", "pullup", "keo xa", "chin-up", "chin up"),
        reject=(
            "negative",
            "pha am",
            "scapular",
            "ba vai",
            "partial",
            "ban phan",
            "assisted",
            "inverted",
            "row",
        ),
    )
    return _unique([hang, scapular, inverted, negative, pullup])


def _build_squat_ladder(pool: list[Exercise]) -> list[tuple[int, Exercise]]:
    bodyweight = _first_match(
        pool,
        require=("squat", "ngoi xom", "dung len ngoi xuong"),
        reject=("split", "bulgarian", "jump", "goblet", "front", "back squat", "overhead"),
    )
    tempo = _first_match(
        pool,
        require=("tempo",),
        predicate=lambda ex: _has_any(_blob(ex), ("squat", "ngoi xom")),
    )
    return _unique([bodyweight, tempo])


def _build_plank_ladder(pool: list[Exercise]) -> list[tuple[int, Exercise]]:
    knee = _first_match(
        pool,
        require=("plank",),
        predicate=lambda ex: "goi" in _blob(ex) or "knee" in _blob(ex),
    )
    # Ưu tiên chống khuỷu / cẳng tay — không dùng chống thẳng tay (hand plank).
    elbow = _first_match(
        pool,
        require=(
            "front plank on elbow",
            "plank on elbow",
            "forearm plank",
            "chong khuyu",
            "cang tay",
        ),
        reject=("side", "ben", "goi", "knee", "hand", "thang tay"),
    )
    front = elbow or _first_match(
        pool,
        require=("plank",),
        reject=(
            "side",
            "ben",
            "goi",
            "knee",
            "up-down",
            "walk",
            "hand",
            "thang tay",
            "chong thang",
        ),
    )
    if front is None:
        front = _first_match(
            pool,
            require=("plank", "chong nguoi"),
            reject=("side", "ben", "hand", "thang tay"),
        )
    return _unique([knee, front])


def _build_run_ladder(pool: list[Exercise]) -> list[tuple[int, Exercise]]:
    """Prefer Trail Run (Chạy bền); never treat walking lunges as cardio."""
    trail = _first_match(
        pool,
        require=("trail run", "chay ben", "chay dia hinh"),
        reject=("lunge", "chung chan", "treadmill", "may chay"),
    )
    run = _first_match(
        pool,
        require=(
            "jog",
            "easy run",
            "continuous run",
            "long run",
            "chay nhe",
            "chay dai",
            "chay lien tuc",
        ),
        reject=(
            "sprint",
            "nuoc rut",
            "sled",
            "xe truot",
            "lunge",
            "chung chan",
            "interval",
            "tempo",
            "treadmill",
            "may chay",
            "trail",
        ),
    )
    walk = _first_match(
        pool,
        require=("di bo", "march in place", "walk run", "di bo – chay", "di bo chay"),
        reject=("lunge", "chung chan", "treadmill", "may chay", "incline"),
    )
    return _unique([trail, run, walk])


def _catalog_exercises(
    db: Session,
) -> dict[str, list[tuple[int, Exercise]]]:
    q = db.query(Exercise).filter(Exercise.is_active.is_(True))
    q = q.filter(
        or_(
            Exercise.notes_vi.is_(None),
            not_(Exercise.notes_vi.like(f"{MARKER_PREFIX}%")),
        )
    )
    q, *_ = apply_catalog_location_sql(
        q,
        db,
        location="home",
        no_equipment=False,
        equipment_slugs=["pull-up-bar"],
    )
    pool = [ex for ex in q.all() if not _is_excluded(ex)]
    families = {
        "push": _build_push_ladder(pool),
        "pull": _build_pull_ladder(pool),
        "squat": _build_squat_ladder(pool),
        "plank": _build_plank_ladder(pool),
        "run": _build_run_ladder(pool),
    }
    missing = [name for name, rows in families.items() if not rows]
    if missing:
        raise BadRequestError(
            "Kho bài tập chưa đủ bài cho lộ trình Làm quen ("
            + ", ".join(missing)
            + "). Thêm bài thể trọng / xà đơn tương ứng rồi thử lại."
        )
    return families


def _catalog_pool(
    db: Session,
    *,
    no_equipment: bool,
    equipment_slugs: list[str],
) -> list[Exercise]:
    q = db.query(Exercise).filter(Exercise.is_active.is_(True))
    q = q.filter(
        or_(
            Exercise.notes_vi.is_(None),
            not_(Exercise.notes_vi.like(f"{MARKER_PREFIX}%")),
        )
    )
    q, *_ = apply_catalog_location_sql(
        q,
        db,
        location="home",
        no_equipment=no_equipment,
        equipment_slugs=equipment_slugs,
    )
    return sorted(
        (ex for ex in q.all() if not _is_excluded(ex)),
        key=lambda ex: int(ex.id),
    )


def _named_or_pattern(
    pool: list[Exercise],
    *,
    names: tuple[str, ...],
    patterns: tuple[str, ...] = (),
) -> Exercise | None:
    match = _first_match(pool, require=names)
    if match is not None:
        return match
    wanted = {value.strip().lower() for value in patterns}
    return next(
        (
            ex
            for ex in pool
            if str(ex.movement_pattern or "").strip().lower() in wanted
        ),
        None,
    )


def _payload_equipment_slugs(payload: dict[str, Any] | None) -> list[str]:
    raw = (payload or {}).get("equipment_list") or (payload or {}).get("available_equipment") or []
    out: list[str] = []
    seen: set[str] = set()
    for item in raw:
        slug = str(item or "").strip().lower()
        if not slug or slug in seen:
            continue
        seen.add(slug)
        out.append(slug)
    return out


def _pick_inverted_row(*, has_bar_or_rings: bool, ring, bar, table):
    if has_bar_or_rings:
        return ring or bar or table
    return table or bar or ring


def _first_push_pull_catalog(
    db: Session, gender: str, *, user_slugs: list[str] | None = None
) -> dict[str, Exercise]:
    no_eq = _catalog_pool(db, no_equipment=True, equipment_slugs=[])
    with_gear = _catalog_pool(
        db,
        no_equipment=False,
        equipment_slugs=["pull-up-bar", "resistance-band"],
    )
    with_bar = _catalog_pool(
        db, no_equipment=False, equipment_slugs=["pull-up-bar"]
    )

    push = _build_push_ladder(no_eq)
    squat = _build_squat_ladder(no_eq)
    plank = _build_plank_ladder(no_eq)
    run = _build_run_ladder(no_eq)
    bar_pull = _build_pull_ladder(with_bar)

    def ladder_match(
        rows: list[tuple[int, Exercise]],
        predicate,
    ) -> Exercise | None:
        return next((row for _, row in rows if predicate(row)), None)

    floor_pull = _named_or_pattern(
        no_eq,
        names=(
            "superman",
            "bird dog",
            "bird-dog",
            "y-t-w",
            "ytw",
            "reverse snow",
            "snow angel",
        ),
        patterns=("v_pull", "vertical_pull", "h_pull", "horizontal_pull"),
    )
    backpack_bent = _first_match(
        no_eq,
        require=("backpack", "balo", "ba lo"),
        reject=(
            "one-arm",
            "one arm",
            "single arm",
            "mot tay",
            "rdl",
            "romanian",
            "deadlift",
            "pullover",
            "good morning",
            "hinge",
        ),
        predicate=lambda ex: _has_any(
            _blob(ex), ("row", "cheo", "bent-over", "bent over")
        ),
    )
    backpack_one_arm = _first_match(
        no_eq,
        require=("backpack", "balo", "ba lo"),
        predicate=lambda ex: _has_any(
            _blob(ex), ("one-arm", "one arm", "single arm", "mot tay")
        ),
    )
    if backpack_bent is None and backpack_one_arm is None:
        backpack_bent = _first_match(
            no_eq,
            require=("backpack", "balo", "ba lo"),
        )
    elevated_table_row = _first_match(
        no_eq,
        require=("elevated feet", "feet elevated", "chan tren ghe"),
        predicate=lambda ex: _has_any(
            _blob(ex), ("inverted", "duoi ban", "table row", "row")
        ),
    )
    table_row = _first_match(
        no_eq,
        require=("inverted", "duoi ban", "table row", "gamm ban", "gầm bàn"),
        reject=("elevated", "chan tren ghe", "feet elevated", "chan tren"),
    ) or _first_match(
        with_gear,
        require=("table inverted", "duoi ban", "keo nguoi duoi ban"),
        reject=("elevated", "chan tren ghe", "feet elevated"),
    )
    bar_row = ladder_match(
        bar_pull,
        lambda ex: _has_any(
            _blob(ex),
            ("inverted row", "australian", "cheo up", "hanging row", "bar inverted"),
        )
        and not _has_any(_blob(ex), ("elevated", "chan tren ghe", "feet elevated")),
    ) or _first_match(
        with_bar,
        require=("inverted row", "australian", "bar inverted"),
        reject=("elevated", "chan tren ghe", "feet elevated"),
    )
    user = {str(s).strip().lower() for s in (user_slugs or ()) if str(s).strip()}
    has_bar_or_rings = bool(user & {"pull-up-bar", "gymnastic-rings"})
    ring_row = None
    if has_bar_or_rings:
        with_rings = _catalog_pool(
            db, no_equipment=False, equipment_slugs=["gymnastic-rings"]
        )
        ring_row = _first_match(
            with_rings,
            require=("ring row", "cheo vong", "chèo vòng", "keo vong"),
        )
    inverted_row = _pick_inverted_row(
        has_bar_or_rings=has_bar_or_rings,
        ring=ring_row,
        bar=bar_row,
        table=table_row,
    )
    bar_inverted_row = bar_row
    rows: dict[str, Exercise | None] = {
        "wall_push": ladder_match(
            push, lambda ex: _has_any(_blob(ex), ("wall", "tuong"))
        ),
        "knee_push": ladder_match(
            push, lambda ex: is_knee_pushup_name(ex.name_vi, ex.name_en)
        ),
        "strict_push": ladder_match(
            push, lambda ex: is_standard_pushup_name(ex.name_vi, ex.name_en)
        ) or _first_match(
            no_eq,
            require=("push up", "push-up", "chong day"),
            reject=("knee", "quy", "wall", "tuong", "incline", "decline", "diamond", "pike"),
        ),
        "floor_pull": floor_pull,
        "backpack_bent": backpack_bent,
        "backpack_one_arm": backpack_one_arm,
        "squat": squat[0][1] if squat else None,
        "plank": plank[-1][1] if plank else None,
        "cardio": run[0][1] if run else (run[-1][1] if run else None),
        "dead_hang": ladder_match(
            bar_pull,
            lambda ex: _has_any(_blob(ex), ("dead hang", "treo nguoi", "treo xa"))
            and not _has_any(_blob(ex), ("active", "chu dong", "scapular", "ba vai")),
        ),
        "scapular": _first_match(
            with_bar,
            require=(
                "scapular",
                "ba vai",
                "keo xa bang ba vai",
                "keo xa 1/3",
                "1/3 pull",
            ),
        ),
        "inverted_row": inverted_row,
        "bar_inverted_row": bar_inverted_row,
        "elevated_row": elevated_table_row
        or _first_match(
            no_eq + with_gear,
            require=("elevated", "chan tren ghe", "feet elevated"),
            predicate=lambda ex: _has_any(_blob(ex), ("inverted", "duoi ban", "row")),
        ),
        "incline_push": ladder_match(
            push,
            lambda ex: _has_any(
                _blob(ex), ("incline", "ke tay", "elevated", "tay tren ghe")
            )
            and not is_knee_pushup_name(ex.name_vi, ex.name_en)
            and not _has_any(_blob(ex), ("decline", "chan tren ghe", "diamond")),
        )
        or _first_match(
            no_eq,
            require=("incline", "ke tay", "tay tren ghe"),
            reject=("knee", "quy", "decline", "diamond"),
        ),
        "diamond_push": _first_match(no_eq, require=("diamond", "kim cuong")),
        "decline_push": _first_match(
            no_eq,
            require=("decline", "chan tren ghe"),
            predicate=lambda ex: is_pushup_name(ex.name_vi) or is_pushup_name(ex.name_en),
        ),
        "strict_pull": ladder_match(
            bar_pull,
            lambda ex: _has_any(
                _blob(ex), ("pull-up", "pull up", "pullup", "keo xa", "chin-up", "hit xa")
            )
            and not _has_any(
                _blob(ex),
                ("negative", "pha am", "partial", "ban phan", "scapular", "hang", "assisted", "tro luc", "inverted"),
            ),
        ),
        "band_pull": _first_match(
            with_gear,
            require=("band assisted", "tro luc day", "hit xa tro luc day", "band pull"),
        ),
        "glute_bridge": _first_match(
            no_eq,
            require=("glute bridge", "cau mong", "nang mong"),
            reject=("single", "mot chan", "one-leg", "dumbbell", "band"),
        ),
        "glute_single": _first_match(
            no_eq,
            require=("single leg glute", "cau mong mot chan", "glute bridge 1"),
        )
        or _first_match(
            no_eq,
            require=("glute", "cau mong", "nang mong"),
            predicate=lambda ex: _has_any(_blob(ex), ("single", "mot chan", "one-leg")),
        ),
        "lunge": _first_match(
            no_eq,
            require=("reverse lunge", "chung chan ra sau", "static lunge", "forward lunge"),
            reject=("barbell", "dumbbell", "walking"),
        )
        or _first_match(no_eq, require=("lunge", "chung chan"), reject=("barbell", "dumbbell")),
        "walking_lunge": _first_match(
            no_eq, require=("walking lunge", "chung chan buoc")
        ),
        "bulgarian": _first_match(
            no_eq,
            require=("bulgarian", "chan sau ke ghe"),
            reject=("dumbbell", "goblet", "kettle"),
        ),
        "jump_squat": _first_match(no_eq, require=("jump squat", "squat bat nhay", "ngoi xom bat")),
        "hip_thrust": _first_match(
            no_eq,
            require=("hip thrust", "day hong"),
            reject=("barbell", "dumbbell", "machine", "kettle"),
        ),
        "backpack_rdl": _first_match(
            no_eq,
            require=("backpack", "balo", "ba lo"),
            predicate=lambda ex: _has_any(
                _blob(ex), ("rdl", "romanian", "deadlift", "gap hong")
            )
            and not _has_any(_blob(ex), ("single", "mot chan", "one-leg")),
        ),
        "backpack_rdl_sl": _first_match(
            no_eq,
            require=("backpack", "balo", "ba lo"),
            predicate=lambda ex: _has_any(
                _blob(ex), ("rdl", "romanian", "deadlift", "gap hong")
            )
            and _has_any(_blob(ex), ("single", "mot chan", "one-leg")),
        ),
        "backpack_gm": (
            None
            if has_bar_or_rings
            else _first_match(no_eq, require=("good morning", "cui nguoi om balo"))
        ),
        "hollow": _first_match(no_eq, require=("hollow", "than rong")),
        "bird_dog": _first_match(no_eq, require=("bird dog", "gio tay chan")),
        "jumping_jack": _first_match(
            no_eq,
            require=("jumping jack", "nhay dang chan", "nhảy dang chân"),
        ),
        "elbow_plank": _first_match(
            no_eq,
            require=(
                "front plank on elbow",
                "plank on elbow",
                "forearm plank",
                "chong khuyu",
                "cang tay",
            ),
            reject=("side", "ben", "goi", "knee", "hand", "thang tay"),
        ),
        "box_squat": _first_match(no_eq, require=("box squat", "ngoi xom xuong hop", "cham ghe")),
    }
    rows["active_hang"] = rows["scapular"] or rows["dead_hang"]
    rows["negative_push"] = rows["knee_push"]
    rows["negative_pull"] = rows["scapular"] or rows["dead_hang"]
    rows["partial_pull"] = rows["strict_pull"] or rows["inverted_row"]
    rows["chin_hold_negative"] = None
    # Làm quen dùng chống khuỷu, không dùng chống thẳng tay.
    if rows.get("elbow_plank") is not None:
        rows["plank"] = rows["elbow_plank"]
    rows["hand_plank"] = rows.get("plank")

    required = _familiarization_required_keys(
        gender=gender,
        has_bar_or_rings=has_bar_or_rings,
        has_backpack=backpack_bent is not None or backpack_one_arm is not None,
    )
    _raise_if_catalog_missing(rows, required)
    return {key: row for key, row in rows.items() if row is not None}


def _familiarization_required_keys(
    *,
    gender: str,
    has_bar_or_rings: bool,
    has_backpack: bool,
) -> dict[str, str]:
    required = {
        "wall_push": "chống đẩy tường",
        "knee_push": "chống đẩy quỳ gối",
        "squat": "squat thể trọng",
        "plank": "plank",
        "cardio": "đi bộ / chạy",
        "inverted_row": "kéo người nằm (bàn hoặc xà)",
    }
    if not has_backpack:
        required["floor_pull"] = "chèo balo hoặc Superman / bird-dog"
    if gender == "male":
        required["strict_push"] = "chống đẩy chuẩn"
    if has_bar_or_rings:
        required["dead_hang"] = "treo người trên xà"
    return required


def _raise_if_catalog_missing(
    rows: dict[str, Exercise | None],
    required: dict[str, str],
) -> None:
    missing = [label for key, label in required.items() if rows.get(key) is None]
    if missing:
        raise BadRequestError(
            "Kho bài tập thiếu bài cho lộ trình 60 ngày: "
            + ", ".join(missing)
            + "."
        )


def _require_knee_pushup(families: dict[str, list[tuple[int, Exercise]]]) -> None:
    knee = _ladder_index_for(
        families, "push", lambda ex: is_knee_pushup_name(ex.name_vi, ex.name_en)
    )
    if knee is None:
        raise BadRequestError(
            "Kho bài tập thiếu chống đẩy quỳ gối — cần có bài này để tạo lộ trình "
            "Chinh phục chống đẩy, kéo xà."
        )


def _number(base: dict[str, Any], key: str) -> int:
    try:
        return max(0, int(base.get(key) or 0))
    except (TypeError, ValueError):
        return 0


def _baseline_capacity_zero(base: dict[str, Any], *keys: str) -> bool:
    """True only when at least one key is present and every present key is 0."""
    present = False
    for key in keys:
        if key not in base:
            continue
        present = True
        if _number(base, key) > 0:
            return False
    return present


def _l2_main_sets(week: int, *, peak: int = 4) -> int:
    w = max(1, min(9, int(week)))
    if w <= 2:
        return min(3, peak)
    if w <= 6:
        return peak
    return min(2, peak)


def _normalize_gender(raw: Any) -> str:
    return "female" if str(raw or "").strip().lower() == "female" else "male"


def _normalize_bmi_band(raw: Any) -> str:
    key = str(raw or "normal").strip().lower()
    if key in {"underweight", "normal", "overweight", "obese_1", "obese_2"}:
        return key
    return "normal"


def _cardio_line(level: str, week: int, band: str) -> str:
    w = max(1, min(8, int(week)))
    if is_heavy_bmi(band):
        if level == "first_push_pull":
            return "10 phút đi bộ nhịp vừa (nói chuyện được)"
        minutes = "12–15" if w <= 4 else "15–18"
        return f"{minutes} phút đi bộ nhịp vừa (nói chuyện được)"
    if band == "underweight":
        return "8–10 phút đi bộ nhanh nhịp vừa (nói chuyện được)"
    if band == "overweight":
        if level == "first_push_pull":
            return "10–12 phút đi bộ/chạy nhẹ nhịp vừa (nói chuyện được)"
        return "12–15 phút đi/chạy nhẹ nhịp vừa (nói chuyện được)"
    if level == "first_push_pull":
        if w <= 2:
            return "10–12 phút đi bộ nhanh nhịp vừa (nói chuyện được)"
        if w <= 4:
            return "12–15 phút đi/chạy nhịp vừa (nói chuyện được)"
        return "15 phút chạy nhẹ liên tục"
    if level == "basic_foundation":
        if w <= 3:
            return "12–15 phút chạy nhịp vừa (nói chuyện được)"
        if w <= 7:
            return "15–18 phút chạy nhịp vừa (nói chuyện được)"
        return "12 phút chạy nhẹ"
    if w <= 3:
        return "15–18 phút chạy bền"
    if w <= 7:
        return "18–20 phút chạy bền"
    return "12–15 phút chạy nhẹ"


def _ladder_index_for(
    families: dict[str, list[tuple[int, Exercise]]],
    family: str,
    predicate,
) -> int | None:
    for step, row in families.get(family) or []:
        if predicate(row):
            return int(step)
    return None


def _gender_family_caps(
    path: str,
    gender: str,
    families: dict[str, list[tuple[int, Exercise]]],
) -> dict[str, int]:
    soft = dict(_PATH_CAPS[path])
    if path != "first_push_pull":
        return {
            key: min(soft[key], max(0, len(families[key]) - 1))
            for key in soft
        }

    push_rows = families["push"]
    pull_rows = families["pull"]
    push_last = max(0, len(push_rows) - 1)
    pull_last = max(0, len(pull_rows) - 1)

    if gender == "female":
        knee = _ladder_index_for(
            families, "push", lambda ex: is_knee_pushup_name(ex.name_vi, ex.name_en)
        )
        hang = 0
        soft["push"] = knee if knee is not None else min(1, push_last)
        soft["pull"] = hang
    else:
        standard = _ladder_index_for(
            families,
            "push",
            lambda ex: is_standard_pushup_name(ex.name_vi, ex.name_en),
        )
        pullup = _ladder_index_for(
            families,
            "pull",
            lambda ex: _has_any(
                _blob(ex), ("pull-up", "pull up", "pullup", "keo xa", "chin-up", "chin up")
            )
            and not _has_any(
                _blob(ex), ("negative", "pha am", "scapular", "ba vai", "hang", "treo")
            ),
        )
        soft["push"] = standard if standard is not None else push_last
        soft["pull"] = pullup if pullup is not None else pull_last

    for key in soft:
        soft[key] = min(soft[key], max(0, len(families[key]) - 1))
    return soft


def _baseline_is_zero(base: dict[str, Any]) -> bool:
    return (
        _number(base, "pushups_max") <= 0
        and _number(base, "pullups_max") <= 0
        and _number(base, "pull_hold_seconds") <= 0
        and _number(base, "inverted_rows_max") <= 0
    )


def _relative_start(family: str, base: dict[str, Any], size: int) -> int:
    last = max(0, size - 1)
    if size <= 1:
        return 0
    if family == "push":
        reps = _number(base, "pushups_max")
        variant = str(base.get("pushup_variant") or "standard")
        if reps <= 0:
            if variant == "standard":
                return max(0, last - 1)
            if variant == "knee":
                return min(1, last)
            return 0
        if variant == "standard":
            return last
        if variant == "knee":
            return min(max(1, last // 2), last)
        return min(1, last)
    if family == "pull":
        reps = _number(base, "pullups_max")
        hold = _number(base, "pull_hold_seconds")
        if reps > 0:
            return last
        if hold >= 20:
            return min(max(1, last - 1), last)
        if hold > 0:
            return min(1, last)
        return 0
    if family == "squat":
        return last if _number(base, "squats_max") >= 20 else 0
    if family == "plank":
        return last if _number(base, "plank_seconds") >= 30 else 0
    if family == "run":
        return last if _number(base, "run_10min_meters") >= 1200 else 0
    return 0


def _start_steps(
    path: str,
    base: dict[str, Any],
    families: dict[str, list[tuple[int, Exercise]]],
    *,
    gender: str,
) -> dict[str, int]:
    sizes = {key: len(rows) for key, rows in families.items()}
    caps = _gender_family_caps(path, gender, families)
    if path == "first_push_pull" and _baseline_is_zero(base):
        return {key: 0 for key in caps}
    starts = {
        key: _relative_start(key, base, sizes.get(key, 1)) for key in caps
    }
    if path == "first_push_pull":
        return {
            key: min(value, caps[key], max(0, sizes[key] - 2 if sizes[key] > 1 else 0))
            for key, value in starts.items()
        }
    return {
        key: min(max(0, value), max(0, sizes[key] - 1)) for key, value in starts.items()
    }


def _exercise_for(
    families: dict[str, list[tuple[int, Exercise]]], family: str, step: int
) -> Exercise:
    values = families.get(family) or []
    if not values:
        raise BadRequestError(
            "Kho bài tập chưa đủ bài cho lộ trình Làm quen. Vui lòng bổ sung bài tập."
        )
    eligible = [row for row_step, row in values if row_step <= step]
    return eligible[-1] if eligible else values[0][1]


def progression_step_for_week(
    path: str,
    family: str,
    start: int,
    week: int,
    *,
    max_step: int | None = None,
) -> int:
    cap = _PATH_CAPS[normalize_familiarization_path(path)][family]
    if max_step is not None:
        cap = min(cap, max(0, max_step))
    advance = _WEEK_ADVANCE[max(1, min(FAMILIARIZATION_WEEKS, int(week)))]
    return min(cap, max(0, int(start)) + advance)


def _parse_weekdays(raw: Any, sessions: int) -> list[int]:
    defaults = [1, 3, 5, 2, 4, 6, 7]
    values: list[int] = []
    if isinstance(raw, (list, tuple)):
        for item in raw:
            try:
                day = int(item)
            except (TypeError, ValueError):
                continue
            if 1 <= day <= 7 and day not in values:
                values.append(day)
    while len(values) < sessions:
        for day in defaults:
            if day not in values:
                values.append(day)
                break
        else:
            break
    return values[:sessions]


def _parse_start_time(raw: Any) -> str:
    text = str(raw or "").strip()
    if len(text) >= 4 and ":" in text:
        parts = text.split(":")
        try:
            hour = max(0, min(23, int(parts[0])))
            minute = max(0, min(59, int(parts[1][:2])))
            return f"{hour:02d}:{minute:02d}"
        except (TypeError, ValueError):
            pass
    return "18:00"


def _day_title(
    *,
    week: int,
    day_index: int,
    phase: str,
    weekdays: list[int],
    start_time: str,
) -> str:
    del weekdays, start_time  # schedule chips removed from UI; keep signature stable
    return f"Tuần {week} · Buổi {day_index + 1} — {phase}"


def _first_push_pull_week_steps(
    week: int,
    gender: str,
    families: dict[str, list[tuple[int, Exercise]]],
    caps: dict[str, int],
) -> dict[str, int]:
    """Absolute beginner block: wall → knee (many weeks) → male standard at the end."""
    knee = _ladder_index_for(
        families, "push", lambda ex: is_knee_pushup_name(ex.name_vi, ex.name_en)
    )
    if knee is None:
        knee = 0
    wall = 0
    for step, row in families.get("push") or []:
        if _has_any(_blob(row), ("wall", "tuong")):
            wall = int(step)
            break
    hang = 0
    pull_cap = caps["pull"]
    if week <= 2:
        push = wall
        pull = hang
    elif week <= 6:
        push = knee
        pull = hang if gender == "female" else min(1, pull_cap)
    elif gender == "female":
        push = knee
        pull = hang
    else:
        push = caps["push"]
        pull = pull_cap
    return {
        "push": min(push, caps["push"]),
        "pull": min(pull, caps["pull"]),
        "squat": 0 if week <= 4 else caps["squat"],
        "plank": 0 if week <= 3 else caps["plank"],
        "run": 0 if week <= 4 else caps["run"],
    }


_TRAIN_DAYS_60 = tuple(
    day
    for day in range(1, FIRST_PUSH_PULL_DAYS + 1)
    if (day - 1) % 7 in {0, 2, 4}
)
_FIRST_PUSH_PULL_TRAIN_DAYS = _TRAIN_DAYS_60


def _fixed_exercise(
    row: Exercise,
    *,
    sets: int,
    reps: str,
    rest: int,
    order: int,
    notes: str,
    section: str = "main",
) -> PlanExerciseIn:
    return PlanExerciseIn(
        exercise_id=int(row.id),
        sets=sets,
        reps=reps,
        rest_seconds=rest,
        section=section,
        notes_vi=notes,
        sort_order=order,
    )


_SESSION_ROLES = ("push_legs", "pull_back", "full")
_SESSION_TITLES = {
    "push_legs": "Đẩy & Thân dưới",
    "pull_back": "Kéo & Chuỗi sau",
    "full": "Toàn thân tổng hợp",
}
_SESSION_SPLITS = {
    "push_legs": "Push",
    "pull_back": "Pull",
    "full": "Full Body",
}


def _session_role(ordinal: int) -> str:
    return _SESSION_ROLES[(max(1, ordinal) - 1) % 3]


def _catalog_pick(catalog: dict[str, Exercise], *keys: str) -> tuple[str, Exercise] | tuple[None, None]:
    for key in keys:
        row = catalog.get(key)
        if row is not None:
            return key, row
    return None, None


def _make_add(catalog: dict[str, Exercise], items: list[PlanExerciseIn], default_note: str):
    def add(
        keys: str | tuple[str, ...],
        sets: int,
        reps: str,
        rest: int,
        *,
        section: str = "main",
        note: str | None = None,
    ) -> None:
        if isinstance(keys, str):
            keys = (keys,)
        _key, row = _catalog_pick(catalog, *keys)
        if row is None:
            return
        items.append(
            _fixed_exercise(
                row,
                sets=sets,
                reps=reps,
                rest=rest,
                order=len(items) + 1,
                notes=note or default_note,
                section=section,
            )
        )

    return add


def _pull_prep_keys(catalog: dict[str, Exercise], *, day: int) -> list[str]:
    """Week 1–2 backpack/floor; from week 3 inverted row."""
    if day >= FIRST_PUSH_PULL_INVERTED_ROW_DAY and catalog.get("inverted_row") is not None:
        keys = ["inverted_row"]
        if "backpack_bent" in catalog:
            keys.append("backpack_bent")
        return keys
    keys = [
        key
        for key in ("backpack_bent", "backpack_one_arm", "floor_pull")
        if key in catalog
    ]
    return keys or ["floor_pull"]


def _pull_prep_for_ordinal(
    catalog: dict[str, Exercise], ordinal: int, *, day: int
) -> tuple[str, str, str]:
    keys = _pull_prep_keys(catalog, day=day)
    key = keys[(max(1, ordinal) - 1) % len(keys)]
    if key == "inverted_row":
        return (
            key,
            "5–7",
            "Thân thẳng, kéo ngực về mép bàn/xà; gót chống sàn, không võng hông.",
        )
    if key.startswith("backpack"):
        return (
            key,
            "8–10",
            "Nhét sách vào balo 3–5 kg, kéo khuỷu sát sườn, siết lưng giữa; không vặn thân.",
        )
    return (
        key,
        "8–10",
        "Siết bả vai xuống và vào trong để chuẩn bị cho bài kéo.",
    )


def _warmup(add, role: str, *, include_jumping_jack: bool = False) -> None:
    if include_jumping_jack:
        add(
            "jumping_jack",
            2,
            "20–30 giây",
            60,
            section="warmup",
            note="Khởi động toàn thân, nhịp đều; RPE 3–4, không hụt hơi.",
        )
    if role == "pull_back":
        add(
            ("bird_dog", "wall_push"),
            2,
            "8 nhịp/bên",
            45,
            section="warmup",
            note="Kích hoạt lưng và xương chậu, RPE 3.",
        )
    else:
        add(
            "wall_push",
            2,
            "8 nhịp chậm",
            45,
            section="warmup",
            note="Khởi động vai, cổ tay; RPE 3, không tạo mỏi.",
        )


def _week_from_day(day: int) -> int:
    return max(1, min(9, (max(1, int(day)) - 1) // 7 + 1))


def _female_can_knee(base: dict[str, Any] | None) -> bool:
    """True when baseline already shows ~4+ knee (or floor) push-ups."""
    data = dict(base or {})
    reps = _number(data, "pushups_max")
    variant = str(data.get("pushup_variant") or "").strip().lower()
    if reps < 4:
        return False
    return variant in {"knee", "standard", "incline_low"}


def _female_l1_prescription(week: int, *, can_knee: bool) -> dict[str, Any]:
    """Weekly micro-progression for female Level 1 toward day-59 exit standards."""
    w = max(1, min(8, int(week)))

    # Shared pull / hang / squat / plank / cardio by week
    shared: dict[int, dict[str, Any]] = {
        1: {
            "pull_keys": ("backpack_bent", "backpack_one_arm", "floor_pull"),
            "pull_sets": 3,
            "pull_reps": "8–10",
            "hang_sets": 0,
            "hang_reps": "",
            "squat_sets": 3,
            "squat_reps": "8–10",
            "posterior_keys": ("glute_bridge", "squat"),
            "posterior_reps": "12–15",
            "plank_sets": 3,
            "plank_reps": "15–20 giây",
            "plank_full_sets": 2,
            "plank_full_reps": "15–20 giây",
            "cardio_reps": "10 phút đi bộ nhanh nhịp vừa (nói chuyện được)",
            "extra_lunge": False,
        },
        2: {
            "pull_keys": ("backpack_bent", "backpack_one_arm", "floor_pull"),
            "pull_sets": 3,
            "pull_reps": "10–12",
            "hang_sets": 2,
            "hang_reps": "8–10 giây",
            "squat_sets": 3,
            "squat_reps": "10–12",
            "posterior_keys": ("glute_bridge", "squat"),
            "posterior_reps": "12–15",
            "plank_sets": 3,
            "plank_reps": "20–25 giây",
            "plank_full_sets": 2,
            "plank_full_reps": "20–25 giây",
            "cardio_reps": "10 phút đi bộ nhanh nhịp vừa (nói chuyện được)",
            "extra_lunge": False,
        },
        3: {
            "pull_keys": ("inverted_row", "backpack_bent"),
            "pull_sets": 3,
            "pull_reps": "5–6",
            "hang_sets": 2,
            "hang_reps": "10–15 giây",
            "squat_sets": 3,
            "squat_reps": "12–15",
            "posterior_keys": ("glute_single", "glute_bridge", "squat"),
            "posterior_reps": "8–10/chân",
            "plank_sets": 3,
            "plank_reps": "25–30 giây",
            "plank_full_sets": 2,
            "plank_full_reps": "20–30 giây",
            "cardio_reps": "12 phút đi/chạy nhịp vừa (nói chuyện được)",
            "extra_lunge": False,
        },
        4: {
            "pull_keys": ("inverted_row", "backpack_bent"),
            "pull_sets": 3,
            "pull_reps": "6–8",
            "hang_sets": 2,
            "hang_reps": "15–20 giây",
            "squat_sets": 3,
            "squat_reps": "12–15 nhịp hạ 3 giây",
            "posterior_keys": ("glute_single", "glute_bridge", "squat"),
            "posterior_reps": "8–10/chân",
            "plank_sets": 3,
            "plank_reps": "30–35 giây",
            "plank_full_sets": 2,
            "plank_full_reps": "25–30 giây",
            "cardio_reps": "12 phút đi/chạy nhịp vừa (nói chuyện được)",
            "extra_lunge": False,
        },
        5: {
            "pull_keys": ("inverted_row", "elevated_row"),
            "pull_sets": 3,
            "pull_reps": "6–8",
            "hang_sets": 2,
            "hang_reps": "20–30 giây",
            "squat_sets": 3,
            "squat_reps": "15",
            "posterior_keys": ("glute_single", "glute_bridge", "squat"),
            "posterior_reps": "8–10/chân",
            "plank_sets": 3,
            "plank_reps": "30–40 giây",
            "plank_full_sets": 2,
            "plank_full_reps": "30–35 giây",
            "cardio_reps": "10 phút · mục tiêu khoảng 0,8 km",
            "extra_lunge": True,
        },
        6: {
            "pull_keys": ("inverted_row", "elevated_row"),
            "pull_sets": 3,
            "pull_reps": "8",
            "hang_sets": 3,
            "hang_reps": "25–35 giây",
            "squat_sets": 2,
            "squat_reps": "15–20",
            "posterior_keys": ("glute_single", "glute_bridge", "squat"),
            "posterior_reps": "10–12/chân",
            "plank_sets": 3,
            "plank_reps": "35–40 giây",
            "plank_full_sets": 2,
            "plank_full_reps": "30–40 giây",
            "cardio_reps": "10 phút · mục tiêu khoảng 0,9 km",
            "extra_lunge": True,
        },
        7: {
            "pull_keys": ("inverted_row", "elevated_row"),
            "pull_sets": 3,
            "pull_reps": "6–8",
            "hang_sets": 3,
            "hang_reps": "30–40 giây",
            "squat_sets": 1,
            "squat_reps": "làm tối đa >15",
            "posterior_keys": ("glute_single", "glute_bridge", "squat"),
            "posterior_reps": "10–12/chân",
            "plank_sets": 3,
            "plank_reps": "40–45 giây",
            "plank_full_sets": 2,
            "plank_full_reps": "35–40 giây",
            "cardio_reps": "10 phút · mục tiêu khoảng 0,95 km",
            "extra_lunge": True,
            "squat_follow": ("12", 2),  # 2×12 after AMRAP
        },
        8: {
            "pull_keys": ("inverted_row", "backpack_bent"),
            "pull_sets": 2,
            "pull_reps": "5–6",
            "hang_sets": 2,
            "hang_reps": "20 giây",
            "squat_sets": 2,
            "squat_reps": "12",
            "posterior_keys": ("glute_bridge", "squat"),
            "posterior_reps": "10–12",
            "plank_sets": 2,
            "plank_reps": "25 giây",
            "plank_full_sets": 2,
            "plank_full_reps": "20–25 giây",
            "cardio_reps": "10 phút đi/chạy nhẹ",
            "extra_lunge": False,
        },
    }

    # Push ladder: zero / <4 knee vs already can_knee
    if can_knee:
        push_by_week: dict[int, dict[str, Any]] = {
            1: {
                "push_keys": ("incline_push", "knee_push", "wall_push"),
                "push_sets": 3,
                "push_reps": "5–6",
                "push_note": None,
                "knee_probe": None,
            },
            2: {
                "push_keys": ("knee_push", "incline_push"),
                "push_sets": 3,
                "push_reps": "6–8",
                "push_note": None,
                "knee_probe": None,
            },
            3: {
                "push_keys": ("knee_push",),
                "push_sets": 3,
                "push_reps": "8–10",
                "push_note": None,
                "knee_probe": None,
            },
            4: {
                "push_keys": ("knee_push",),
                "push_sets": 3,
                "push_reps": "8–10",
                "push_note": "Hạ chậm 3 giây, còn dư 2–3 cái.",
                "knee_probe": None,
            },
            5: {
                "push_keys": ("knee_push",),
                "push_sets": 3,
                "push_reps": "10–12",
                "push_note": None,
                "knee_probe": None,
            },
            6: {
                "push_keys": ("knee_push",),
                "push_sets": 4,
                "push_reps": "8–10",
                "push_note": None,
                "knee_probe": None,
            },
            7: {
                "push_keys": ("knee_push",),
                "push_sets": 3,
                "push_reps": "8–10 (hiệp cuối làm tối đa)",
                "push_note": None,
                "knee_probe": None,
            },
            8: {
                "push_keys": ("knee_push", "incline_push"),
                "push_sets": 2,
                "push_reps": "6–8",
                "push_note": "Deload — form sạch, không kiệt.",
                "knee_probe": None,
            },
        }
    else:
        push_by_week = {
            1: {
                "push_keys": ("wall_push", "incline_push"),
                "push_sets": 3,
                "push_reps": "5–8",
                "push_note": "Học thân thẳng; tường hoặc ghế cao.",
                "knee_probe": None,
            },
            2: {
                "push_keys": ("incline_push", "wall_push"),
                "push_sets": 3,
                "push_reps": "6–8",
                "push_note": "Kê tay ghế/bàn chắc.",
                "knee_probe": None,
            },
            3: {
                "push_keys": ("incline_push", "wall_push"),
                "push_sets": 3,
                "push_reps": "8–10",
                "push_note": "Hạ dần độ cao ghế (càng thấp càng khó).",
                "knee_probe": None,
            },
            4: {
                "push_keys": ("incline_push", "wall_push"),
                "push_sets": 3,
                "push_reps": "8–10",
                "push_note": "Ghế thấp; form sạch trước khi thử quỳ.",
                "knee_probe": ("2–4", "Hiệp thử quỳ — dừng nếu vai nhún hoặc thân gãy."),
            },
            5: {
                "push_keys": ("knee_push", "incline_push"),
                "push_sets": 3,
                "push_reps": "4–6",
                "push_note": "Quỳ nhẹ; nếu chưa ổn giữ kê ghế thấp.",
                "knee_probe": None,
            },
            6: {
                "push_keys": ("knee_push", "incline_push"),
                "push_sets": 3,
                "push_reps": "6–8",
                "push_note": None,
                "knee_probe": None,
            },
            7: {
                "push_keys": ("knee_push", "incline_push"),
                "push_sets": 3,
                "push_reps": "8–10 (hiệp cuối làm tối đa)",
                "push_note": None,
                "knee_probe": None,
            },
            8: {
                "push_keys": ("incline_push", "knee_push", "wall_push"),
                "push_sets": 2,
                "push_reps": "6–8",
                "push_note": "Deload — biến thể đang quen, không kiệt.",
                "knee_probe": None,
            },
        }

    out = dict(shared[w])
    out.update(push_by_week[w])
    out["week"] = w
    return out


def _first_push_pull_training_exercises(
    catalog: dict[str, Exercise],
    *,
    gender: str,
    day: int,
    ordinal: int,
    can_knee: bool = False,
    bmi_band: str = "normal",
    push_zero: bool = False,
    pull_zero: bool = False,
) -> list[PlanExerciseIn]:
    del push_zero, pull_zero
    is_final_test = day == 59
    is_rehearsal = day == 57
    female = gender == "female"
    role = _session_role(ordinal)
    week = _week_from_day(day)
    band = _normalize_bmi_band(bmi_band)
    heavy = is_heavy_bmi(band)
    if is_final_test:
        phase_note = "Bài kiểm tra cuối: khởi động kỹ, chỉ tính lần/giây đúng form."
    elif is_rehearsal:
        phase_note = "Còn dư 3–4 cái · tập thử giống kiểm tra nhưng nhẹ hơn 2–3 lần, không kiệt."
    elif female and week <= 3:
        phase_note = "Còn dư 3–4 cái · học kỹ thuật, tiến bài tường → ghế → quỳ; dừng khi động tác xấu."
    elif day <= 14:
        phase_note = "Còn dư 3–4 cái · học kỹ thuật, dừng hiệp khi động tác bắt đầu xấu."
    else:
        phase_note = "Còn dư 2–3 cái · kiểm soát pha hạ 2–3 giây, thân người thẳng."

    items: list[PlanExerciseIn] = []
    add = _make_add(catalog, items, phase_note)
    _warmup(add, role, include_jumping_jack=not heavy)

    if is_final_test:
        if female:
            add("knee_push", 1, "Mục tiêu 4–10 lần đúng form", 180)
            add("dead_hang", 1, "Mục tiêu 20–45 giây", 180)
            add("squat", 1, "Mục tiêu 10–20 lần", 120)
            add(("hand_plank", "plank"), 1, "Mục tiêu 15–40 giây", 120)
            add("cardio", 1, "10 phút · mục tiêu 0,7–1,0 km", 0, section="cardio")
        else:
            add(
                ("strict_push", "incline_push", "knee_push"),
                1,
                "Mục tiêu 3–8 lần sàn (hoặc kê ghế)",
                180,
            )
            add(
                ("inverted_row", "elevated_row"),
                1,
                "Mục tiêu 6–10 kéo người nằm (bàn/xà)",
                180,
            )
            add("squat", 1, "Mục tiêu 12–25 lần", 120)
            add(("plank", "hand_plank"), 1, "Mục tiêu 20–50 giây", 120)
            add("cardio", 1, "10 phút · mục tiêu 0,8–1,2 km", 0, section="cardio")
        return items

    if is_rehearsal:
        if female:
            add("knee_push", 1, "4–7 lần (nhẹ hơn test 2–3)", 150)
            add(
                ("inverted_row", "elevated_row"),
                1,
                "5–6 lần kéo dưới bàn/ghế",
                150,
            )
            add("squat", 1, "8–15 lần", 120)
            add(("hand_plank", "plank"), 1, "15–35 giây", 90)
            add("cardio", 1, "10 phút · khoảng 0,6–0,8 km", 0, section="cardio")
        else:
            add(
                ("strict_push", "incline_push"),
                1,
                "3–6 lần (nhẹ hơn test, sàn hoặc ghế)",
                150,
            )
            add(
                ("inverted_row", "elevated_row"),
                1,
                "5–6 lần kéo dưới bàn/ghế (không kéo xà)",
                150,
            )
            add("squat", 1, "10–20 lần", 120)
            add(("plank", "hand_plank"), 1, "20–40 giây", 90)
            add("cardio", 1, "10 phút · khoảng 0,7–1,0 km", 0, section="cardio")
        return items

    if female:
        rx = _female_l1_prescription(week, can_knee=can_knee)

        def f_push() -> None:
            keys = rx["push_keys"]
            note = rx.get("push_note")
            add(
                keys if len(keys) > 1 else keys[0],
                int(rx["push_sets"]),
                str(rx["push_reps"]),
                90,
                note=note,
            )
            probe = rx.get("knee_probe")
            if probe:
                add(
                    "knee_push",
                    1,
                    probe[0],
                    120,
                    note=probe[1],
                )

        def f_pull() -> None:
            add(
                rx["pull_keys"],
                int(rx["pull_sets"]),
                str(rx["pull_reps"]),
                90 if week >= 3 else 75,
            )
            if int(rx["hang_sets"]) > 0:
                add("dead_hang", int(rx["hang_sets"]), str(rx["hang_reps"]), 120)

        def f_legs() -> None:
            add("squat", int(rx["squat_sets"]), str(rx["squat_reps"]), 75)
            follow = rx.get("squat_follow")
            if follow:
                add("squat", int(follow[1]), str(follow[0]), 75)
            if rx.get("extra_lunge"):
                if heavy:
                    add(("lunge", "squat"), 2, "6–8/chân", 75)
                else:
                    add(("lunge", "walking_lunge"), 2, "8–10/chân", 75)

        def f_posterior() -> None:
            add(
                rx["posterior_keys"],
                3,
                str(rx["posterior_reps"]),
                60,
            )

        def f_core(*, full: bool = False) -> None:
            sets = int(rx["plank_full_sets"] if full else rx["plank_sets"])
            reps = str(rx["plank_full_reps"] if full else rx["plank_reps"])
            add(("plank", "hand_plank"), sets, reps, 60)

        def f_cardio() -> None:
            reps = (
                str(rx["cardio_reps"])
                if band == "normal"
                else _cardio_line("first_push_pull", week, band)
            )
            add("cardio", 1, reps, 0, section="cardio")

        if role == "push_legs":
            f_push()
            f_legs()
            f_core()
            f_cardio()
        elif role == "pull_back":
            f_pull()
            f_posterior()
            f_core()
            f_cardio()
        else:
            f_push()
            f_pull()
            f_legs()
            f_core(full=True)
            f_cardio()
        return items

    early = day <= 14
    mid = 15 <= day <= 28

    def push_main() -> None:
        if heavy:
            if early:
                add(("wall_push", "incline_push"), 3, "6–8", 90)
            elif mid:
                add(("incline_push", "knee_push", "wall_push"), 3, "6–8", 90)
            else:
                add(("incline_push", "knee_push"), 3, "6–10", 90)
        elif early:
            add(("incline_push", "knee_push", "wall_push"), 3, "6–8", 90)
        elif mid:
            add("knee_push", 3, "8–10", 90)
        else:
            add("knee_push", 3, "8–12 (hiệp cuối thử sàn 3–5 nếu form vững)", 105)

    def pull_main() -> None:
        if early:
            add(("backpack_bent", "backpack_one_arm", "floor_pull"), 3, "8–10", 75)
        elif mid:
            add("inverted_row", 3, "5–7", 90)
        else:
            add(("scapular", "dead_hang"), 3, "5 nhịp bả vai hoặc 15–20 giây treo", 90)
            add("inverted_row", 3, "6", 90)

    def posterior() -> None:
        if early:
            add(("glute_bridge", "squat"), 3, "12–15", 60)
        else:
            add(("glute_single", "glute_bridge", "squat"), 3, "8–10/chân", 60)

    def legs() -> None:
        if early:
            add(("box_squat", "squat"), 3, "8–12" if heavy else "10–12", 75)
        elif mid:
            add(("box_squat", "squat"), 3, "10–12" if heavy else "12–15 nhịp hạ 3 giây", 75)
        elif heavy:
            add(("lunge", "box_squat", "squat"), 3, "8–10/chân", 75)
        else:
            add(("lunge", "walking_lunge", "squat"), 3, "10–12/chân", 75)

    def core() -> None:
        if early:
            add(("hand_plank", "plank"), 3, "20–30 giây", 60)
        elif mid:
            add("plank", 3, "30–40 giây", 60)
        else:
            add("plank", 3, "35–45 giây", 60)

    def cardio(minutes: str) -> None:
        add("cardio", 1, minutes, 0, section="cardio")

    cardio_reps = _cardio_line("first_push_pull", week, band)

    if role == "push_legs":
        push_main()
        legs()
        core()
        cardio(cardio_reps)
    elif role == "pull_back":
        pull_main()
        posterior()
        core()
        cardio(cardio_reps)
    else:
        push_main()
        pull_main()
        legs()
        cardio(cardio_reps)
    return items


def _first_push_pull_phase(day: int) -> str:
    week = _week_from_day(day)
    if week <= 2:
        return "Làm quen & form (tường → ghế)"
    if week <= 4:
        return "Ghế thấp / kéo người nằm · chuẩn bị quỳ"
    if week <= 7:
        return "Tích lũy quỳ · treo xà · squat"
    return "Giảm tải và kiểm tra cấp 1"


def _basic_foundation_phase(day: int) -> str:
    if day <= 56:
        return "Tăng tiến tải trọng cấp 2"
    return "Giảm tải và kiểm tra cấp 2"


def _build_60_day_calendar(
    catalog: dict[str, Exercise],
    *,
    gender: str,
    phase_for_day,
    training_exercises,
    can_knee: bool = False,
    bmi_band: str = "normal",
    push_zero: bool = False,
    pull_zero: bool = False,
) -> list[list[PlanDayIn]]:
    ordinal_by_day = {
        day: index for index, day in enumerate(_TRAIN_DAYS_60, start=1)
    }
    templates: list[list[PlanDayIn]] = []
    for week_start in range(1, FIRST_PUSH_PULL_DAYS + 1, 7):
        week = (week_start - 1) // 7 + 1
        week_days: list[PlanDayIn] = []
        for day in range(week_start, min(week_start + 7, FIRST_PUSH_PULL_DAYS + 1)):
            ordinal = ordinal_by_day.get(day)
            if ordinal is None:
                week_days.append(
                    PlanDayIn(
                        day_number=day,
                        title_vi=f"Tuần {week} · Ngày {day} — Nghỉ phục hồi",
                        notes_vi=(
                            "Đi bộ nhẹ 15–20 phút (active recovery), ngủ 7–8 tiếng, "
                            "uống đủ nước. Không tập bù."
                        ),
                        split_role="recovery",
                        exercises=[],
                        meals=[],
                    )
                )
                continue
            session_in_week = ((day - week_start) // 2) + 1
            role = _session_role(ordinal)
            if day == 59:
                session_title = "Kiểm tra đầu ra"
            elif day == 57:
                session_title = "Chuẩn bị trước khi kiểm tra"
            else:
                session_title = (
                    f"Buổi {session_in_week}: {_SESSION_TITLES[role]}"
                )
            week_days.append(
                PlanDayIn(
                    day_number=day,
                    title_vi=f"Tuần {week} · Ngày {day} — {session_title}",
                    notes_vi=(
                        f"{phase_for_day(day)}. Khởi động 5–8 phút. "
                        "Dừng ngay khi đau nhói, chóng mặt hoặc khó thở bất thường."
                    ),
                    split_role=_SESSION_SPLITS[role],
                    exercises=training_exercises(
                        catalog,
                        gender=gender,
                        day=day,
                        ordinal=ordinal,
                        can_knee=can_knee,
                        bmi_band=bmi_band,
                        push_zero=push_zero,
                        pull_zero=pull_zero,
                    ),
                    meals=[],
                )
            )
        templates.append(week_days)
    return templates


def _build_first_push_pull_60_day_templates(
    db: Session,
    *,
    gender: str,
    can_knee: bool = False,
    bmi_band: str = "normal",
    user_slugs: list[str] | None = None,
) -> list[list[PlanDayIn]]:
    return _build_60_day_calendar(
        _first_push_pull_catalog(db, gender, user_slugs=user_slugs),
        gender=gender,
        phase_for_day=_first_push_pull_phase,
        training_exercises=_first_push_pull_training_exercises,
        can_knee=can_knee,
        bmi_band=bmi_band,
    )


def _basic_foundation_training_exercises(
    catalog: dict[str, Exercise],
    *,
    gender: str,
    day: int,
    ordinal: int,
    can_knee: bool = False,
    bmi_band: str = "normal",
    push_zero: bool = False,
    pull_zero: bool = False,
) -> list[PlanExerciseIn]:
    del can_knee
    is_final_test = day == 59
    is_rehearsal = day == 57
    female = gender == "female"
    role = _session_role(ordinal)
    week = _week_from_day(day)
    band = _normalize_bmi_band(bmi_band)
    heavy = is_heavy_bmi(band)
    cardio_reps = _cardio_line("basic_foundation", week, band)
    push_sets = _l2_main_sets(week, peak=3 if female else 4)
    pull_sets = _l2_main_sets(week, peak=3 if female else 4)
    full_sets = _l2_main_sets(week, peak=3)
    pull_keys = ("inverted_row", "elevated_row", "band_pull", "strict_pull")
    if is_final_test:
        phase_note = "Bài kiểm tra cuối: khởi động kỹ, chỉ tính lần/giây đúng form."
    elif is_rehearsal:
        phase_note = "Còn dư 3 cái · tập thử giống kiểm tra nhưng nhẹ hơn 2–3 lần."
    else:
        phase_note = "Còn dư 2 cái · ngực chạm sàn/xà, pha hạ 2 giây."

    items: list[PlanExerciseIn] = []
    add = _make_add(catalog, items, phase_note)
    _warmup(add, role)

    if is_final_test:
        if female:
            add("strict_push", 1, "Mục tiêu 1–6 sàn hoặc 6–12 kê bục 20 cm", 180)
            add(
                ("inverted_row", "band_pull"),
                1,
                "Mục tiêu 4–8 kéo người nằm (bàn/xà) hoặc 2–4 kéo xà dây",
                180,
            )
            add("squat", 1, "Mục tiêu 18–28 lần", 120)
            add("plank", 1, "Mục tiêu 30–60 giây", 120)
            add("cardio", 1, "10 phút · mục tiêu 0,9–1,3 km", 0, section="cardio")
        else:
            add("strict_push", 1, "Mục tiêu 8–15 lần sàn (hoặc ghế nếu cần)", 180)
            add(
                ("strict_pull", "inverted_row"),
                1,
                "Mục tiêu 2–6 kéo xà hoặc kéo người nằm (bàn/xà)",
                180,
            )
            add("squat", 1, "Mục tiêu 20–35 lần", 120)
            add("plank", 1, "Mục tiêu 45–75 giây", 120)
            add("cardio", 1, "10 phút · mục tiêu 1,1–1,5 km", 0, section="cardio")
        return items

    if is_rehearsal:
        if female:
            add("strict_push", 1, "1 sàn hoặc 6–7 kê bục (nhẹ hơn test)", 150)
            add(
                ("inverted_row", "elevated_row"),
                1,
                "3–5 lần kéo dưới bàn/ghế",
                150,
            )
            add("squat", 1, "15–22 lần", 120)
            add("plank", 1, "28–50 giây", 90)
            add("cardio", 1, "10 phút · khoảng 0,8–1,1 km", 0, section="cardio")
        else:
            add("strict_push", 1, "6–12 lần (nhẹ hơn test, sàn hoặc ghế)", 150)
            add(
                ("elevated_row", "inverted_row"),
                1,
                "3–5 lần kéo dưới bàn/ghế (không kéo xà)",
                150,
            )
            add("squat", 1, "18–28 lần", 120)
            add("plank", 1, "40–65 giây", 90)
            add("cardio", 1, "10 phút · khoảng 1,0–1,3 km", 0, section="cardio")
        return items

    if role == "push_legs":
        if female:
            add(("incline_push", "strict_push", "knee_push"), push_sets, "6–10", 90)
        elif push_zero or heavy:
            add(("incline_push", "knee_push", "strict_push"), push_sets, "6–10", 90)
        else:
            add("strict_push", push_sets, "8–12", 90)
        if heavy:
            add(("lunge", "box_squat", "squat"), 3, "8–10/chân", 75)
        else:
            add(("walking_lunge", "lunge", "squat"), 3, "12–15 bước/chân", 75)
        add(("plank", "hollow"), 3, "45–60 giây", 60)
        add("cardio", 1, cardio_reps, 0, section="cardio")
    elif role == "pull_back":
        pull_reps = "6–8" if female or heavy or pull_zero else "4–6"
        add(pull_keys, pull_sets, pull_reps, 120)
        add(("glute_single", "hip_thrust", "glute_bridge"), 3, "10–12/chân", 75)
        add("plank", 3, "45–60 giây", 60)
        add("cardio", 1, cardio_reps, 0, section="cardio")
    else:
        if female:
            if push_zero:
                add(("incline_push", "knee_push", "strict_push"), full_sets, "4–6", 90)
            else:
                add(("strict_push", "incline_push"), full_sets, "4–6", 90)
            add(pull_keys, full_sets, "5–8", 120)
        elif heavy or push_zero:
            add(("incline_push", "knee_push", "strict_push"), full_sets, "6–10", 90)
            add(pull_keys, full_sets, "5–8", 120)
        else:
            add("strict_push", full_sets, "8–12", 90)
            add(pull_keys, full_sets, "4–6", 120)
        if heavy:
            add(("box_squat", "squat"), 3, "10–12", 75)
        else:
            add(("walking_lunge", "squat"), 3, "12–15", 75)
        add("cardio", 1, cardio_reps, 0, section="cardio")
    return items


def _build_basic_foundation_60_day_templates(
    db: Session,
    *,
    gender: str,
    bmi_band: str = "normal",
    user_slugs: list[str] | None = None,
    push_zero: bool = False,
    pull_zero: bool = False,
) -> list[list[PlanDayIn]]:
    return _build_60_day_calendar(
        _first_push_pull_catalog(db, gender, user_slugs=user_slugs),
        gender=gender,
        phase_for_day=_basic_foundation_phase,
        training_exercises=_basic_foundation_training_exercises,
        bmi_band=bmi_band,
        push_zero=push_zero,
        pull_zero=pull_zero,
    )


def _families_for_day(path: str, day_index: int) -> list[str]:
    role = _session_role(day_index + 1)
    if role == "push_legs":
        return ["push", "squat", "plank", "run"]
    if role == "pull_back":
        return ["pull", "plank", "run"]
    return ["push", "pull", "squat", "run"]


def _rep_target(
    family: str,
    step: int,
    delta: int,
    *,
    path: str,
    gender: str,
    week: int,
    at_cap: bool,
) -> str:
    endgame = path == "first_push_pull" and (week >= 7 or at_cap)
    if endgame and family == "push":
        return "3–5"
    if endgame and family == "pull":
        if gender == "female":
            return "30–40 giây"
        return "1–3"
    if family == "pull" and step <= 1:
        seconds = max(8, 15 + delta * 2)
        if path == "first_push_pull" and gender == "female" and week >= 5:
            return "25–35 giây"
        return f"{seconds}–{seconds + 10} giây"
    if family == "pull" and step in {2, 3}:
        seconds = max(3, 6 + delta)
        return f"{seconds}–{seconds + 4} giây"
    if family == "plank":
        seconds = max(15, 25 + delta * 5)
        return f"{seconds}–{seconds + 10} giây"
    if family == "run":
        return "1 phút chạy / 1 phút đi bộ" if step == 0 else "8–12 phút nhịp dễ"
    low = max(2, (4 if family == "pull" else 8) + delta)
    high = low + (2 if family == "pull" else 4)
    return f"{low}–{high}"


def _make_exercise(
    row: Exercise,
    *,
    family: str,
    step: int,
    week: int,
    sort_order: int,
    path: str,
    gender: str,
    at_cap: bool,
) -> PlanExerciseIn:
    sets, delta, rir, _ = _WEEK_LOAD[week]
    section = "cardio" if family == "run" else "main"
    rest = 0 if family == "run" else 150 if family == "pull" else 90
    progression = (
        f"Mức nặng {10 - rir}/10 · còn dư {rir} cái. Khi hoàn thành mọi hiệp đúng kỹ thuật trong 2 buổi liên tiếp, "
        "tăng 1–2 lần hoặc chuyển biến thể kế tiếp. Nếu hụt mức lần tối thiểu "
        "2 buổi, lùi một biến thể và giảm 1 hiệp."
    )
    if week in {4, 8}:
        progression += " Cuối tuần thực hiện bài test khi đã hồi phục; không test sau buổi nặng."
    return PlanExerciseIn(
        exercise_id=int(row.id),
        sets=1 if family == "run" else sets,
        reps=_rep_target(
            family,
            step,
            delta,
            path=path,
            gender=gender,
            week=week,
            at_cap=at_cap,
        ),
        rest_seconds=rest,
        section=section,
        notes_vi=progression,
        sort_order=sort_order,
    )


def build_familiarization_week_templates(
    db: Session, payload: dict[str, Any]
) -> tuple[list[list[PlanDayIn]], dict[str, Any]]:
    path = normalize_familiarization_path(payload.get("familiarization_path"))
    gender = _normalize_gender(payload.get("gender"))
    sessions = max(2, min(5, int(payload.get("sessions_per_week") or 3)))
    base = dict(payload.get("fitness_baseline") or {})
    evaluation = evaluate_fitness_baseline(gender, base)
    band = bmi_band_from_payload(payload)
    user_slugs = _payload_equipment_slugs(payload)
    push_zero = _baseline_capacity_zero(base, "pushups_max")
    pull_zero = _baseline_capacity_zero(base, "pullups_max", "inverted_rows_max")
    if path == "first_push_pull":
        can_knee = gender == "female" and _female_can_knee(base)
        return (
            _build_first_push_pull_60_day_templates(
                db,
                gender=gender,
                can_knee=can_knee,
                bmi_band=band,
                user_slugs=user_slugs,
            ),
            evaluation,
        )
    if path == "basic_foundation":
        return (
            _build_basic_foundation_60_day_templates(
                db,
                gender=gender,
                bmi_band=band,
                user_slugs=user_slugs,
                push_zero=push_zero,
                pull_zero=pull_zero,
            ),
            evaluation,
        )
    families = _catalog_exercises(db)
    caps = _gender_family_caps(path, gender, families)
    starts = _start_steps(path, base, families, gender=gender)

    templates: list[list[PlanDayIn]] = []
    for week in range(1, FAMILIARIZATION_WEEKS + 1):
        _, _, _, phase = _WEEK_LOAD[week]
        if path == "first_push_pull":
            steps = _first_push_pull_week_steps(week, gender, families, caps)
        else:
            steps = {
                key: progression_step_for_week(
                    path,
                    key,
                    value,
                    week,
                    max_step=caps[key],
                )
                for key, value in starts.items()
            }
        days: list[PlanDayIn] = []
        for day_index in range(sessions):
            families_for_day = _families_for_day(path, day_index)
            main_exercises = [
                _make_exercise(
                    _exercise_for(families, family, steps[family]),
                    family=family,
                    step=steps[family],
                    week=week,
                    sort_order=i + 1,
                    path=path,
                    gender=gender,
                    at_cap=steps[family] >= caps[family],
                )
                for i, family in enumerate(families_for_day, start=1)
            ]
            primer_family = (
                "push" if "push" in families_for_day else families_for_day[0]
            )
            primer_row = _exercise_for(
                families, primer_family, max(0, steps[primer_family] - 1)
            )
            exercises = [
                PlanExerciseIn(
                    exercise_id=int(primer_row.id),
                    sets=1,
                    reps="5–8 nhịp chậm",
                    rest_seconds=45,
                    section="warmup",
                    notes_vi="Khởi động đúng mẫu chuyển động, RPE 3–4; không tập tới mỏi.",
                    sort_order=1,
                ),
                *main_exercises,
            ]
            days.append(
                PlanDayIn(
                    day_number=day_index + 1,
                    title_vi=_day_title(
                        week=week,
                        day_index=day_index,
                        phase=phase,
                        weekdays=[],
                        start_time="",
                    ),
                    notes_vi=(
                        "Khởi động 5–8 phút. Không tập xuyên đau nhói; giữ kỹ thuật và "
                        "mức dự trữ ghi trong từng bài."
                    ),
                    split_role="Full Body",
                    exercises=exercises,
                    meals=[],
                )
            )
        templates.append(days)
    return templates, evaluation


def expand_familiarization_weeks(
    week_templates: list[list[PlanDayIn]],
) -> list[PlanDayIn]:
    expanded: list[PlanDayIn] = []
    for week in week_templates:
        for source in week:
            day = source.model_copy(deep=True)
            day.day_number = len(expanded) + 1
            expanded.append(day)
    return expanded


def _fold_familiarization_weeks(days: list[PlanDayIn]) -> list[list[PlanDayIn]]:
    weeks: list[list[PlanDayIn]] = []
    for index in range(0, len(days), 7):
        weeks.append(days[index : index + 7])
    return weeks


def _apply_rest_day_meals(days: list[PlanDayIn], meal_result) -> list[PlanDayIn]:
    rest = getattr(meal_result, "rest_day_template", None)
    schedule = getattr(meal_result, "schedule", None)
    if rest is None:
        return days
    rest_targets = getattr(schedule, "rest", None) if schedule is not None else None
    out: list[PlanDayIn] = []
    for day in days:
        if (day.split_role or "").lower() != "recovery":
            out.append(day)
            continue
        updates: dict[str, Any] = {
            "meals": [item.model_copy() for item in rest.meals],
            "meal_notes": dict(rest.meal_notes),
        }
        if rest_targets is not None:
            updates.update(
                {
                    "target_calories": rest_targets.target_calories,
                    "target_protein_g": rest_targets.protein_g,
                    "target_carbs_g": rest_targets.carbs_g,
                    "target_fat_g": rest_targets.fat_g,
                }
            )
        out.append(day.model_copy(update=updates))
    return out


def _attach_familiarization_meals(
    db: Session,
    payload: dict[str, Any],
    templates: list[list[PlanDayIn]],
    weight_goal: dict[str, Any] | None,
):
    food_ids = [int(fid) for fid in (payload.get("food_ids") or []) if str(fid).strip()]
    if not food_ids:
        return templates, None
    goal = str((weight_goal or {}).get("goal") or goal_from_bmi_band(bmi_band_from_payload(payload)))
    meal_payload = {
        **payload,
        "goal": goal,
        "ai_suggest_foods": False,
        "food_ids": food_ids,
        "kg_per_week": (weight_goal or {}).get("kg_per_week") or payload.get("kg_per_week"),
    }
    targets = estimate_targets(meal_payload)
    expanded = expand_familiarization_weeks(templates)
    meal_result = generate_meals(
        db,
        meal_payload,
        targets,
        plan_days=expanded,
        goal=goal,
    )
    if meal_result.schedule and meal_result.templates_by_kind:
        expanded = apply_meals_with_schedule(
            expanded,
            meal_result.schedule,
            meal_result.templates_by_kind,
            foods_by_id=meal_result.foods_by_id,
        )
        expanded = _apply_rest_day_meals(expanded, meal_result)
    elif meal_result.templates:
        expanded = apply_meals_to_days(expanded, meal_result.templates)
    return _fold_familiarization_weeks(expanded), meal_result


def generate_familiarization_workout(
    db: Session,
    user_id: str | None,
    payload: dict[str, Any],
    *,
    persist: bool = True,
) -> dict[str, Any]:
    path = normalize_familiarization_path(payload.get("familiarization_path"))
    gender = _normalize_gender(payload.get("gender"))
    templates, evaluation = build_familiarization_week_templates(db, payload)
    weight_goal = build_familiarization_weight_goal(payload)
    templates, meal_result = _attach_familiarization_meals(
        db, payload, templates, weight_goal
    )
    first_week = templates[0]
    sessions = FIRST_PUSH_PULL_SESSIONS_PER_WEEK
    copy = familiarization_overview_copy(path, gender)
    if weight_goal and weight_goal.get("copy_vi"):
        note = str(weight_goal["copy_vi"])
        for week in templates:
            for day in week:
                if int(day.day_number or 0) == FIRST_PUSH_PULL_DAYS:
                    base_note = (day.notes_vi or "").rstrip()
                    day.notes_vi = f"{base_note}\n\n{note}" if base_note else note
    nutrition_vi = copy["nutrition_vi"]
    if weight_goal and weight_goal.get("copy_vi"):
        nutrition_vi = f"{weight_goal['copy_vi']} {nutrition_vi}"
    minutes = 45
    label = copy["label_vi"]
    stamp = datetime.now().strftime("%d/%m/%Y %H:%M")
    duration_label = "60 ngày"
    description = copy["summary_vi"]
    weekday_labels = []
    insights = {
        "overview": {
            "schedule_vi": copy["schedule_vi"],
            "summary_vi": copy["summary_vi"],
            "periodization_vi": copy["periodization_vi"],
            "nutrition_vi": nutrition_vi,
            "mission_vi": copy["mission_vi"],
            "outcome_vi": copy["outcome_vi"],
        },
        "advice_vi": [
            "Đau nhói, chóng mặt hoặc khó thở bất thường: dừng tập và đánh giá y tế.",
            (
                "Dụng cụ nhà: tường, ghế/bàn chắc, balo sách, xà cửa. "
                "Tuần 3 bắt đầu kéo người nằm (bàn/xà); tuần 5 treo xà siết bả vai. "
                "Kiểm tra bàn không bị bênh trước khi kéo dưới gầm."
                if path == "first_push_pull"
                else "Dụng cụ: thể trọng, xà đơn, ghế, balo. Nữ cấp 2–3 có thể kéo xà trợ lực dây band nếu có."
            ),
            "Mốc ngày 59 là mục tiêu kiểm tra, không phải cam kết mọi người đều đạt đúng hạn.",
        ],
        "days": [],
        "nutrition": (
            {
                "tdee": weight_goal.get("tdee"),
                "target_calories": weight_goal.get("daily_kcal"),
                "protein_g": weight_goal.get("protein_g"),
                "goal_vi": {
                    "lose_weight": "giảm cân",
                    "maintain": "giữ cân",
                    "gain_weight": "tăng cân",
                }.get(str(weight_goal.get("goal") or ""), str(weight_goal.get("goal") or "")),
            }
            if weight_goal
            else None
        ),
        "generator": "familiarization_rules_v1",
        "used_openai": False,
        "used_openai_pick": False,
        "challenge_100_days": False,
        "generation_mode": "familiarization",
        "familiarization_path": path,
        "duration_days": FIRST_PUSH_PULL_DAYS,
        "sessions_per_week": sessions,
        "fitness_evaluation": evaluation,
        "weight_goal": weight_goal,
        "familiarization_catalog": familiarization_catalog(),
        "familiarization_week_templates": [
            [day.model_dump() for day in week] for week in templates
        ],
        "session_minutes": minutes,
    }
    if meal_result is not None:
        if meal_result.warning_vi:
            insights["meal_warning_vi"] = meal_result.warning_vi
        if meal_result.rest_day_template and meal_result.schedule:
            rest = meal_result.schedule.rest
            insights["rest_day_nutrition"] = {
                "target_calories": rest.target_calories,
                "protein_g": rest.protein_g,
                "carbs_g": rest.carbs_g,
                "fat_g": rest.fat_g,
            }
            insights["rest_day_meals"] = [
                {
                    "food_id": item.food_id,
                    "meal_type": item.meal_type,
                    "servings": item.servings,
                    "notes_vi": item.notes_vi,
                }
                for item in meal_result.rest_day_template.meals
            ]
    duration_weeks = FIRST_PUSH_PULL_WEEKS
    start_date = datetime.now(UTC).date()
    if path == "basic_foundation":
        strength_tier = "ok"
    else:
        strength_tier = (
            "weak" if evaluation["level"] in {"zero", "below_basic"} else "ok"
        )
    create = CreatePlanRequest(
        title_vi=f"{label} {stamp}",
        description_vi=description,
        start_date=start_date,
        end_date=start_date + timedelta(days=FIRST_PUSH_PULL_DAYS - 1),
        source="ai",
        duration_weeks=duration_weeks,
        experience_level=min(max(int(payload.get("experience_level") or 1), 1), 3),
        strength_tier=strength_tier,
        challenge_100_days=False,
        days=first_week,
    )
    settings = get_settings()
    usage = {
        "month": "",
        "generation_count": 0,
        "qa_message_count": 0,
        "limit": None,
        "remaining": None,
        "unlimited": True,
        "price_vnd": 0,
        "model": settings.openai_model,
        "openai_configured": bool((settings.openai_api_key or "").strip()),
    }
    if not persist:
        return {
            "plan": None,
            "plan_id": None,
            "share_token": None,
            "share_url_path": None,
            "days": [
                day.model_dump()
                for day in expand_familiarization_weeks(templates)
            ],
            "sessions_requested": int(payload.get("sessions_per_week") or 3),
            "sessions_actual": sessions,
            "session_minutes": minutes,
            "insights": insights,
            "usage": usage,
        }
    detail = PlanService(db).create_plan(user_id, create, insights_json=insights)
    token = detail.get("share_token")
    return {
        "plan": detail,
        "plan_id": detail.get("id"),
        "share_token": token,
        "share_url_path": f"/lich/{token}" if token else None,
        "usage": usage,
    }
