"""Restore AI plan snapshot: owner, missing snapshot, other user."""

from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.exceptions import ForbiddenError, NotFoundError
from app.models.base import Base
from app.models.entities import (
    Exercise,
    MuscleGroup,
    User,
    UserDailyPlan,
    UserDailyPlanDay,
    UserDailyPlanExercise,
)
from app.schemas.plans import (
    CreatePlanRequest,
    PlanDayIn,
    PlanExerciseIn,
    UpdatePlanContentRequest,
    UpdatePlanDayIn,
    UpdatePlanExerciseIn,
)
from app.services.plan_service import PlanService

USER_A = "11111111-1111-1111-1111-111111111111"
USER_B = "22222222-2222-2222-2222-222222222222"


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    now = datetime.now(UTC)
    db.add(User(id=USER_A, email="a@test.com", password_hash="x", display_name="A", role="user", created_at=now))
    db.add(User(id=USER_B, email="b@test.com", password_hash="x", display_name="B", role="user", created_at=now))
    db.add(MuscleGroup(slug="nguc", name_vi="Ngực", sort_order=1))
    db.commit()
    group = db.query(MuscleGroup).first()
    db.add(
        Exercise(
            name_vi="Chống đẩy",
            name_en="Push-up",
            muscle_group_id=group.id,
            exercise_type="main",
            difficulty=1,
            secondary_muscles=[],
            is_active=True,
            created_at=now,
            updated_at=now,
        )
    )
    db.add(
        Exercise(
            name_vi="Plank",
            name_en="Plank",
            muscle_group_id=group.id,
            exercise_type="main",
            difficulty=1,
            secondary_muscles=[],
            is_active=True,
            created_at=now,
            updated_at=now,
        )
    )
    db.commit()
    return db


def _create_ai_plan(db: Session, user_id: str, exercise_id: int) -> dict:
    payload = CreatePlanRequest(
        title_vi="Lịch AI",
        source="ai",
        days=[
            PlanDayIn(
                day_number=1,
                title_vi="Push",
                exercises=[
                    PlanExerciseIn(exercise_id=exercise_id, sets=3, reps="10", rest_seconds=60)
                ],
            )
        ],
    )
    return PlanService(db).create_plan(user_id, payload, insights_json={"overview": {"summary_vi": "x"}})


def test_restore_ai_replaces_edited_exercises():
    db = _session()
    pushup, plank = db.query(Exercise).order_by(Exercise.id.asc()).all()
    detail = _create_ai_plan(db, USER_A, pushup.id)
    assert detail.get("ai_generation_id")
    PlanService(db).update_plan_content(
        USER_A,
        detail["id"],
        UpdatePlanContentRequest(
            days=[
                UpdatePlanDayIn(
                    day_number=1,
                    exercises=[
                        UpdatePlanExerciseIn(exercise_id=plank.id, sets=5, reps="20", rest_seconds=30)
                    ],
                )
            ]
        ),
    )
    restored = PlanService(db).restore_ai(USER_A, detail["id"])
    assert restored["days"][0]["exercises"][0]["exercise_id"] == pushup.id
    assert restored["days"][0]["exercises"][0]["sets"] == 3
    assert "restore_snapshot" not in (restored.get("insights") or {})


def test_restore_ai_missing_snapshot():
    db = _session()
    now = datetime.now(UTC)
    plan = UserDailyPlan(
        user_id=USER_A,
        title_vi="Thủ công",
        source="manual",
        is_template=False,
        challenge_100_days=False,
        created_at=now,
        updated_at=now,
    )
    db.add(plan)
    db.flush()
    db.add(UserDailyPlanDay(plan_id=plan.id, day_number=1, title_vi="A"))
    db.commit()
    with pytest.raises(NotFoundError):
        PlanService(db).restore_ai(USER_A, plan.id)


def test_restore_ai_other_user_forbidden():
    db = _session()
    pushup = db.query(Exercise).order_by(Exercise.id.asc()).first()
    detail = _create_ai_plan(db, USER_A, pushup.id)
    with pytest.raises(ForbiddenError):
        PlanService(db).restore_ai(USER_B, detail["id"])
