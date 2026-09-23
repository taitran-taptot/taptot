from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user_optional
from app.core.exceptions import BadRequestError
from app.models.entities import FeedbackSuggestion, TrainerContactRequest
from app.services.feedback_sheets import append_feedback_row

router = APIRouter(tags=["Feedback"])

CATEGORY_LABELS = {
    "equipment": "Dụng cụ",
    "workout_plan": "Lịch tập",
    "meal_plan": "Lịch ăn",
    "food_catalog": "Kho thực phẩm",
    "exercise_catalog": "Kho bài tập",
    "knowledge": "Kho kiến thức",
    "trainer": "Huấn luyện viên",
    "other": "Khác",
    "food": "Kho thực phẩm",
    "exercise": "Kho bài tập",
}
VALID_FEEDBACK_CATEGORIES = frozenset(CATEGORY_LABELS)
PLAN_URL_CATEGORIES = frozenset({"workout_plan", "meal_plan"})


class FeedbackIn(BaseModel):
    category: str
    title: str | None = Field(default=None, max_length=200)
    content: str = Field(min_length=5, max_length=4000)
    plan_url: str | None = Field(default=None, max_length=500)


class FeedbackOut(BaseModel):
    id: int
    category: str
    title: str
    message: str = "Đã gửi góp ý. Cảm ơn bạn!"


class TrainerContactIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    phone_zalo: str = Field(min_length=8, max_length=30)
    email: EmailStr | None = None
    age: int | None = Field(default=None, ge=10, le=100)
    message: str | None = Field(default=None, max_length=2000)


class TrainerContactOut(BaseModel):
    id: int
    message: str = "Đã gửi yêu cầu. Chúng tôi sẽ liên hệ lại sớm!"


def prepare_feedback(
    category: str,
    content: str,
    plan_url: str | None = None,
    title: str | None = None,
) -> dict[str, str | None]:
    cat = (category or "").strip().lower()
    if cat not in VALID_FEEDBACK_CATEGORIES:
        raise BadRequestError("Chủ đề góp ý không hợp lệ.")
    text = (content or "").strip()
    if len(text) < 5:
        raise BadRequestError("Nội dung góp ý quá ngắn.")
    link = (plan_url or "").strip() or None
    if cat in PLAN_URL_CATEGORIES and not link:
        raise BadRequestError("Hãy dán link lịch khi góp ý về lịch tập hoặc lịch ăn.")
    label = (title or "").strip() or CATEGORY_LABELS[cat]
    return {"category": cat, "title": label, "content": text, "plan_url": link}


@router.post("/feedback", response_model=FeedbackOut, status_code=201)
def create_feedback(
    payload: FeedbackIn,
    user: CurrentUser | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
) -> FeedbackOut:
    prepared = prepare_feedback(payload.category, payload.content, payload.plan_url, payload.title)
    now = datetime.now(UTC)
    row = FeedbackSuggestion(
        user_id=user.id if user else None,
        category=prepared["category"],
        title=prepared["title"],
        content=prepared["content"],
        plan_url=prepared["plan_url"],
        created_at=now,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    append_feedback_row(
        email=(user.email if user else "") or "",
        category_label=str(prepared["title"]),
        content=str(prepared["content"]),
        plan_url=prepared["plan_url"],
        time_iso=now.isoformat(timespec="seconds"),
    )
    return FeedbackOut(id=row.id, category=row.category, title=row.title)


@router.post("/contact/trainer", response_model=TrainerContactOut, status_code=201)
def create_trainer_contact(
    payload: TrainerContactIn,
    db: Session = Depends(get_db),
) -> TrainerContactOut:
    row = TrainerContactRequest(
        full_name=payload.full_name.strip(),
        age=payload.age if payload.age is not None else 0,
        phone_zalo=payload.phone_zalo.strip(),
        email=str(payload.email).strip().lower() if payload.email else "",
        message=(payload.message or "").strip() or None,
        created_at=datetime.now(UTC),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return TrainerContactOut(id=row.id)
