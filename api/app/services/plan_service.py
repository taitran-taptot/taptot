"""User daily plan service — nested create/list/detail + export payload."""

from __future__ import annotations

import json
import secrets
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.exceptions import AppException, BadRequestError, ForbiddenError, NotFoundError
from app.models.entities import (
    AiGeneration,
    Exercise,
    Export,
    Food,
    MuscleGroup,
    UserDailyPlan,
    UserDailyPlanDay,
    UserDailyPlanExercise,
    UserDailyPlanMeal,
    UserProfile,
)
from app.schemas.plans import CreatePlanRequest, PlanDayIn, PlanExerciseIn, PlanMealIn, UpdatePlanContentRequest
from app.services.workout_rest import default_rest_for_section
from app.services.export_service import ExportService
from app.services.meal_constants import VALID_MEALS
from app.services.plan_guest import (
    GUEST_CHALLENGE_TTL_DAYS,
    GUEST_EXPIRED_MESSAGE,
    GUEST_TTL_DAYS,
    aware as _aware,
    guest_days_left,
    guest_expires_at,
    guest_ttl_days,
    is_guest_expired,
    purge_expired_guest_plans,
)
from app.services.plan_notes import (
    pack_day_notes,
    unpack_day_notes,
)

VALID_SECTIONS = frozenset({"warmup", "main", "cooldown", "cardio"})
VALID_SOURCES = frozenset({"manual", "ai", "template", "imported"})
RESTORE_SNAPSHOT_KEY = "restore_snapshot"


def _plan_current_week(plan: UserDailyPlan, *, today: date | None = None) -> int:
    ref = today or datetime.now(UTC).date()
    start = plan.start_date
    if start is None and plan.created_at:
        start = _aware(plan.created_at).date()
    if start is None:
        return 1
    days_elapsed = (ref - start).days
    if days_elapsed < 0:
        return 1
    return max(1, days_elapsed // 7 + 1)


def _nutrition_checkin_due(plan: UserDailyPlan, insights: dict[str, Any]) -> date | None:
    start = plan.start_date
    if start is None and plan.created_at:
        start = _aware(plan.created_at).date()
    if start is None:
        return None
    checkins = insights.get("nutrition_checkins") or []
    n = len(checkins) + 1
    interval = int(insights.get("nutrition_checkin_interval_days") or 0)
    if interval <= 0:
        if insights.get("challenge_100_days") or insights.get("curriculum"):
            interval = 28
        else:
            block = int(insights.get("nutrition_block_size") or 2)
            interval = max(14, block * 7)
    return start + timedelta(days=interval * n)


def _day_orm_to_plan_in(day: UserDailyPlanDay, exercises: list, meals: list) -> PlanDayIn:
    meal_notes, section_notes, free, split_role = unpack_day_notes(day.notes_vi)
    return PlanDayIn(
        day_number=day.day_number,
        title_vi=day.title_vi,
        notes_vi=free,
        split_role=split_role,
        meal_notes=meal_notes,
        section_notes=section_notes,
        target_calories=day.target_calories,
        target_protein_g=day.target_protein_g,
        target_carbs_g=day.target_carbs_g,
        target_fat_g=day.target_fat_g,
        exercises=[
            PlanExerciseIn(
                exercise_id=ex.exercise_id,
                sets=ex.sets,
                reps=ex.reps,
                rest_seconds=ex.rest_seconds,
                section=getattr(ex, "section", None) or "main",
                notes_vi=ex.notes_vi,
                sort_order=ex.sort_order,
            )
            for ex in exercises
        ],
        meals=[
            PlanMealIn(
                food_id=m.food_id,
                meal_type=m.meal_type,
                servings=float(m.servings or 1),
                notes_vi=m.notes_vi,
                sort_order=m.sort_order,
            )
            for m in meals
        ],
    )


def _load_day_children(
    db: Session, days: list[UserDailyPlanDay]
) -> tuple[dict[int, list], dict[int, list]]:
    """Batch-load exercises + meals for a set of plan days (avoids N+1)."""
    exercises_by_day: dict[int, list] = {d.id: [] for d in days}
    meals_by_day: dict[int, list] = {d.id: [] for d in days}
    day_ids = [d.id for d in days]
    if not day_ids:
        return exercises_by_day, meals_by_day
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
    return exercises_by_day, meals_by_day


def _new_share_token() -> str:
    # ~128-bit URL-safe token — capability URL for guest/public plans
    return secrets.token_urlsafe(16)


def _reapply_ai_weekly_dose(
    days: list[Any],
    *,
    insights_json: dict[str, Any] | None,
    sessions_per_week: int,
    experience_level: int | None,
    strength_tier: str | None,
) -> list[Any]:
    """Clamp each expanded week so periodization +sets cannot exceed the budget."""
    raw = insights_json or {}
    meta_raw = raw.get("volume_meta") or {}
    if not isinstance(meta_raw, dict) or not meta_raw:
        return days
    meta_by_id: dict[int, dict[str, Any]] = {}
    for key, val in meta_raw.items():
        try:
            meta_by_id[int(key)] = dict(val) if isinstance(val, dict) else {}
        except (TypeError, ValueError):
            continue
    if not meta_by_id:
        return days
    from app.services.workout_generation.weekly_volume import apply_weekly_dose_expanded

    focus = frozenset(str(s) for s in (raw.get("focus_slugs") or []) if s)
    level = int(raw.get("effective_level") or experience_level or 1)
    tier = str(raw.get("strength_tier") or strength_tier or "ok")
    minutes = int(raw.get("session_minutes") or 45)
    conservative = bool(raw.get("conservative_volume"))
    days, _note = apply_weekly_dose_expanded(
        days,
        sessions_per_week=sessions_per_week,
        meta_by_id=meta_by_id,
        effective_level=level,
        strength_tier=tier,
        focus_slugs=focus,
        session_minutes=minutes,
        conservative_volume=conservative,
    )
    return days


def _as_instruction_steps(raw: Any) -> list[str] | None:
    if raw is None:
        return None
    if isinstance(raw, list):
        steps = [str(x).strip() for x in raw if str(x).strip()]
        return steps or None
    if isinstance(raw, str) and raw.strip():
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                steps = [str(x).strip() for x in parsed if str(x).strip()]
                return steps or None
        except (json.JSONDecodeError, TypeError):
            return [raw.strip()]
    return None


def _resolve_import_rest_seconds(ex: dict[str, Any]) -> int:
    raw = ex.get("rest_seconds")
    if raw is not None and raw != "":
        return int(raw)
    return default_rest_for_section(
        ex.get("section"),
        movement_role=ex.get("movement_role"),
    )


class PlanService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _experience_level_for_user(
        self,
        user_id: str | None,
        payload_level: int | None,
    ) -> int:
        if payload_level is not None:
            return max(1, min(5, int(payload_level)))
        if not user_id:
            return 2
        profile = self.db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        if not profile:
            return 2
        mapping = {"beginner": 2, "intermediate": 3, "advanced": 5}
        return mapping.get(str(profile.experience_level or "").lower(), 2)

    def count_user_plans(self, user_id: str) -> int:
        return (
            self.db.query(UserDailyPlan)
            .filter(UserDailyPlan.user_id == user_id)
            .count()
        )

    def get_quota(self, user_id: str) -> dict[str, Any]:
        """Informational only — no plan-count cap."""
        used = self.count_user_plans(user_id)
        return {"used": used, "limit": None, "remaining": None, "unlimited": True}

    def list_plans(self, user_id: str) -> list[dict[str, Any]]:
        plans = (
            self.db.query(UserDailyPlan)
            .filter(UserDailyPlan.user_id == user_id)
            .order_by(UserDailyPlan.created_at.desc())
            .all()
        )
        return self._summaries(plans)

    def get_plan(self, user_id: str, plan_id: int) -> dict[str, Any]:
        plan = self._get_owned(user_id, plan_id)
        return self._detail(plan)

    def get_by_share_token(self, token: str) -> dict[str, Any]:
        plan = (
            self.db.query(UserDailyPlan)
            .filter(UserDailyPlan.share_token == token)
            .first()
        )
        if not plan:
            raise NotFoundError("UserDailyPlan", token)
        if is_guest_expired(plan):
            self.db.delete(plan)
            self.db.commit()
            raise AppException(GUEST_EXPIRED_MESSAGE, status_code=404)
        return self._detail(plan)

    def create_plan(
        self,
        user_id: str | None,
        payload: CreatePlanRequest,
        *,
        ai_generation_id: int | None = None,
        insights_json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if payload.source not in VALID_SOURCES:
            raise BadRequestError("Invalid plan source")
        days = list(payload.days)
        duration_weeks = getattr(payload, "duration_weeks", 1) or 1
        if duration_weeks > 1 and days:
            from app.services.periodization import (
                expand_plan_days_for_weeks,
                periodization_description_note,
                resolve_overload_profile,
            )

            experience_level = self._experience_level_for_user(user_id, payload.experience_level)
            strength_tier = getattr(payload, "strength_tier", None)
            profile = resolve_overload_profile(experience_level, strength_tier=strength_tier)
            template_len = len(days)
            insights = insights_json or {}
            curriculum = bool(
                insights.get("challenge_100_days")
                or insights.get("curriculum")
                or insights.get("curriculum_12_weeks")
            )
            free_home = str(insights.get("generation_mode") or "").strip().lower() == "free_home"
            gen_mode = str(insights.get("generation_mode") or "").strip().lower()
            familiarization = gen_mode in {
                "familiarization",
                "fitness_advanced",
                "fitness_soldier",
            }
            week_templates = None
            raw_templates = insights.get("week_templates")
            if curriculum and isinstance(raw_templates, list) and raw_templates:
                week_templates = []
                for phase in raw_templates:
                    if isinstance(phase, dict) and ("a" in phase or "b" in phase):
                        a_days = [
                            PlanDayIn(**d) if isinstance(d, dict) else d
                            for d in (phase.get("a") or [])
                        ]
                        b_days = [
                            PlanDayIn(**d) if isinstance(d, dict) else d
                            for d in (phase.get("b") or [])
                        ]
                        week_templates.append({"a": a_days, "b": b_days or a_days})
                    elif isinstance(phase, list):
                        week_templates.append(
                            [
                                PlanDayIn(**d) if isinstance(d, dict) else d
                                for d in phase
                            ]
                        )
            if familiarization:
                from app.services.workout_generation.familiarization_curriculum import (
                    expand_familiarization_weeks,
                )

                raw_weeks = insights.get("familiarization_week_templates")
                parsed_weeks: list[list[PlanDayIn]] = []
                if isinstance(raw_weeks, list):
                    for raw_week in raw_weeks:
                        if not isinstance(raw_week, list):
                            continue
                        parsed_weeks.append(
                            [
                                PlanDayIn(**day) if isinstance(day, dict) else day
                                for day in raw_week
                            ]
                        )
                if not parsed_weeks:
                    raise BadRequestError("Lịch Làm quen thiếu mẫu tuần.")
                days = expand_familiarization_weeks(parsed_weeks)
            elif free_home:
                from app.services.workout_generation.free_home_curriculum import (
                    expand_free_home_weeks,
                )

                days = expand_free_home_weeks(days, duration_weeks)
            else:
                days = expand_plan_days_for_weeks(
                    days,
                    duration_weeks,
                    is_dict=False,
                    experience_level=experience_level,
                    strength_tier=strength_tier,
                    week_templates=week_templates,
                    curriculum=curriculum,
                )
                days = _reapply_ai_weekly_dose(
                    days,
                    insights_json=insights_json,
                    sessions_per_week=template_len,
                    experience_level=experience_level,
                    strength_tier=strength_tier,
                )
            nb = insights.get("nutrition_blocks")
            spw = insights.get("sessions_per_week")
            bs = int(insights.get("nutrition_block_size") or 2)
            if nb and spw:
                from app.services.workout_generation.meal_engine import (
                    apply_nutrition_blocks_to_expanded_days,
                )

                cur = insights.get("curriculum") or {}
                deload_weeks = cur.get("deload_weeks") if curriculum else None
                days = apply_nutrition_blocks_to_expanded_days(
                    days,
                    nb,
                    sessions_per_week=int(spw),
                    block_size=bs,
                    deload_weeks=deload_weeks,
                )
            desc = payload.description_vi or ""
            payload = payload.model_copy(update={"days": days})
            if payload.source != "ai":
                note = periodization_description_note(
                    profile, duration_weeks, curriculum=curriculum
                )
                if note not in desc:
                    payload = payload.model_copy(
                        update={"description_vi": (desc + "\n" + note).strip() if desc else note}
                    )
        stored_insights = dict(insights_json) if insights_json else None
        if payload.source == "ai":
            stored_insights = dict(stored_insights or {})
            stored_insights[RESTORE_SNAPSHOT_KEY] = {
                "days": [d.model_dump(mode="json") for d in payload.days]
            }
        now = datetime.now(UTC)
        token = _new_share_token()
        plan = UserDailyPlan(
            user_id=user_id,
            title_vi=payload.title_vi.strip(),
            description_vi=payload.description_vi,
            start_date=payload.start_date,
            end_date=payload.end_date,
            target_calories=payload.target_calories,
            target_protein_g=payload.target_protein_g,
            target_carbs_g=payload.target_carbs_g,
            target_fat_g=payload.target_fat_g,
            source=payload.source,
            is_template=bool(payload.is_template),
            share_token=token,
            ai_generation_id=ai_generation_id,
            insights_json=stored_insights,
            challenge_100_days=bool(getattr(payload, "challenge_100_days", False)),
            created_at=now,
            updated_at=now,
        )
        self.db.add(plan)
        self.db.flush()
        self._add_days(plan.id, payload.days)
        if payload.source == "ai" and user_id and not plan.ai_generation_id:
            snapshot = (stored_insights or {}).get(RESTORE_SNAPSHOT_KEY) or {
                "days": [d.model_dump(mode="json") for d in payload.days]
            }
            gen = AiGeneration(
                user_id=user_id,
                generation_type="workout_schedule",
                input_params={},
                output_data=snapshot,
                is_paid=False,
                created_at=now,
            )
            self.db.add(gen)
            self.db.flush()
            plan.ai_generation_id = gen.id
        self.db.commit()
        return self._detail(plan)

    def claim_guest_plans(self, user_id: str, share_tokens: list[str]) -> dict[str, Any]:
        """Attach orphan (guest) plans to the logged-in user."""
        tokens = []
        seen: set[str] = set()
        for raw in share_tokens:
            t = (raw or "").strip()
            if not t or t in seen:
                continue
            seen.add(t)
            tokens.append(t)

        claimed_plans: list[UserDailyPlan] = []
        not_found: list[str] = []
        already_owned: list[str] = []
        mutated = False

        for token in tokens:
            plan = (
                self.db.query(UserDailyPlan)
                .filter(UserDailyPlan.share_token == token)
                .first()
            )
            if not plan:
                not_found.append(token)
                continue
            if is_guest_expired(plan):
                self.db.delete(plan)
                mutated = True
                not_found.append(token)
                continue
            if plan.user_id is not None:
                if str(plan.user_id) == str(user_id):
                    already_owned.append(token)
                else:
                    # Belonging to another account — cannot claim
                    not_found.append(token)
                continue
            plan.user_id = user_id
            plan.updated_at = datetime.now(UTC)
            mutated = True
            claimed_plans.append(plan)

        if mutated:
            self.db.commit()

        claimed = self._summaries(claimed_plans)

        return {
            "claimed_count": len(claimed),
            "claimed": claimed,
            "skipped_full": [],
            "not_found": not_found,
            "already_owned": already_owned,
            "quota": self.get_quota(user_id),
        }

    def delete_plan(self, user_id: str, plan_id: int) -> None:
        plan = self._get_owned(user_id, plan_id)
        self.db.delete(plan)
        self.db.commit()

    def update_plan_content(self, user_id: str, plan_id: int, payload: UpdatePlanContentRequest) -> dict[str, Any]:
        """Update exercises (sets/reps) and meals only — keep calories & plan meta locked."""
        plan = self._get_owned(user_id, plan_id)
        existing_days = (
            self.db.query(UserDailyPlanDay)
            .filter(UserDailyPlanDay.plan_id == plan.id)
            .all()
        )
        by_number = {d.day_number: d for d in existing_days}
        if not by_number:
            raise BadRequestError("Plan has no days to edit")

        seen: set[int] = set()
        for day_in in payload.days:
            if day_in.day_number in seen:
                raise BadRequestError(f"Duplicate day_number: {day_in.day_number}")
            seen.add(day_in.day_number)
            day = by_number.get(day_in.day_number)
            if not day:
                raise BadRequestError(
                    f"Không thể thêm ngày mới — chỉ sửa ngày đã có (ngày {day_in.day_number} không tồn tại)."
                )

            if day_in.meal_notes is not None or day_in.section_notes is not None:
                old_mn, old_sn, free, old_role = unpack_day_notes(day.notes_vi)
                day.notes_vi = pack_day_notes(
                    meal_notes=day_in.meal_notes if day_in.meal_notes is not None else old_mn,
                    section_notes=day_in.section_notes if day_in.section_notes is not None else old_sn,
                    free_text=free,
                    split_role=day_in.split_role if day_in.split_role is not None else old_role,
                )

            self.db.query(UserDailyPlanExercise).filter(
                UserDailyPlanExercise.plan_day_id == day.id
            ).delete(synchronize_session=False)
            self.db.query(UserDailyPlanMeal).filter(
                UserDailyPlanMeal.plan_day_id == day.id
            ).delete(synchronize_session=False)

            for idx, ex in enumerate(day_in.exercises):
                section = ex.section if ex.section in VALID_SECTIONS else "main"
                if not self.db.get(Exercise, ex.exercise_id):
                    raise BadRequestError(f"Unknown exercise_id: {ex.exercise_id}")
                self.db.add(
                    UserDailyPlanExercise(
                        plan_day_id=day.id,
                        exercise_id=ex.exercise_id,
                        sort_order=ex.sort_order if ex.sort_order is not None else idx,
                        sets=ex.sets,
                        reps=str(ex.reps) if ex.reps is not None else None,
                        rest_seconds=ex.rest_seconds,
                        section=section,
                        notes_vi=ex.notes_vi,
                    )
                )

            for idx, meal in enumerate(day_in.meals):
                meal_type = meal.meal_type if meal.meal_type in VALID_MEALS else "lunch"
                if not self.db.get(Food, meal.food_id):
                    raise BadRequestError(f"Unknown food_id: {meal.food_id}")
                self.db.add(
                    UserDailyPlanMeal(
                        plan_day_id=day.id,
                        meal_type=meal_type,
                        food_id=meal.food_id,
                        servings=meal.servings,
                        sort_order=meal.sort_order if meal.sort_order is not None else idx,
                        notes_vi=meal.notes_vi,
                    )
                )

        # Days not included in payload keep previous content (partial update by day).
        plan.updated_at = datetime.now(UTC)
        self.db.commit()
        return self.get_plan(user_id, plan_id)

    def restore_ai(self, user_id: str, plan_id: int) -> dict[str, Any]:
        """Replace edited days with the original TAPTOT snapshot."""
        plan = self._get_owned(user_id, plan_id)
        snapshot = self._ai_restore_snapshot(plan, user_id)
        raw_days = snapshot.get("days") if isinstance(snapshot, dict) else None
        if not isinstance(raw_days, list) or not raw_days:
            raise BadRequestError("Bản TAPTOT gốc không hợp lệ.")
        try:
            days = [
                d if isinstance(d, PlanDayIn) else PlanDayIn.model_validate(d)
                for d in raw_days
            ]
        except Exception as exc:
            raise BadRequestError("Bản TAPTOT gốc không hợp lệ.") from exc
        self._replace_plan_days(plan, days)
        plan.updated_at = datetime.now(UTC)
        self.db.commit()
        return self.get_plan(user_id, plan_id)

    def _ai_restore_snapshot(self, plan: UserDailyPlan, user_id: str) -> dict[str, Any]:
        if plan.ai_generation_id:
            gen = self.db.get(AiGeneration, plan.ai_generation_id)
            if not gen:
                raise NotFoundError("AiGeneration", plan.ai_generation_id)
            if str(gen.user_id) != str(user_id):
                raise ForbiddenError("Not your plan")
            data = gen.output_data if isinstance(gen.output_data, dict) else None
            if data:
                return data
        insights = plan.insights_json if isinstance(plan.insights_json, dict) else {}
        stored = insights.get(RESTORE_SNAPSHOT_KEY)
        if isinstance(stored, dict) and stored.get("days"):
            return stored
        raise NotFoundError("AiGeneration", "original")

    def _replace_plan_days(self, plan: UserDailyPlan, days: list[PlanDayIn]) -> None:
        existing = (
            self.db.query(UserDailyPlanDay)
            .filter(UserDailyPlanDay.plan_id == plan.id)
            .all()
        )
        day_ids = [int(d.id) for d in existing]
        if day_ids:
            self.db.query(UserDailyPlanExercise).filter(
                UserDailyPlanExercise.plan_day_id.in_(day_ids)
            ).delete(synchronize_session=False)
            self.db.query(UserDailyPlanMeal).filter(
                UserDailyPlanMeal.plan_day_id.in_(day_ids)
            ).delete(synchronize_session=False)
            self.db.query(UserDailyPlanDay).filter(
                UserDailyPlanDay.plan_id == plan.id
            ).delete(synchronize_session=False)
            self.db.flush()
            for day in existing:
                if day in self.db:
                    self.db.expunge(day)
        self._add_days(plan.id, days)

    def preview_nutrition_checkin(
        self, user_id: str, plan_id: int, weight_kg: float
    ) -> dict[str, Any]:
        return self._nutrition_checkin_core(user_id, plan_id, weight_kg, preview=True)

    def nutrition_checkin(self, user_id: str, plan_id: int, weight_kg: float) -> dict[str, Any]:
        return self._nutrition_checkin_core(user_id, plan_id, weight_kg, preview=False)

    def _nutrition_checkin_core(
        self,
        user_id: str,
        plan_id: int,
        weight_kg: float,
        *,
        preview: bool,
    ) -> dict[str, Any]:
        if weight_kg < 30 or weight_kg > 300:
            raise BadRequestError("Cân nặng không hợp lệ (30–300 kg).")
        plan = self._get_owned(user_id, plan_id)
        insights: dict[str, Any] = dict(plan.insights_json or {})
        old_blocks: list[dict[str, Any]] = list(insights.get("nutrition_blocks") or [])
        nut_payload: dict[str, Any] = dict(insights.get("nutrition_payload") or {})
        spw = int(insights.get("sessions_per_week") or 0)
        block_size = int(insights.get("nutrition_block_size") or 2)
        if not old_blocks or not nut_payload or spw <= 0:
            raise BadRequestError(
                "Lịch này chưa có điều chỉnh dinh dưỡng theo block — không thể cập nhật cân."
            )

        from app.services.workout_generation.meal_engine import (
            apply_nutrition_blocks_to_expanded_days,
            generate_meals_with_blocks,
            parse_week_from_title,
        )
        from app.services.workout_generation.nutrition_targets import (
            NutritionBlock,
            build_nutrition_blocks,
            build_weekly_calorie_schedule,
            clamp_block_avg_target,
            estimate_targets,
            parse_kg_per_week,
            targets_for_calories,
        )

        goal = str(nut_payload.get("goal") or "maintain")
        kg_rate = float(
            insights.get("kg_per_week")
            or nut_payload.get("kg_per_week")
            or parse_kg_per_week(nut_payload, goal=goal)
        )
        current_week = _plan_current_week(plan)
        current_bi = min((current_week - 1) // block_size, len(old_blocks) - 1)
        current_block = old_blocks[current_bi]
        prev_avg = int(current_block.get("avg_target_calories") or plan.target_calories or 2000)
        last_weight = float(nut_payload.get("weight_kg") or current_block.get("projected_weight_kg") or weight_kg)

        check_payload = {**nut_payload, "weight_kg": weight_kg}
        nt = estimate_targets(check_payload)
        if nt is None:
            raise BadRequestError("Thiếu chiều cao/tuổi để tính lại calo.")

        raw_avg = int(nt.target_calories)
        if goal == "lose_weight":
            expected = kg_rate * block_size
            actual = last_weight - weight_kg
            if actual > expected * 1.2:
                raw_avg = prev_avg
            elif actual < expected * 0.5:
                raw_avg = min(prev_avg, max(raw_avg, prev_avg - 100))
        elif goal == "gain_weight":
            expected = kg_rate * block_size
            actual = weight_kg - last_weight
            if actual > expected * 1.2:
                raw_avg = prev_avg
            elif actual < expected * 0.5:
                raw_avg = max(prev_avg, min(raw_avg, prev_avg + 100))

        new_avg = clamp_block_avg_target(raw_avg, prev_avg, goal)

        preview_out = {
            "weight_kg": weight_kg,
            "avg_target_calories": new_avg,
            "delta_from_current": new_avg - prev_avg,
            "protein_g": nt.protein_g,
            "current_week": current_week,
            "block_index": current_bi,
        }
        if preview:
            return {"preview": preview_out, "plan": self._detail(plan)}

        days_orm = (
            self.db.query(UserDailyPlanDay)
            .filter(UserDailyPlanDay.plan_id == plan.id)
            .order_by(UserDailyPlanDay.day_number.asc())
            .all()
        )
        if not days_orm:
            raise BadRequestError("Lịch không có ngày tập.")

        max_week = max(parse_week_from_title(d.title_vi) for d in days_orm)
        week_from = current_bi * block_size + 1
        weeks_from_here = max(1, max_week - week_from + 1)

        exercises_by_day, meals_by_day = _load_day_children(self.db, days_orm)
        template_days = [
            _day_orm_to_plan_in(
                day,
                exercises_by_day.get(day.id, []),
                meals_by_day.get(day.id, []),
            )
            for day in days_orm[:spw]
        ]

        split_roles = [d.split_role for d in template_days]
        gender = str(nut_payload.get("gender") or "male").lower()
        if gender not in {"male", "female"}:
            gender = "male"

        rebuilt = build_nutrition_blocks(
            {**nut_payload, "weight_kg": weight_kg},
            goal=goal,
            duration_weeks=weeks_from_here,
            split_roles=split_roles,
            block_size=block_size,
        )
        if not rebuilt:
            raise BadRequestError("Không tính được block dinh dưỡng mới.")

        first = rebuilt[0]
        if first.schedule.avg_target != new_avg:
            adjusted_base = targets_for_calories(
                first.targets,
                goal=goal,
                weight_kg=first.projected_weight_kg,
                target_calories=new_avg,
            )
            schedule = build_weekly_calorie_schedule(
                goal=goal,
                avg_target=new_avg,
                split_roles=split_roles,
                gender=gender,
                weight_kg=first.projected_weight_kg,
                bmr=float(first.targets.bmr),
                base=adjusted_base,
            )
            rebuilt = [
                NutritionBlock(
                    block_index=0,
                    week_from=week_from,
                    week_to=min(max_week, week_from + block_size - 1),
                    projected_weight_kg=first.projected_weight_kg,
                    targets=adjusted_base,
                    schedule=schedule,
                ),
                *[
                    NutritionBlock(
                        block_index=i + 1,
                        week_from=week_from + (i + 1) * block_size,
                        week_to=min(max_week, week_from + (i + 2) * block_size - 1),
                        projected_weight_kg=b.projected_weight_kg,
                        targets=b.targets,
                        schedule=b.schedule,
                    )
                    for i, b in enumerate(rebuilt[1:])
                ],
            ]

        for i, block in enumerate(rebuilt):
            block_index = current_bi + i
            wf = block_index * block_size + 1
            wt = min(max_week, (block_index + 1) * block_size)
            rebuilt[i] = NutritionBlock(
                block_index=block_index,
                week_from=wf,
                week_to=wt,
                projected_weight_kg=block.projected_weight_kg,
                targets=block.targets,
                schedule=block.schedule,
            )

        meal_result = generate_meals_with_blocks(
            self.db, nut_payload, rebuilt, template_days, goal=goal
        )
        new_insights = meal_result.nutrition_blocks
        for i, ins in enumerate(new_insights):
            ins["block_index"] = current_bi + i
            wf = current_bi * block_size + 1 + i * block_size
            wt = min(max_week, wf + block_size - 1)
            ins["weeks"] = list(range(wf, wt + 1))

        merged_blocks = old_blocks[:current_bi] + new_insights

        all_days_in = [
            _day_orm_to_plan_in(
                day,
                exercises_by_day.get(day.id, []),
                meals_by_day.get(day.id, []),
            )
            for day in days_orm
        ]

        applied = apply_nutrition_blocks_to_expanded_days(
            all_days_in,
            merged_blocks,
            sessions_per_week=spw,
            block_size=block_size,
        )

        replace_day_ids = [
            day_orm.id
            for day_orm in days_orm
            if parse_week_from_title(day_orm.title_vi) >= week_from
        ]
        if replace_day_ids:
            self.db.query(UserDailyPlanMeal).filter(
                UserDailyPlanMeal.plan_day_id.in_(replace_day_ids)
            ).delete(synchronize_session=False)

        for day_orm, day_in in zip(days_orm, applied):
            week = parse_week_from_title(day_orm.title_vi)
            if week < week_from:
                continue
            day_orm.target_calories = day_in.target_calories
            day_orm.target_protein_g = day_in.target_protein_g
            day_orm.target_carbs_g = day_in.target_carbs_g
            day_orm.target_fat_g = day_in.target_fat_g
            for idx, meal in enumerate(day_in.meals or []):
                meal_type = meal.meal_type if meal.meal_type in VALID_MEALS else "lunch"
                self.db.add(
                    UserDailyPlanMeal(
                        plan_day_id=day_orm.id,
                        meal_type=meal_type,
                        food_id=meal.food_id,
                        servings=meal.servings,
                        sort_order=meal.sort_order if meal.sort_order is not None else idx,
                        notes_vi=meal.notes_vi,
                    )
                )
            if day_in.meal_notes is not None:
                old_mn, old_sn, free, role = unpack_day_notes(day_orm.notes_vi)
                day_orm.notes_vi = pack_day_notes(
                    meal_notes=day_in.meal_notes,
                    section_notes=old_sn,
                    free_text=free,
                    split_role=role,
                )

        nut_payload["weight_kg"] = weight_kg
        checkins = list(insights.get("nutrition_checkins") or [])
        checkins.append(
            {
                "at": datetime.now(UTC).isoformat(),
                "weight_kg": weight_kg,
                "avg_target_calories": new_avg,
                "week": current_week,
                "block_index": current_bi,
            }
        )
        insights["nutrition_blocks"] = merged_blocks
        insights["nutrition_payload"] = nut_payload
        insights["nutrition_checkins"] = checkins
        insights["last_nutrition_checkin_at"] = checkins[-1]["at"]
        next_due = _nutrition_checkin_due(plan, insights)
        if next_due:
            insights["next_nutrition_checkin_due"] = next_due.isoformat()
        b0 = merged_blocks[0]
        if b0.get("rest_day_nutrition"):
            insights["rest_day_nutrition"] = b0["rest_day_nutrition"]
        if b0.get("rest_day_meals"):
            insights["rest_day_meals"] = b0["rest_day_meals"]

        plan.insights_json = insights
        plan.target_calories = int(b0.get("avg_target_calories") or new_avg)
        plan.target_protein_g = b0.get("protein_g") or nt.protein_g
        plan.target_carbs_g = b0.get("carbs_g") or nt.carbs_g
        plan.target_fat_g = b0.get("fat_g") or nt.fat_g
        plan.updated_at = datetime.now(UTC)
        self.db.commit()
        detail = self.get_plan(user_id, plan_id)
        return {"preview": preview_out, "plan": detail}

    def export_plan(
        self,
        user_id: str,
        plan_id: int,
        fmt: str,
        options: dict | None = None,
    ) -> Export:
        self._get_owned(user_id, plan_id)
        detail = self.get_plan(user_id, plan_id)
        return ExportService(self.db).export_daily_plan_detail(user_id, detail, fmt, options)

    def _add_days(self, plan_id: int, days: list[PlanDayIn]) -> None:
        seen_days: set[int] = set()
        for day_in in days:
            if day_in.day_number in seen_days:
                raise BadRequestError(f"Duplicate day_number: {day_in.day_number}")
            seen_days.add(day_in.day_number)
            day = UserDailyPlanDay(
                plan_id=plan_id,
                day_number=day_in.day_number,
                title_vi=day_in.title_vi,
                notes_vi=pack_day_notes(
                    meal_notes=day_in.meal_notes,
                    section_notes=day_in.section_notes,
                    free_text=day_in.notes_vi,
                    split_role=day_in.split_role,
                ),
                target_calories=day_in.target_calories,
                target_protein_g=day_in.target_protein_g,
                target_carbs_g=day_in.target_carbs_g,
                target_fat_g=day_in.target_fat_g,
            )
            self.db.add(day)
            self.db.flush()

            for idx, ex in enumerate(day_in.exercises):
                section = ex.section if ex.section in VALID_SECTIONS else "main"
                if not self.db.get(Exercise, ex.exercise_id):
                    raise BadRequestError(f"Unknown exercise_id: {ex.exercise_id}")
                self.db.add(
                    UserDailyPlanExercise(
                        plan_day_id=day.id,
                        exercise_id=ex.exercise_id,
                        sort_order=ex.sort_order if ex.sort_order is not None else idx,
                        sets=ex.sets,
                        reps=str(ex.reps) if ex.reps is not None else None,
                        rest_seconds=ex.rest_seconds,
                        section=section,
                        notes_vi=ex.notes_vi,
                    )
                )

            for idx, meal in enumerate(day_in.meals):
                meal_type = meal.meal_type if meal.meal_type in VALID_MEALS else "lunch"
                if not self.db.get(Food, meal.food_id):
                    raise BadRequestError(f"Unknown food_id: {meal.food_id}")
                self.db.add(
                    UserDailyPlanMeal(
                        plan_day_id=day.id,
                        meal_type=meal_type,
                        food_id=meal.food_id,
                        servings=meal.servings,
                        sort_order=meal.sort_order if meal.sort_order is not None else idx,
                        notes_vi=meal.notes_vi,
                    )
                )

    def _get_owned(self, user_id: str, plan_id: int) -> UserDailyPlan:
        plan = self.db.get(UserDailyPlan, plan_id)
        if not plan:
            raise NotFoundError("UserDailyPlan", plan_id)
        if str(plan.user_id) != str(user_id):
            raise ForbiddenError("Not your plan")
        return plan

    def _plan_summary_stats(self, plan_ids: list[int]) -> dict[int, tuple[int, int, int]]:
        """plan_id -> (day_count, exercise_count, meal_count)."""
        if not plan_ids:
            return {}
        day_counts = {
            int(pid): int(n)
            for pid, n in (
                self.db.query(UserDailyPlanDay.plan_id, func.count(UserDailyPlanDay.id))
                .filter(UserDailyPlanDay.plan_id.in_(plan_ids))
                .group_by(UserDailyPlanDay.plan_id)
                .all()
            )
        }
        ex_counts = {
            int(pid): int(n)
            for pid, n in (
                self.db.query(UserDailyPlanDay.plan_id, func.count(UserDailyPlanExercise.id))
                .join(
                    UserDailyPlanExercise,
                    UserDailyPlanExercise.plan_day_id == UserDailyPlanDay.id,
                )
                .filter(UserDailyPlanDay.plan_id.in_(plan_ids))
                .group_by(UserDailyPlanDay.plan_id)
                .all()
            )
        }
        meal_counts = {
            int(pid): int(n)
            for pid, n in (
                self.db.query(UserDailyPlanDay.plan_id, func.count(UserDailyPlanMeal.id))
                .join(
                    UserDailyPlanMeal,
                    UserDailyPlanMeal.plan_day_id == UserDailyPlanDay.id,
                )
                .filter(UserDailyPlanDay.plan_id.in_(plan_ids))
                .group_by(UserDailyPlanDay.plan_id)
                .all()
            )
        }
        return {
            pid: (
                day_counts.get(pid, 0),
                ex_counts.get(pid, 0),
                meal_counts.get(pid, 0),
            )
            for pid in plan_ids
        }

    def _summaries(self, plans: list[UserDailyPlan]) -> list[dict[str, Any]]:
        stats = self._plan_summary_stats([p.id for p in plans])
        return [self._summary(p, stats=stats.get(p.id, (0, 0, 0))) for p in plans]

    def _summary(
        self,
        plan: UserDailyPlan,
        *,
        stats: tuple[int, int, int] | None = None,
    ) -> dict[str, Any]:
        if stats is None:
            stats = self._plan_summary_stats([plan.id]).get(plan.id, (0, 0, 0))
        day_count, exercise_count, meal_count = stats
        token = getattr(plan, "share_token", None)
        is_guest = getattr(plan, "user_id", None) is None
        return {
            "id": plan.id,
            "title_vi": plan.title_vi,
            "description_vi": plan.description_vi,
            "source": plan.source,
            "target_calories": plan.target_calories,
            "target_protein_g": getattr(plan, "target_protein_g", None),
            "target_carbs_g": getattr(plan, "target_carbs_g", None),
            "target_fat_g": getattr(plan, "target_fat_g", None),
            "is_template": bool(getattr(plan, "is_template", False)),
            "start_date": plan.start_date,
            "end_date": plan.end_date,
            "ai_generation_id": getattr(plan, "ai_generation_id", None),
            "share_token": token,
            "share_url_path": f"/lich/{token}" if token else None,
            "day_count": day_count,
            "exercise_count": exercise_count,
            "meal_count": meal_count,
            "created_at": plan.created_at,
            "updated_at": plan.updated_at,
            "is_guest": is_guest,
            "challenge_100_days": bool(getattr(plan, "challenge_100_days", False)),
            "expires_at": guest_expires_at(plan) if is_guest else None,
            "days_left": guest_days_left(plan) if is_guest else None,
        }

    def _detail(self, plan: UserDailyPlan) -> dict[str, Any]:
        days = (
            self.db.query(UserDailyPlanDay)
            .filter(UserDailyPlanDay.plan_id == plan.id)
            .order_by(UserDailyPlanDay.day_number.asc())
            .all()
        )
        day_ids = [d.id for d in days]
        exercises_by_day: dict[int, list[UserDailyPlanExercise]] = {d.id: [] for d in days}
        meals_by_day: dict[int, list[UserDailyPlanMeal]] = {d.id: [] for d in days}
        if day_ids:
            for ex in (
                self.db.query(UserDailyPlanExercise)
                .filter(UserDailyPlanExercise.plan_day_id.in_(day_ids))
                .order_by(UserDailyPlanExercise.sort_order.asc())
                .all()
            ):
                exercises_by_day.setdefault(ex.plan_day_id, []).append(ex)
            for meal in (
                self.db.query(UserDailyPlanMeal)
                .filter(UserDailyPlanMeal.plan_day_id.in_(day_ids))
                .order_by(UserDailyPlanMeal.sort_order.asc())
                .all()
            ):
                meals_by_day.setdefault(meal.plan_day_id, []).append(meal)

        all_ex_ids = {
            ex.exercise_id
            for items in exercises_by_day.values()
            for ex in items
        }
        all_food_ids = {
            m.food_id for items in meals_by_day.values() for m in items
        }
        exercises_map: dict[int, Exercise] = {}
        if all_ex_ids:
            exercises_map = {
                e.id: e
                for e in self.db.query(Exercise).filter(Exercise.id.in_(all_ex_ids)).all()
            }
        mg_ids = {e.muscle_group_id for e in exercises_map.values() if e.muscle_group_id}
        mg_map: dict[int, MuscleGroup] = {}
        if mg_ids:
            mg_map = {
                m.id: m
                for m in self.db.query(MuscleGroup).filter(MuscleGroup.id.in_(mg_ids)).all()
            }
        foods_map: dict[int, Food] = {}
        if all_food_ids:
            foods_map = {
                f.id: f for f in self.db.query(Food).filter(Food.id.in_(all_food_ids)).all()
            }

        day_payload = []
        for day in days:
            exercises = exercises_by_day.get(day.id) or []
            meals = meals_by_day.get(day.id) or []
            ex_out = []
            for ex in exercises:
                exercise = exercises_map.get(ex.exercise_id)
                mg = mg_map.get(exercise.muscle_group_id) if exercise and exercise.muscle_group_id else None
                name_vi = (exercise.name_vi if exercise else None) or str(ex.exercise_id)
                steps = _as_instruction_steps(
                    getattr(exercise, "instruction_steps_vi", None) if exercise else None
                )
                instruction = getattr(exercise, "instruction_vi", None) if exercise else None
                if not steps and instruction:
                    steps = [instruction]
                ex_out.append(
                    {
                        "id": ex.id,
                        "exercise_id": ex.exercise_id,
                        "name_vi": name_vi,
                        "name_en": exercise.name_en if exercise else None,
                        "body_part": mg.slug if mg else None,
                        "gif_url": getattr(exercise, "gif_url", None) if exercise else None,
                        "image_url": getattr(exercise, "image_url", None) if exercise else None,
                        "video_url": getattr(exercise, "video_url", None) if exercise else None,
                        "instruction_vi": instruction,
                        "instruction_steps_vi": steps,
                        "section": getattr(ex, "section", None) or "main",
                        "sets": ex.sets,
                        "reps": ex.reps,
                        "rest_seconds": ex.rest_seconds,
                        "sort_order": ex.sort_order,
                        "notes_vi": ex.notes_vi,
                    }
                )
            meal_out = []
            for meal in meals:
                food = foods_map.get(meal.food_id)
                servings = float(meal.servings or 1)
                cal = int(round((food.calories or 0) * servings)) if food else 0
                meal_out.append(
                    {
                        "id": meal.id,
                        "food_id": meal.food_id,
                        "name_vi": food.name_vi if food else f"#{meal.food_id}",
                        "meal_type": meal.meal_type,
                        "servings": servings,
                        "calories": cal,
                        "protein_g": (food.protein_g * servings) if food and food.protein_g is not None else None,
                        "carbs_g": (food.carbs_g * servings) if food and food.carbs_g is not None else None,
                        "fat_g": (food.fat_g * servings) if food and food.fat_g is not None else None,
                        "serving_size": food.serving_size if food else None,
                        "serving_grams": food.serving_grams if food else None,
                        "sort_order": meal.sort_order,
                        "notes_vi": meal.notes_vi,
                    }
                )
            meal_notes, section_notes, free_text, split_role = unpack_day_notes(day.notes_vi)
            day_payload.append(
                {
                    "id": day.id,
                    "day_number": day.day_number,
                    "title_vi": day.title_vi,
                    "notes_vi": free_text,
                    "split_role": split_role,
                    "meal_notes": meal_notes,
                    "section_notes": section_notes,
                    "target_calories": getattr(day, "target_calories", None),
                    "target_protein_g": getattr(day, "target_protein_g", None),
                    "target_carbs_g": getattr(day, "target_carbs_g", None),
                    "target_fat_g": getattr(day, "target_fat_g", None),
                    "exercises": ex_out,
                    "meals": meal_out,
                }
            )

        summary = self._summary(plan)
        summary["days"] = day_payload
        summary["insights"] = self._resolve_insights(plan)
        return summary

    def _resolve_insights(self, plan: UserDailyPlan) -> dict[str, Any] | None:
        """Return stored AI insights only (no rebuild from AiGeneration)."""
        if plan.source != "ai":
            return None
        raw = getattr(plan, "insights_json", None)
        if not raw or not isinstance(raw, dict):
            return None
        if RESTORE_SNAPSHOT_KEY in raw:
            raw = {k: v for k, v in raw.items() if k != RESTORE_SNAPSHOT_KEY}
        # Normalize hybrid / partial blobs so PlanDetailOut response_model always validates.
        if "overview" not in raw or not isinstance(raw.get("overview"), dict):
            bits = []
            if raw.get("frame_code"):
                bits.append(f"Frame `{raw['frame_code']}`")
            if raw.get("session_minutes"):
                bits.append(f"{raw['session_minutes']} phút/buổi")
            if raw.get("generator"):
                bits.append(str(raw["generator"]))
            raw = {
                **raw,
                "overview": {
                    "summary_vi": " · ".join(bits) if bits else "Lịch AI TAPTOT",
                    "schedule_vi": bits[0] if bits else None,
                    "nutrition_vi": None,
                    "periodization_vi": None,
                },
                "advice_vi": list(raw.get("advice_vi") or []),
                "days": list(raw.get("days") or []),
            }
        return raw

    def save_as_template(self, user_id: str, plan_id: int, title_vi: str | None = None) -> dict[str, Any]:
        """Clone an owned plan into a reusable template (is_template=True)."""
        source = self._get_owned(user_id, plan_id)
        detail = self._detail(source)
        days_in: list[PlanDayIn] = []
        from app.schemas.plans import PlanExerciseIn, PlanMealIn

        for day in detail["days"]:
            days_in.append(
                PlanDayIn(
                    day_number=day["day_number"],
                    title_vi=day.get("title_vi"),
                    notes_vi=day.get("notes_vi"),
                    split_role=day.get("split_role"),
                    meal_notes=day.get("meal_notes") or {},
                    section_notes=day.get("section_notes") or {},
                    exercises=[
                        PlanExerciseIn(
                            exercise_id=ex["exercise_id"],
                            sets=ex["sets"],
                            reps=ex.get("reps"),
                            rest_seconds=_resolve_import_rest_seconds(ex),
                            section=ex.get("section") or "main",
                            notes_vi=ex.get("notes_vi"),
                            sort_order=ex.get("sort_order"),
                        )
                        for ex in day.get("exercises") or []
                    ],
                    meals=[
                        PlanMealIn(
                            food_id=m["food_id"],
                            meal_type=m.get("meal_type") or "lunch",
                            servings=m.get("servings") or 1,
                            notes_vi=m.get("notes_vi"),
                            sort_order=m.get("sort_order"),
                        )
                        for m in day.get("meals") or []
                    ],
                )
            )
        req = CreatePlanRequest(
            title_vi=(title_vi or f"Mẫu — {source.title_vi}").strip()[:255],
            description_vi=source.description_vi,
            target_calories=source.target_calories,
            target_protein_g=getattr(source, "target_protein_g", None),
            target_carbs_g=getattr(source, "target_carbs_g", None),
            target_fat_g=getattr(source, "target_fat_g", None),
            source="template",
            is_template=True,
            days=days_in,
        )
        return self.create_plan(user_id, req)

    def list_templates(self, user_id: str) -> list[dict[str, Any]]:
        plans = (
            self.db.query(UserDailyPlan)
            .filter(UserDailyPlan.user_id == user_id, UserDailyPlan.is_template.is_(True))
            .order_by(UserDailyPlan.updated_at.desc())
            .all()
        )
        return self._summaries(plans)
