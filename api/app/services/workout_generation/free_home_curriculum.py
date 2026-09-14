"""Fixed 8-week home bodyweight curriculum for “từ con số 0”."""

from __future__ import annotations

import hashlib
import re
from typing import Any

from app.schemas.plans import PlanDayIn, PlanExerciseIn
from app.services.workout_generation.muscle_quotas import (
    CHEST_SLUGS,
    CORE_SLUGS,
    GLUTE_SLUGS,
    QUAD_SLUGS,
    SHOULDER_SLUGS,
)
from app.services.workout_generation.split_map import mobility_match_rank
from app.services.workout_rest import home_interval_cardio_prescription

FOUNDATION_MOTIVES = frozenset({"daily_energy", "build_habit", "body_confidence"})
DEFAULT_MOTIVE = "build_habit"
FREE_HOME_WEEKS = 8
EASE_NOTE_VI = (
    "Tuần này nhẹ hơn có chủ đích — giữ form, đừng nghĩ mình tụt tiến bộ."
)
PERIODIZATION_VI = (
    "Tháng đầu mình không ép bạn “tập cho oách” — bắt đúng sức nền, dù chỉ vài lần một hiệp. "
    "Tuần 4 nhẹ hơn có chủ đích để bạn kịp theo. "
    "Tháng hai cùng khung lịch nhưng dày hơn một chút; tuần 8 lại nhẹ rồi nhìn lại mình đã đi được bao xa. "
    "Cứ xuất hiện đủ buổi là đang thắng."
)
PLAN_TITLE_STEM_VI = "Lịch tập cải thiện thể lực"

_CARDIO_NAME_NEEDLES = (
    "đi bộ",
    "di bo",
    "march",
    "walk",
    "cardio",
    "nhảy dây",
    "nhay day",
    "jogging",
    "chạy tại chỗ",
    "chay tai cho",
)
_CORE_NAME_NEEDLES = (
    "plank",
    "bird-dog",
    "bird dog",
    "dead bug",
    "superman",
    "crunch",
    "sit-up",
    "sit up",
    "core",
    "bụng",
    "bung",
    "hollow",
)
_EASY_CARDIO_PREFER = (
    "march",
    "đi bộ",
    "di bo",
    "walk",
    "step",
    "tại chỗ",
    "tai cho",
)
_STABILITY_CORE_PREFER = (
    "bird-dog",
    "bird dog",
    "dead bug",
    "plank gối",
    "plank goi",
    "knee plank",
    "superman",
)
_POSTURE_PREFER = (
    "y-t-w",
    "ytw",
    "y t w",
    "glute",
    "cầu mông",
    "cau mong",
    "squat",
    "push",
    "chống đẩy",
    "chong day",
)

_MOTIVE_FOCUS: dict[str, frozenset[str]] = {
    "daily_energy": CORE_SLUGS,
    "build_habit": frozenset(),
    "body_confidence": CHEST_SLUGS | GLUTE_SLUGS | QUAD_SLUGS | SHOULDER_SLUGS,
}

NUTRITION_TEMPLATES: dict[str, tuple[str, ...]] = {
    "daily_energy": (
        "Uống đủ nước, ăn đủ 3 bữa (cơm + rau + đạm). Đừng bỏ bữa; trước tập 30–60 phút có thể ăn nhẹ chuối hoặc bánh mì.",
        "Giữ giờ ăn ổn định. Ưu tiên cơm/khoai, thịt/cá/trứng và rau mỗi bữa. Hạn chế đồ ngọt lúc đói — dễ mệt giữa ngày.",
        "Ngày tập: ăn đủ tinh bột. Ngày nghỉ vẫn ăn rau và đạm. Không cắt calo gắt khi mới bắt đầu vận động.",
    ),
    "build_habit": (
        "Ăn đúng giờ mỗi ngày. Mỗi bữa có đạm (trứng, thịt, cá, đậu) và không cắt carbo ngày tập — cần năng lượng để tập đều.",
        "Giữ 3 bữa chính. Thêm một bữa phụ nhỏ nếu đói trước tập. Ưu tiên đồ nhà làm, hạn chế bỏ bữa vì “bận”.",
        "Đạm mỗi bữa, rau mỗi đĩa, cơm vừa phải. Thói quen ăn đều quan trọng hơn ăn kiêng những tuần đầu.",
    ),
    "body_confidence": (
        "Đạm + rau đủ nửa đĩa, hạn chế nước ngọt. Không ăn kiêng gắt giai đoạn này — cơ thể cần năng lượng để tập và phục hồi.",
        "Ăn no vừa phải, không nhịn. Ưu tiên thịt/cá/trứng, rau và cơm. Bỏ dần snack ngọt, không cần thực đơn khắc nghiệt.",
        "Tập trung ăn đủ, ngủ đủ. Đạm mỗi bữa, hạn chế đồ uống có đường. Vóc dáng sẽ theo sau khi nền thể lực lên.",
    ),
}
NUTRITION_ADVICE: dict[str, tuple[str, ...]] = {
    "daily_energy": (
        "Uống nước đều trong ngày, đừng đợi khát.",
        "Không tập lúc đói quá lâu — ăn nhẹ trước buổi tập nếu cần.",
        "Ngủ đủ 7 tiếng giúp bớt mệt hơn là cắt ăn.",
    ),
    "build_habit": (
        "Ăn đúng giờ còn quan trọng hơn ăn “sạch” tuyệt đối.",
        "Ngày tập cứ ăn cơm bình thường, đừng cắt tinh bột.",
        "Nếu lỡ một bữa, bữa sau ăn đủ — đừng nhịn bù.",
    ),
    "body_confidence": (
        "Không ăn kiêng gắt song song lịch mới — dễ bỏ tập.",
        "Hạn chế nước ngọt; nước lọc và trái cây đủ cho giai đoạn này.",
        "Đạm mỗi bữa giúp phục hồi và giữ form khi mới tập.",
    ),
}


def normalize_foundation_motive(raw: Any) -> str:
    key = str(raw or "").strip().lower()
    return key if key in FOUNDATION_MOTIVES else DEFAULT_MOTIVE


def motive_focus_slugs(motive: str) -> frozenset[str]:
    return _MOTIVE_FOCUS.get(normalize_foundation_motive(motive), frozenset())


def periodization_vi() -> str:
    return PERIODIZATION_VI


def plan_title_vi(stamp: str) -> str:
    return f"{PLAN_TITLE_STEM_VI} {stamp}"


def free_home_session_dose(session_minutes: int) -> dict[str, int]:
    """Warmup / main / cooldown sets-rest for the chosen session length."""
    from app.services.schedule_spec_master import snap_session_minutes

    minutes = snap_session_minutes(int(session_minutes or 45))
    if minutes <= 30:
        return {
            "stretch_sets": 1,
            "primer_sets": 1,
            "cooldown_sets": 1,
            "main_sets": 2,
            "main_rest": 45,
        }
    if minutes <= 45:
        return {
            "stretch_sets": 1,
            "primer_sets": 1,
            "cooldown_sets": 2,
            "main_sets": 2,
            "main_rest": 45,
        }
    if minutes <= 60:
        return {
            "stretch_sets": 1,
            "primer_sets": 2,
            "cooldown_sets": 2,
            "main_sets": 3,
            "main_rest": 60,
        }
    if minutes <= 75:
        return {
            "stretch_sets": 2,
            "primer_sets": 2,
            "cooldown_sets": 2,
            "main_sets": 3,
            "main_rest": 60,
        }
    return {
        "stretch_sets": 2,
        "primer_sets": 2,
        "cooldown_sets": 2,
        "main_sets": 3,
        "main_rest": 90,
    }


def pick_nutrition_copy(motive: str, *, seed: str | None = None) -> tuple[str, list[str]]:
    key = normalize_foundation_motive(motive)
    templates = NUTRITION_TEMPLATES[key]
    digest = hashlib.sha1(f"{seed or ''}:{key}".encode("utf-8")).hexdigest()
    idx = int(digest[:8], 16) % len(templates)
    return templates[idx], list(NUTRITION_ADVICE[key])


def _item_id(item: object) -> int | None:
    try:
        if isinstance(item, dict):
            return int(item.get("id") or 0) or None
        return int(getattr(item, "id", 0) or 0) or None
    except (TypeError, ValueError):
        return None


def _item_name(item: object) -> str:
    if isinstance(item, dict):
        return str(item.get("name_vi") or item.get("name_en") or "").lower()
    return str(getattr(item, "name_vi", None) or getattr(item, "name_en", None) or "").lower()


def _item_muscle(item: object) -> str:
    if isinstance(item, dict):
        return str(item.get("muscle_slug") or item.get("muscle") or "").strip().lower()
    return str(
        getattr(item, "muscle_slug", None) or getattr(item, "muscle", None) or ""
    ).strip().lower()


def _meta_name(meta: dict[str, Any] | None) -> str:
    if not meta:
        return ""
    return str(meta.get("name_vi") or meta.get("name_en") or "").lower()


def _meta_muscle(meta: dict[str, Any] | None) -> str:
    if not meta:
        return ""
    return str(meta.get("muscle_slug") or meta.get("muscle") or "").strip().lower()


def _name_hits(name: str, needles: tuple[str, ...]) -> bool:
    text = str(name or "").lower()
    return any(n in text for n in needles)


def is_cardio_exercise(ex: PlanExerciseIn, meta: dict[str, Any] | None) -> bool:
    if str(getattr(ex, "section", "") or "") == "cardio":
        return True
    role = str((meta or {}).get("movement_role") or "").lower()
    if role in {"cardio", "conditioning"}:
        return True
    return _name_hits(_meta_name(meta), _CARDIO_NAME_NEEDLES)


def is_core_exercise(ex: PlanExerciseIn, meta: dict[str, Any] | None) -> bool:
    slug = _meta_muscle(meta)
    if slug in CORE_SLUGS:
        return True
    role = str((meta or {}).get("movement_role") or "").lower()
    if role == "core":
        return True
    return _name_hits(_meta_name(meta), _CORE_NAME_NEEDLES)


def day_has_cardio_or_core(day: PlanDayIn, meta_by_id: dict[int, dict[str, Any]]) -> bool:
    for ex in day.exercises or []:
        meta = meta_by_id.get(int(ex.exercise_id)) or {}
        if is_cardio_exercise(ex, meta) or is_core_exercise(ex, meta):
            return True
    return False


def _prefer_needles(motive: str, want_cardio: bool) -> tuple[str, ...]:
    key = normalize_foundation_motive(motive)
    if want_cardio:
        if key == "daily_energy":
            return _EASY_CARDIO_PREFER
        return _CARDIO_NAME_NEEDLES
    if key == "daily_energy":
        return _STABILITY_CORE_PREFER
    if key == "body_confidence":
        return _POSTURE_PREFER + _CORE_NAME_NEEDLES
    return _CORE_NAME_NEEDLES


def _rank_finisher(item: object, *, motive: str, want_cardio: bool) -> tuple[int, int, int]:
    name = _item_name(item)
    slug = _item_muscle(item)
    needles = _prefer_needles(motive, want_cardio)
    prefer_hit = 0 if _name_hits(name, needles) else 1
    if want_cardio:
        kind_hit = 0 if _name_hits(name, _CARDIO_NAME_NEEDLES) else 1
    else:
        kind_hit = 0 if (slug in CORE_SLUGS or _name_hits(name, _CORE_NAME_NEEDLES)) else 1
    eid = _item_id(item) or 0
    return (kind_hit, prefer_hit, eid)


def _used_ids(day: PlanDayIn) -> set[int]:
    out: set[int] = set()
    for ex in day.exercises or []:
        try:
            out.add(int(ex.exercise_id))
        except (TypeError, ValueError):
            continue
    return out


def _make_finisher(
    item: object,
    *,
    want_cardio: bool,
    session_minutes: int | None = None,
    experience_level: int | None = 1,
) -> PlanExerciseIn | None:
    eid = _item_id(item)
    if not eid:
        return None
    if want_cardio:
        from app.services.schedule_spec_master import home_session_spec, snap_session_minutes

        minutes = snap_session_minutes(int(session_minutes or 45))
        budget = int(home_session_spec(minutes).get("conditioningMinutes") or 5)
        sets, reps, rest, notes = home_interval_cardio_prescription(
            budget, experience_level=experience_level
        )
        return PlanExerciseIn(
            exercise_id=eid,
            sets=sets,
            reps=reps,
            rest_seconds=rest,
            section="cardio",
            notes_vi=notes,
            sort_order=90,
        )
    return PlanExerciseIn(
        exercise_id=eid,
        sets=2,
        reps="8–12",
        rest_seconds=45,
        section="main",
        notes_vi="Core ổn định — giữ form, đừng nín thở.",
        sort_order=80,
    )


def _pool_from_shortlists(shortlists: dict[str, list] | None, keys: tuple[str, ...]) -> list:
    pool: list = []
    seen: set[int] = set()
    for key in keys:
        for item in (shortlists or {}).get(key) or []:
            eid = _item_id(item)
            if not eid or eid in seen:
                continue
            seen.add(eid)
            pool.append(item)
    return pool


def ensure_cardio_or_core(
    plan_days: list[PlanDayIn],
    *,
    day_contexts: list[dict[str, Any]],
    meta_by_id: dict[int, dict[str, Any]],
    motive: str,
    session_minutes: int | None = None,
) -> list[PlanDayIn]:
    """Each session gets at least one easy cardio or core drill."""
    ctx_by_index = {
        int(ctx["frame_day"].day_index): ctx for ctx in day_contexts if ctx.get("frame_day")
    }
    want_cardio_default = normalize_foundation_motive(motive) == "daily_energy"
    for day in plan_days:
        if day_has_cardio_or_core(day, meta_by_id):
            continue
        idx = max(0, int(day.day_number or 1) - 1)
        ctx = ctx_by_index.get(idx) or {}
        shortlists = ctx.get("shortlists") or {}
        used = _used_ids(day)
        want_cardio = want_cardio_default
        keys = ("cardio", "conditioning") if want_cardio else ("core", "conditioning")
        pool = [x for x in _pool_from_shortlists(shortlists, keys) if (_item_id(x) or 0) not in used]
        if not pool:
            want_cardio = not want_cardio
            keys = ("cardio", "conditioning") if want_cardio else ("core", "conditioning")
            pool = [
                x for x in _pool_from_shortlists(shortlists, keys) if (_item_id(x) or 0) not in used
            ]
        if not pool:
            pool = [
                x
                for x in _pool_from_shortlists(shortlists, ("resistance", "compound"))
                if (_item_id(x) or 0) not in used
                and (
                    _item_muscle(x) in CORE_SLUGS
                    or _name_hits(_item_name(x), _CORE_NAME_NEEDLES + _CARDIO_NAME_NEEDLES)
                )
            ]
            want_cardio = False
        if not pool:
            continue
        ranked = sorted(pool, key=lambda x: _rank_finisher(x, motive=motive, want_cardio=want_cardio))
        chosen = ranked[0]
        finisher = _make_finisher(
            chosen,
            want_cardio=want_cardio,
            session_minutes=session_minutes,
        )
        if not finisher:
            continue
        eid = int(finisher.exercise_id)
        if isinstance(chosen, dict):
            meta_by_id.setdefault(eid, {}).update(
                {
                    "name_vi": chosen.get("name_vi"),
                    "name_en": chosen.get("name_en"),
                    "muscle_slug": chosen.get("muscle_slug") or chosen.get("muscle"),
                    "movement_role": chosen.get("movement_role"),
                }
            )
        else:
            meta_by_id.setdefault(eid, {}).update(
                {
                    "name_vi": getattr(chosen, "name_vi", None),
                    "name_en": getattr(chosen, "name_en", None),
                    "muscle_slug": getattr(chosen, "muscle_slug", None),
                    "movement_role": getattr(chosen, "movement_role", None),
                }
            )
        day.exercises = list(day.exercises or []) + [finisher]
        for i, ex in enumerate(day.exercises, start=1):
            ex.sort_order = i
    return plan_days


def _trained_slugs_for_day(day: PlanDayIn, meta_by_id: dict[int, dict[str, Any]]) -> frozenset[str]:
    slugs: set[str] = set()
    for ex in day.exercises or []:
        section = str(getattr(ex, "section", "") or "main")
        if section in {"warmup", "cooldown"}:
            continue
        slug = _meta_muscle(meta_by_id.get(int(ex.exercise_id)))
        if slug:
            slugs.add(slug)
    return frozenset(slugs)


def rematch_cooldown_to_trained(
    plan_days: list[PlanDayIn],
    *,
    day_contexts: list[dict[str, Any]],
    meta_by_id: dict[int, dict[str, Any]],
) -> list[PlanDayIn]:
    ctx_by_index = {
        int(ctx["frame_day"].day_index): ctx for ctx in day_contexts if ctx.get("frame_day")
    }
    for day in plan_days:
        trained = _trained_slugs_for_day(day, meta_by_id)
        if not trained:
            continue
        idx = max(0, int(day.day_number or 1) - 1)
        pool = list((ctx_by_index.get(idx) or {}).get("shortlists", {}).get("cooldown") or [])
        if not pool:
            continue
        used = _used_ids(day)
        cooldown_exs = [
            ex for ex in (day.exercises or []) if str(getattr(ex, "section", "") or "") == "cooldown"
        ]
        if not cooldown_exs:
            continue
        ranked = sorted(
            pool,
            key=lambda x: (
                mobility_match_rank(
                    muscle_slug=_item_muscle(x),
                    name_vi=_item_name(x),
                    split_role=day.split_role,
                    cooldown=True,
                    trained_slugs=trained,
                ),
                _item_id(x) or 0,
            ),
        )
        replacements: list[int] = []
        taken = set(used)
        for item in ranked:
            eid = _item_id(item)
            if not eid or eid in taken:
                continue
            replacements.append(eid)
            taken.add(eid)
            if isinstance(item, dict):
                meta_by_id.setdefault(eid, {}).update(
                    {
                        "name_vi": item.get("name_vi"),
                        "muscle_slug": item.get("muscle_slug") or item.get("muscle"),
                    }
                )
            else:
                meta_by_id.setdefault(eid, {}).update(
                    {
                        "name_vi": getattr(item, "name_vi", None),
                        "muscle_slug": getattr(item, "muscle_slug", None),
                    }
                )
            if len(replacements) >= len(cooldown_exs):
                break
        if not replacements:
            continue
        ri = 0
        new_ex: list[PlanExerciseIn] = []
        for ex in day.exercises or []:
            if str(getattr(ex, "section", "") or "") != "cooldown" or ri >= len(replacements):
                new_ex.append(ex)
                continue
            swapped = ex.model_copy(deep=True)
            swapped.exercise_id = replacements[ri]
            ri += 1
            new_ex.append(swapped)
        day.exercises = new_ex
        for i, ex in enumerate(day.exercises, start=1):
            ex.sort_order = i
    return plan_days


def _parse_int(raw: Any, default: int) -> int:
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def _nudge_reps(reps: Any, delta: int) -> Any:
    if isinstance(reps, int):
        return max(1, reps + delta)
    text = str(reps or "").strip()
    if not text:
        return reps

    def _bump_num(match: re.Match[str]) -> str:
        return str(max(1, int(match.group(0)) + delta))

    if re.search(r"\d+", text):
        return re.sub(r"\d+", _bump_num, text, count=2)
    return reps


def scale_exercise_for_week(ex: PlanExerciseIn, week: int) -> PlanExerciseIn:
    """8-week foundation: W1 familiarize … W4/W8 deload; W5–7 build then peak."""
    out = ex.model_copy(deep=True)
    section = str(getattr(ex, "section", "main") or "main")
    if section not in {"main", "exercises", "cardio"}:
        return out
    sets = max(1, _parse_int(out.sets, 3))
    rest = max(0, _parse_int(out.rest_seconds, 90))
    w = max(1, int(week or 1))

    if w <= 1:
        # Phase 1 — làm quen
        if sets >= 3:
            out.sets = sets - 1
        out.rest_seconds = min(180, int(round(rest * 1.15)))
    elif w == 2:
        pass  # baseline
    elif w == 3:
        if sets < 4:
            out.sets = sets + 1
        else:
            out.reps = _nudge_reps(out.reps, 2)
    elif w == 4:
        out.sets = max(1, int(round(sets * 0.7)))
        out.rest_seconds = min(180, int(round(rest * 1.2)))
        if section in {"main", "exercises"}:
            out.notes_vi = EASE_NOTE_VI
    elif w == 5:
        # Phase 2 — mở lại sau deload, hơi trên baseline
        if sets < 4:
            out.sets = sets + 1
    elif w == 6:
        if sets < 4:
            out.sets = sets + 1
        else:
            out.sets = min(5, sets + 1)
        out.rest_seconds = max(60, int(round(rest * 0.95)))
    elif w == 7:
        # Peak nhẹ
        bump = 2 if sets < 4 else 1
        out.sets = min(5, sets + bump)
        out.reps = _nudge_reps(out.reps, 2)
        out.rest_seconds = max(60, int(round(rest * 0.9)))
    else:
        # Week 8+ deload
        out.sets = max(1, int(round(sets * 0.7)))
        out.rest_seconds = min(180, int(round(rest * 1.2)))
        if section in {"main", "exercises"}:
            out.notes_vi = EASE_NOTE_VI
    return out


def _foundation_week_tag(week: int) -> str:
    phase = 1 if week <= 4 else 2
    ease = week in {4, 8}
    tag = f"Tuần {week} · Giai đoạn {phase}"
    if ease:
        tag += " — Nhẹ hơn"
    return tag


def expand_free_home_weeks(days: list[PlanDayIn], duration_weeks: int = FREE_HOME_WEEKS) -> list[PlanDayIn]:
    weeks = max(1, min(FREE_HOME_WEEKS, int(duration_weeks or FREE_HOME_WEEKS)))
    if weeks <= 1 or not days:
        return days
    sessions = len(days)
    expanded: list[PlanDayIn] = []
    title_prefix = re.compile(
        r"^(Tháng\s+\d+\s*·\s*|Pha\s+\d+\s*·\s*|Giai đoạn\s+\d+\s*·\s*)?"
        r"Tuần\s+\d+(?:\s*·\s*Giai đoạn\s+\d+)?(?:\s*—\s*[^:：]+)?\s*[:：]\s*",
        re.I,
    )
    for week in range(1, weeks + 1):
        tag = _foundation_week_tag(week)
        for src in days:
            day = src.model_copy(deep=True)
            base_num = day.day_number
            day.day_number = (week - 1) * sessions + base_num
            title = title_prefix.sub("", str(day.title_vi or f"Ngày {base_num}"))
            day.title_vi = f"{tag}: {title}"
            day.exercises = [scale_exercise_for_week(ex, week) for ex in (day.exercises or [])]
            expanded.append(day)
    return expanded


def apply_free_home_session_timing(
    plan_days: list[PlanDayIn],
    *,
    session_minutes: int,
    experience_level: int | None = 1,
    meta_by_id: dict[int, dict[str, Any]] | None = None,
) -> list[PlanDayIn]:
    """Fit warmup / main / cardio / cooldown sets-rest to the chosen session length."""
    from app.services.workout_generation.session_duration import parse_reps_minutes

    dose = free_home_session_dose(session_minutes)
    meta_by_id = meta_by_id or {}
    for day in plan_days:
        exercises = list(day.exercises or [])
        mains = [
            ex for ex in exercises if str(getattr(ex, "section", None) or "main") == "main"
        ]
        first_main_id = int(mains[0].exercise_id) if mains else None
        for ex in exercises:
            section = str(getattr(ex, "section", None) or "main")
            if section == "warmup":
                if first_main_id is not None and int(ex.exercise_id) == first_main_id:
                    ex.sets = int(dose["primer_sets"])
                else:
                    ex.sets = int(dose["stretch_sets"])
                continue
            if section == "cooldown":
                ex.sets = int(dose["cooldown_sets"])
                continue
            if section == "cardio":
                minutes = parse_reps_minutes(ex.reps)
                if minutes is not None:
                    sets, reps, rest, notes = home_interval_cardio_prescription(
                        minutes, experience_level=experience_level
                    )
                    ex.sets = sets
                    ex.reps = reps
                    ex.rest_seconds = rest
                    if notes:
                        ex.notes_vi = notes
                continue
            # Main volume is seeded in assemble then owned by fill/clamp.
        for i, ex in enumerate(exercises, start=1):
            ex.sort_order = i
        day.exercises = exercises
    return plan_days


def apply_free_home_finishes(
    plan_days: list[PlanDayIn],
    *,
    day_contexts: list[dict[str, Any]],
    meta_by_id: dict[int, dict[str, Any]],
    motive: str,
    session_minutes: int | None = None,
    experience_level: int | None = 1,
) -> list[PlanDayIn]:
    ensure_cardio_or_core(
        plan_days,
        day_contexts=day_contexts,
        meta_by_id=meta_by_id,
        motive=motive,
        session_minutes=session_minutes,
    )
    rematch_cooldown_to_trained(
        plan_days,
        day_contexts=day_contexts,
        meta_by_id=meta_by_id,
    )
    apply_free_home_session_timing(
        plan_days,
        session_minutes=int(session_minutes or 45),
        experience_level=experience_level,
        meta_by_id=meta_by_id,
    )
    return plan_days
