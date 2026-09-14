"""AI workout schedule generation routes."""

from __future__ import annotations

import json
import logging
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import SessionLocal, get_db
from app.core.deps import CurrentUser, get_current_user, get_current_user_optional
from app.core.exceptions import AppException, BadRequestError, ConflictError, ForbiddenError
from app.services.ai_chat.agent import history_for_client, run_chat_events
from app.services.workout_generation import generate_workout
from app.services.workout_generation.session_policy import CHALLENGE_WEEKS, MAX_WEEKS
from app.services.redeem_code_service import RedeemCodeService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ai", tags=["AI"])


class FitnessBaselineIn(BaseModel):
    pushups_max: int | None = None
    pullups_max: int | None = None
    plank_seconds: int | None = None
    squats_max: int | None = None


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
    redeem_code: str | None = Field(default=None, max_length=32)

    @model_validator(mode="after")
    def _duration_vs_challenge(self):
        mode = (self.generation_mode or "").strip().lower()
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
            return self
        self.foundation_motive = None
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


@router.post("/generate-workout-schedule")
def generate_workout_schedule(
    body: WorkoutScheduleRequest,
    db: Session = Depends(get_db),
    user: CurrentUser | None = Depends(get_current_user_optional),
) -> dict[str, Any]:
    settings = get_settings()
    user_id = user.id if user else None
    redeem_service = RedeemCodeService(db)
    free_home = (body.generation_mode or "").strip().lower() == "free_home"
    require_code = bool(settings.require_redeem_code_for_generate) and not free_home
    reservation_token: str | None = None
    if require_code:
        reservation_token = redeem_service.reserve(body.redeem_code)
        if not reservation_token:
            raise ForbiddenError(
                "Cần mã TAPTOT hợp lệ và chưa sử dụng để tạo lịch."
            )
    elif body.redeem_code and not free_home:
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


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    conversation_id: str | None = Field(default=None, max_length=64)


def _sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.get("/chat/history")
def chat_history(
    conversation_id: str | None = None,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return history_for_client(db, user.id, conversation_id)


@router.post("/chat")
def ai_chat(
    body: ChatRequest,
    user: CurrentUser = Depends(get_current_user),
) -> StreamingResponse:
    def gen():
        db = SessionLocal()
        try:
            for ev in run_chat_events(db, user.id, body.message, body.conversation_id):
                name = str(ev.get("event") or "message")
                payload = ev.get("data")
                if not isinstance(payload, dict):
                    payload = {k: v for k, v in ev.items() if k != "event"}
                yield _sse(name, payload)
        except Exception:
            logger.exception("ai chat stream failed user=%s", user.id)
            yield _sse("error", {"message": "Có lỗi khi trả lời. Thử lại giúp mình."})
        finally:
            db.close()

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
