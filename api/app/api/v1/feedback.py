from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user
from app.core.exceptions import BadRequestError
from app.models.entities import FeedbackSuggestion, TrainerContactRequest

router = APIRouter(tags=["Feedback"])

VALID_FEEDBACK_CATEGORIES = frozenset({"food", "exercise", "other"})


class FeedbackIn(BaseModel):
    category: str = Field(description="food | exercise | other")
    title: str = Field(min_length=2, max_length=200)
    content: str = Field(min_length=5, max_length=4000)


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


@router.post("/feedback", response_model=FeedbackOut, status_code=201)
def create_feedback(
    payload: FeedbackIn,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FeedbackOut:
    category = (payload.category or "").strip().lower()
    if category not in VALID_FEEDBACK_CATEGORIES:
        raise BadRequestError("category phải là food, exercise hoặc other")
    row = FeedbackSuggestion(
        user_id=user.id,
        category=category,
        title=payload.title.strip(),
        content=payload.content.strip(),
        created_at=datetime.now(UTC),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
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
