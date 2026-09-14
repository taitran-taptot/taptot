"""Compact plan/profile payloads for the Q&A agent (token-cheap, no media/instructions)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from types import SimpleNamespace
from typing import Any

from sqlalchemy.orm import Session

from app.models.entities import (
    Exercise,
    Food,
    MuscleGroup,
    User,
    UserDailyPlan,
    UserDailyPlanDay,
    UserDailyPlanExercise,
    UserDailyPlanMeal,
    UserProfile,
)
from app.services.plan_notes import unpack_day_notes
from app.services.workout_generation.weekly_volume import (
    count_weekly_sets,
    volume_family,
    weekly_budget,
)

HEAVY_KEYS = frozenset(
    {
        "gif_url",
        "image_url",
        "video_url",
        "instruction_steps_vi",
        "instruction_steps_en",
        "instruction_en",
        "content_md",
        "seo_title",
        "seo_description",
        "description_vi",
    }
)

EXPERIENCE_TO_LEVEL = {"beginner": 2, "intermediate": 3, "advanced": 3}

GOAL_VI = {
    "lose_weight": "Giảm cân",
    "maintain": "Giữ cân",
    "gain_weight": "Tăng cân",
    "gain_muscle": "Tăng cơ",
}

WEEKDAY_VI = (
    "Thứ hai",
    "Thứ ba",
    "Thứ tư",
    "Thứ năm",
    "Thứ sáu",
    "Thứ bảy",
    "Chủ nhật",
)

PRIMARY_FAMS = ("chest", "back", "quads", "hinge")


def clip_text(value: Any, limit: int = 400) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)] + "…"


def drop_heavy_fields(obj: Any) -> Any:
    """Strip media/instruction blobs from nested dict/list payloads."""
    if isinstance(obj, dict):
        return {
            key: drop_heavy_fields(val)
            for key, val in obj.items()
            if key not in HEAVY_KEYS and val is not None
        }
    if isinstance(obj, list):
        return [drop_heavy_fields(item) for item in obj]
    return obj


def week_day_range(
    day_numbers: list[int],
    *,
    sessions_per_week: int | None = None,
    challenge: bool = False,
    start_date: date | None = None,
    today: date | None = None,
) -> tuple[int, int] | None:
    """Inclusive day_number window: one week sample, never the full 100-day dump."""
    if not day_numbers:
        return None
    lo, hi = min(day_numbers), max(day_numbers)
    span = hi - lo + 1
    if not challenge and span <= 8:
        return lo, hi
    spw = max(1, min(7, int(sessions_per_week or 7)))
    today = today or date.today()
    week_i = 0
    if start_date:
        week_i = max(0, (today - start_date).days // 7)
    start = lo + week_i * spw
    end = start + spw - 1
    if start > hi:
        n_weeks = max(1, (span + spw - 1) // spw)
        week_i = n_weeks - 1
        start = lo + week_i * spw
        end = start + spw - 1
    return start, min(end, hi)


def experience_level_int(raw: Any) -> int:
    if raw is None:
        return 2
    if isinstance(raw, (int, float)):
        return max(1, min(3, int(raw)))
    return EXPERIENCE_TO_LEVEL.get(str(raw).strip().lower(), 2)


def resolve_today_day_number(
    *,
    start_date: date | None,
    day_numbers: list[int],
    challenge: bool = False,
    today: date | None = None,
) -> int | None:
    """Map calendar today onto a plan day_number (1-based from start, or cycling template)."""
    today = today or date.today()
    ordered = sorted({int(n) for n in day_numbers})
    if not ordered:
        return None
    if start_date:
        elapsed = (today - start_date).days
        if elapsed < 0:
            return None
        n = elapsed + 1
        if n in ordered:
            return n
        if challenge:
            return None
        return ordered[elapsed % len(ordered)]
    if len(ordered) <= 7:
        return ordered[today.weekday() % len(ordered)]
    return None


def _plan_sessions_per_week(plan: UserDailyPlan, day_count: int) -> int | None:
    insights = plan.insights_json if isinstance(plan.insights_json, dict) else {}
    raw = insights.get("sessions_per_week")
    try:
        if raw is not None:
            return max(1, min(7, int(raw)))
    except (TypeError, ValueError):
        pass
    if day_count and day_count <= 7:
        return day_count
    return None


def latest_plan(db: Session, user_id: str) -> UserDailyPlan | None:
    return (
        db.query(UserDailyPlan)
        .filter(UserDailyPlan.user_id == user_id)
        .order_by(UserDailyPlan.updated_at.desc())
        .first()
    )


def build_user_snapshot(db: Session, user_id: str) -> dict[str, Any]:
    user = db.get(User, user_id)
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    plan = latest_plan(db, user_id)
    age = None
    if profile and profile.birth_year:
        age = date.today().year - int(profile.birth_year)
        if age < 10 or age > 100:
            age = None
    active = None
    if plan:
        day_count = (
            db.query(UserDailyPlanDay)
            .filter(UserDailyPlanDay.plan_id == plan.id)
            .count()
        )
        active = {
            "id": plan.id,
            "title_vi": plan.title_vi,
            "sessions_per_week": _plan_sessions_per_week(plan, day_count),
            "target_calories": plan.target_calories,
            "target_protein_g": getattr(plan, "target_protein_g", None),
            "challenge_100_days": bool(getattr(plan, "challenge_100_days", False)),
            "day_count": day_count,
        }
    snap: dict[str, Any] = {
        "display_name": getattr(user, "display_name", None) if user else None,
        "goal": getattr(profile, "goal", None) if profile else None,
        "goal_vi": GOAL_VI.get(str(getattr(profile, "goal", None) or ""), None),
        "age": age,
        "gender": getattr(profile, "gender", None) if profile else None,
        "weight_kg": getattr(profile, "weight_kg", None) if profile else None,
        "height_cm": getattr(profile, "height_cm", None) if profile else None,
        "experience_level": getattr(profile, "experience_level", None) if profile else None,
        "training_location": getattr(profile, "training_location", None) if profile else None,
        "activity_level": getattr(profile, "activity_level", None) if profile else None,
        "tdee": getattr(profile, "tdee", None) if profile else None,
        "target_calories": getattr(profile, "target_calories", None) if profile else None,
        "target_protein_g": getattr(profile, "target_protein_g", None) if profile else None,
        "active_plan": active,
    }
    return drop_heavy_fields(snap)


def _load_week_days(
    db: Session, plan: UserDailyPlan
) -> tuple[list[UserDailyPlanDay], dict[str, Any]]:
    days = (
        db.query(UserDailyPlanDay)
        .filter(UserDailyPlanDay.plan_id == plan.id)
        .order_by(UserDailyPlanDay.day_number.asc())
        .all()
    )
    numbers = [int(d.day_number) for d in days]
    today = date.today()
    today_n = resolve_today_day_number(
        start_date=plan.start_date,
        day_numbers=numbers,
        challenge=bool(getattr(plan, "challenge_100_days", False)),
        today=today,
    )
    window = week_day_range(
        numbers,
        sessions_per_week=_plan_sessions_per_week(plan, len(days)),
        challenge=bool(getattr(plan, "challenge_100_days", False)),
        start_date=plan.start_date,
        today=today,
    )
    if window:
        start, end = window
        if today_n is not None:
            start = min(start, today_n)
            end = max(end, today_n)
        days = [d for d in days if start <= int(d.day_number) <= end]
    rest = today_n is None or today_n not in set(numbers)
    note = None
    if plan.start_date and today < plan.start_date:
        note = "Chưa tới ngày bắt đầu lịch."
    elif rest and numbers:
        note = "Hôm nay không có buổi tập trong lịch (nghỉ hoặc lịch đã hết)."
    meta = {
        "plan_id": plan.id,
        "title_vi": plan.title_vi,
        "week_day_start": window[0] if window else None,
        "week_day_end": window[1] if window else None,
        "sample_only": bool(getattr(plan, "challenge_100_days", False) or len(numbers) > 8),
        "today": today.isoformat(),
        "weekday_vi": WEEKDAY_VI[today.weekday()],
        "today_day_number": today_n,
        "today_is_rest": rest,
        "today_note_vi": note,
    }
    return days, meta


def _coerce_plan_id(plan_id: Any) -> int | None:
    if plan_id is None or plan_id == "":
        return None
    try:
        return int(plan_id)
    except (TypeError, ValueError):
        return None


def compact_plan_overview(db: Session, user_id: str, plan_id: int | None = None) -> dict[str, Any]:
    pid = _coerce_plan_id(plan_id)
    plan = (
        db.get(UserDailyPlan, pid)
        if pid
        else latest_plan(db, user_id)
    )
    if not plan or str(plan.user_id) != str(user_id):
        return {"error": "no_plan", "message_vi": "Bạn chưa có lịch tập trên tài khoản."}

    days, meta = _load_week_days(db, plan)
    day_ids = [d.id for d in days]
    exercises_by_day: dict[int, list[UserDailyPlanExercise]] = {d.id: [] for d in days}
    meals_by_day: dict[int, list[UserDailyPlanMeal]] = {d.id: [] for d in days}
    if day_ids:
        for ex in (
            db.query(UserDailyPlanExercise)
            .filter(UserDailyPlanExercise.plan_day_id.in_(day_ids))
            .order_by(UserDailyPlanExercise.sort_order.asc())
            .all()
        ):
            exercises_by_day.setdefault(ex.plan_day_id, []).append(ex)
        for meal in (
            db.query(UserDailyPlanMeal)
            .filter(UserDailyPlanMeal.plan_day_id.in_(day_ids))
            .order_by(UserDailyPlanMeal.sort_order.asc())
            .all()
        ):
            meals_by_day.setdefault(meal.plan_day_id, []).append(meal)

    ex_ids = {ex.exercise_id for items in exercises_by_day.values() for ex in items}
    food_ids = {m.food_id for items in meals_by_day.values() for m in items}
    exercises_map = {
        e.id: e for e in db.query(Exercise).filter(Exercise.id.in_(ex_ids)).all()
    } if ex_ids else {}
    foods_map = {
        f.id: f for f in db.query(Food).filter(Food.id.in_(food_ids)).all()
    } if food_ids else {}

    day_out = []
    for day in days:
        _, _, _, split_role = unpack_day_notes(day.notes_vi)
        ex_out = []
        for ex in exercises_by_day.get(day.id) or []:
            catalog = exercises_map.get(ex.exercise_id)
            ex_out.append(
                {
                    "exercise_id": ex.exercise_id,
                    "name_vi": (catalog.name_vi if catalog else None) or str(ex.exercise_id),
                    "sets": ex.sets,
                    "reps": ex.reps,
                    "rest_seconds": ex.rest_seconds,
                    "section": getattr(ex, "section", None) or "main",
                }
            )
        meal_out = []
        for meal in (meals_by_day.get(day.id) or [])[:8]:
            food = foods_map.get(meal.food_id)
            servings = float(meal.servings or 1)
            cal = int(round((food.calories or 0) * servings)) if food else None
            meal_out.append(
                {
                    "food_id": meal.food_id,
                    "name_vi": food.name_vi if food else f"#{meal.food_id}",
                    "meal_type": meal.meal_type,
                    "servings": servings,
                    "calories": cal,
                }
            )
        day_out.append(
            {
                "day_number": day.day_number,
                "title_vi": day.title_vi,
                "split_role": split_role,
                "is_today": int(day.day_number) == meta.get("today_day_number"),
                "target_calories": getattr(day, "target_calories", None),
                "exercises": ex_out,
                "meals": meal_out or None,
            }
        )

    payload = {
        **meta,
        "target_calories": plan.target_calories,
        "target_protein_g": getattr(plan, "target_protein_g", None),
        "days": day_out,
    }
    return drop_heavy_fields(payload)


def analyze_plan_for_goal(db: Session, user_id: str, plan_id: int | None = None) -> dict[str, Any]:
    pid = _coerce_plan_id(plan_id)
    plan = (
        db.get(UserDailyPlan, pid)
        if pid
        else latest_plan(db, user_id)
    )
    if not plan or str(plan.user_id) != str(user_id):
        return {"error": "no_plan", "message_vi": "Bạn chưa có lịch tập để phân tích."}

    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    goal = (getattr(profile, "goal", None) or "maintain") if profile else "maintain"
    level = experience_level_int(getattr(profile, "experience_level", None) if profile else None)

    days, meta = _load_week_days(db, plan)
    day_ids = [d.id for d in days]
    if not day_ids:
        return {"error": "empty_plan", "message_vi": "Lịch tập chưa có buổi nào."}

    rows = (
        db.query(UserDailyPlanExercise)
        .filter(UserDailyPlanExercise.plan_day_id.in_(day_ids))
        .all()
    )
    by_day: dict[int, list[UserDailyPlanExercise]] = {d.id: [] for d in days}
    for ex in rows:
        by_day.setdefault(ex.plan_day_id, []).append(ex)

    ex_ids = {ex.exercise_id for ex in rows}
    meta_by_id: dict[int, dict[str, Any]] = {}
    if ex_ids:
        for ex, mg in (
            db.query(Exercise, MuscleGroup)
            .join(MuscleGroup, MuscleGroup.id == Exercise.muscle_group_id)
            .filter(Exercise.id.in_(ex_ids))
            .all()
        ):
            meta_by_id[int(ex.id)] = {
                "muscle_slug": mg.slug,
                "movement_pattern": getattr(ex, "movement_pattern", None),
            }

    fake_days = []
    family_days: dict[str, set[int]] = {}
    for day in days:
        items = []
        for ex in by_day.get(day.id) or []:
            items.append(
                SimpleNamespace(
                    exercise_id=ex.exercise_id,
                    sets=ex.sets,
                    section=getattr(ex, "section", None) or "main",
                )
            )
            if (getattr(ex, "section", None) or "main") != "main":
                continue
            info = meta_by_id.get(int(ex.exercise_id)) or {}
            fam = volume_family(info.get("muscle_slug"), info.get("movement_pattern"))
            if fam != "other":
                family_days.setdefault(fam, set()).add(int(day.day_number))
        fake_days.append(SimpleNamespace(exercises=items, split_role=unpack_day_notes(day.notes_vi)[3]))

    counts = count_weekly_sets(fake_days, meta_by_id)
    budget = weekly_budget(level)
    families: dict[str, Any] = {}
    notes: list[str] = []
    for fam, band in budget.items():
        sets = int(counts.get(fam, 0) or 0)
        if sets < band.recommended_min:
            verdict = "low"
        elif sets > band.max_sets:
            verdict = "high"
        else:
            verdict = "ok"
        families[fam] = {
            "hard_sets": sets,
            "min": band.recommended_min,
            "target": band.target_sets,
            "max": band.max_sets,
            "verdict": verdict,
            "days_per_week": len(family_days.get(fam) or []),
        }
        if verdict == "low" and fam in PRIMARY_FAMS:
            notes.append(
                f"{fam}: {sets} hard sets/tuần — dưới tối thiểu {band.recommended_min} (mục tiêu {band.target_sets})."
            )
        elif verdict == "high" and fam in PRIMARY_FAMS:
            notes.append(
                f"{fam}: {sets} hard sets/tuần — vượt trần {band.max_sets}."
            )

    primary_ok = all(families[f]["verdict"] != "low" for f in PRIMARY_FAMS if f in families)
    if goal == "gain_muscle" and primary_ok:
        suitable = True
        summary = "Volume nhóm cơ chính nằm trong vùng tăng cơ cho trình độ hiện tại."
    elif goal == "gain_muscle" and not primary_ok:
        suitable = False
        summary = "Volume một số nhóm cơ chính còn thấp so với mục tiêu tăng cơ."
    elif goal == "lose_weight":
        suitable = True
        summary = "Có thể dùng lịch này để giảm mỡ nếu ăn deficit; volume sức mạnh vẫn nên giữ gần mức tối thiểu."
    else:
        suitable = primary_ok
        summary = "Volume chính nằm trong ngân sách tuần." if primary_ok else "Volume chính lệch ngân sách tuần."

    return drop_heavy_fields(
        {
            **meta,
            "goal": goal,
            "goal_vi": GOAL_VI.get(goal, goal),
            "experience_level": level,
            "families": families,
            "suitable_for_goal": suitable,
            "summary_vi": summary,
            "notes_vi": notes,
        }
    )


def profile_for_calculator(db: Session, user_id: str) -> dict[str, Any]:
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    if not profile:
        return {}
    age = None
    if profile.birth_year:
        age = date.today().year - int(profile.birth_year)
    return {
        "gender": profile.gender or "male",
        "weight_kg": profile.weight_kg,
        "height_cm": profile.height_cm,
        "age": age,
        "activity_level": profile.activity_level or "moderate",
        "goal": profile.goal or "maintain",
    }


def utcnow() -> datetime:
    return datetime.now(UTC)
