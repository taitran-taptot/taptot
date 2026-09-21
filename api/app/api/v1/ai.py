"""AI workout schedule generation routes."""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user_optional
from app.core.exceptions import AppException, BadRequestError, ConflictError, ForbiddenError
from app.services.workout_generation import generate_workout
from app.services.workout_generation.familiarization_curriculum import (
    FIRST_PUSH_PULL_SESSIONS_PER_WEEK,
    FIRST_PUSH_PULL_WEEKS,
)
from app.services.workout_generation.fitness_standards import (
    familiarization_catalog,
    normalize_familiarization_path,
)
from app.services.workout_generation.fitness_test_advice import build_fitness_test_advice
from app.services.workout_generation.session_policy import CHALLENGE_WEEKS, MAX_WEEKS
from app.services.redeem_code_service import RedeemCodeService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ai", tags=["AI"])


class FitnessBaselineIn(BaseModel):
    pushups_max: int | None = Field(default=None, ge=0, le=1000)
    pushup_variant: str | None = Field(default=None, max_length=24)
    pullups_max: int | None = Field(default=None, ge=0, le=1000)
    pull_test_variant: str | None = Field(default=None, max_length=24)
    pull_hold_seconds: int | None = Field(default=None, ge=0, le=3600)
    inverted_rows_max: int | None = Field(default=None, ge=0, le=1000)
    plank_seconds: int | None = Field(default=None, ge=0, le=3600)
    squats_max: int | None = Field(default=None, ge=0, le=5000)
    run_10min_meters: int | None = Field(default=None, ge=0, le=10000)


class WorkoutScheduleRequest(BaseModel):
    goal: str = "maintain"
    gender: str = "male"
    age: int = Field(ge=16, le=150)
    height_cm: float = Field(ge=50, le=250)
    weight_kg: float = Field(ge=20, le=400)
    activity: str = "moderate"
    sessions_per_week: int = Field(ge=2, le=7, default=3)
    session_minutes: int = Field(ge=30, le=90, default=45)
    location: str = "home"
    focus_areas: list[str] = Field(default_factory=list)
    extra_goals: list[str] = Field(default_factory=list)
    equipment_list: list[str] = Field(default_factory=list)
    food_ids: list[int] = Field(default_factory=list)
    experience_level: int = Field(default=1, ge=1, le=5)
    ai_suggest_equipment: bool = False
    no_equipment: bool = False
    ai_suggest_foods: bool = False
    fitness_baseline: FitnessBaselineIn | None = None
    health_note: str | None = None
    duration_weeks: int = Field(default=4, ge=4, le=14)
    kg_per_week: float | None = Field(default=None, ge=0.1, le=1.5)
    # Thử thách 100 ngày (14 tuần, 3 pha).
    challenge_100_days: bool = False
    # Alias cũ — map sang challenge_100_days.
    curriculum_12_weeks: bool = False
    # free_home = nền thể lực tại nhà (8 tuần, 2 giai đoạn, BW, deterministic, không meal).
    generation_mode: str | None = Field(default=None, max_length=32)
    foundation_motive: str | None = Field(default=None, max_length=32)
    familiarization_path: str | None = Field(default=None, max_length=32)
    # ISO weekday 1=Mon … 7=Sun; used by familiarization day titles.
    preferred_weekdays: list[int] = Field(default_factory=list)
    preferred_start_time: str | None = Field(default=None, max_length=8)
    redeem_code: str | None = Field(default=None, max_length=32)

    @model_validator(mode="after")
    def _duration_vs_challenge(self):
        mode = (self.generation_mode or "").strip().lower()
        if mode == "familiarization":
            self.generation_mode = "familiarization"
            self.familiarization_path = normalize_familiarization_path(
                self.familiarization_path
            )
            self.challenge_100_days = False
            self.curriculum_12_weeks = False
            self.location = "home"
            self.duration_weeks = FIRST_PUSH_PULL_WEEKS
            self.sessions_per_week = FIRST_PUSH_PULL_SESSIONS_PER_WEEK
            self.session_minutes = 45
            if self.familiarization_path == "first_push_pull":
                self.no_equipment = True
                self.equipment_list = []
            else:
                self.no_equipment = False
                self.equipment_list = ["pull-up-bar"]
            self.ai_suggest_equipment = False
            self.ai_suggest_foods = False
            self.foundation_motive = None
            cleaned: list[int] = []
            for day in self.preferred_weekdays or []:
                try:
                    value = int(day)
                except (TypeError, ValueError):
                    continue
                if 1 <= value <= 7 and value not in cleaned:
                    cleaned.append(value)
            self.preferred_weekdays = cleaned
            time_text = (self.preferred_start_time or "").strip()
            self.preferred_start_time = time_text or "18:00"
            return self
        if mode in {"fitness_advanced", "fitness_soldier"}:
            self.generation_mode = "fitness_advanced"
            self.challenge_100_days = False
            self.curriculum_12_weeks = False
            self.duration_weeks = 12
            self.session_minutes = 55
            if self.sessions_per_week < 4 or self.sessions_per_week > 6:
                raise ValueError(
                    "Thử thách thể lực nâng cao chỉ nhận 4–6 buổi mỗi tuần."
                )
            self.no_equipment = False
            slugs = [str(s).strip() for s in (self.equipment_list or []) if str(s).strip()]
            if "pull-up-bar" not in slugs:
                slugs.append("pull-up-bar")
            self.equipment_list = slugs
            self.ai_suggest_equipment = False
            self.foundation_motive = None
            self.familiarization_path = None
            return self
        if mode == "free_home":
            self.generation_mode = "free_home"
            self.challenge_100_days = False
            self.curriculum_12_weeks = False
            self.duration_weeks = 8
            self.location = "home"
            self.no_equipment = True
            self.equipment_list = []
            self.ai_suggest_equipment = False
            self.food_ids = []
            self.ai_suggest_foods = False
            motive = (self.foundation_motive or "").strip().lower()
            if motive not in {"daily_energy", "build_habit", "body_confidence"}:
                motive = "build_habit"
            self.foundation_motive = motive
            self.familiarization_path = None
            self.preferred_weekdays = []
            self.preferred_start_time = None
            return self
        self.foundation_motive = None
        self.familiarization_path = None
        self.preferred_weekdays = []
        self.preferred_start_time = None
        self.generation_mode = mode or None
        if self.challenge_100_days or self.curriculum_12_weeks:
            self.challenge_100_days = True
            self.curriculum_12_weeks = False
            self.duration_weeks = CHALLENGE_WEEKS
        elif self.duration_weeks > MAX_WEEKS:
            self.duration_weeks = MAX_WEEKS
        return self


def _usage_payload() -> dict[str, Any]:
    settings = get_settings()
    return {
        "month": date.today().strftime("%Y-%m"),
        "generation_count": 0,
        "qa_message_count": 0,
        "limit": None,
        "remaining": None,
        "unlimited": True,
        "price_vnd": 0,
        "model": settings.openai_model,
        "openai_configured": bool((settings.openai_api_key or "").strip()),
    }


@router.get("/usage")
def ai_usage() -> dict[str, Any]:
    """Public usage stub — guests can load the AI builder without auth."""
    return _usage_payload()


@router.get("/familiarization-catalog")
def get_familiarization_catalog() -> dict[str, Any]:
    """Public, deterministic programme metadata for the builder."""
    return familiarization_catalog()


class FitnessTestAdviceRequest(BaseModel):
    gender: str = "male"
    offer: str = "challenge_100"
    fitness_baseline: FitnessBaselineIn | None = None
    stretch_completed: bool = True
    feeling: str | None = Field(default=None, max_length=2000)


@router.post("/fitness-test/advice")
def fitness_test_advice(body: FitnessTestAdviceRequest) -> dict[str, Any]:
    """Compare a live test against package standards and return coach copy."""
    baseline = body.fitness_baseline.model_dump() if body.fitness_baseline else {}
    return build_fitness_test_advice(
        gender=body.gender,
        offer=body.offer,
        fitness_baseline=baseline,
        stretch_completed=body.stretch_completed,
        feeling=body.feeling,
    )


@router.post("/generate-workout-schedule")
def generate_workout_schedule(
    body: WorkoutScheduleRequest,
    db: Session = Depends(get_db),
    user: CurrentUser | None = Depends(get_current_user_optional),
) -> dict[str, Any]:
    settings = get_settings()
    user_id = user.id if user else None
    redeem_service = RedeemCodeService(db)
    free_mode = (body.generation_mode or "").strip().lower() in {
        "free_home",
        "familiarization",
        "fitness_advanced",
        "fitness_soldier",
    }
    require_code = bool(settings.require_redeem_code_for_generate) and not free_mode
    reservation_token: str | None = None
    if require_code:
        reservation_token = redeem_service.reserve(body.redeem_code)
        if not reservation_token:
            raise ForbiddenError(
                "Cần mã TAPTOT hợp lệ và chưa sử dụng để tạo lịch."
            )
    elif body.redeem_code and not free_mode:
        reservation_token = redeem_service.reserve(body.redeem_code)

    payload = body.model_dump()
    payload.pop("redeem_code", None)
    try:
        result = generate_workout(db, user_id, payload)
    except AppException:
        db.rollback()
        if reservation_token:
            redeem_service.release(body.redeem_code, reservation_token)
        raise
    except Exception as exc:
        db.rollback()
        if reservation_token:
            redeem_service.release(body.redeem_code, reservation_token)
        logger.exception("generate-workout-schedule failed for user=%s: %s", user_id, exc)
        raise BadRequestError(
            "Không tạo được lịch tập lúc này. Vui lòng thử lại sau vài giây."
        ) from exc

    plan_id = result.get("plan_id")
    code_applied = False
    if reservation_token:
        if not plan_id:
            redeem_service.release(body.redeem_code, reservation_token)
            raise BadRequestError("Không tạo được lịch để áp dụng mã TAPTOT.")
        applied = redeem_service.complete(
            body.redeem_code,
            reservation_token,
            plan_id=int(plan_id),
            user_id=user_id,
        )
        if not applied:
            raise ConflictError(
                "Không thể hoàn tất mã TAPTOT cho lịch này. Vui lòng liên hệ hỗ trợ."
            )
        code_applied = True

    # Always attach fresh usage stub
    result["usage"] = _usage_payload()
    result["code_applied"] = code_applied
    # FE only needs token + ids; strip heavy nested detail to keep response snappy.
    plan = result.get("plan")
    if isinstance(plan, dict):
        result["plan"] = {
            "id": plan.get("id"),
            "title_vi": plan.get("title_vi"),
            "source": plan.get("source"),
            "share_token": plan.get("share_token"),
        }
    return result
