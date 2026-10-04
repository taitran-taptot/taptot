"""Manual plan exercise cues: RIR, RPE, tempo, drop/super-set."""

from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models.base import Base
from app.models.entities import Exercise, MuscleGroup, User
from app.schemas.plans import (
    CreatePlanRequest,
    PlanDayIn,
    UpdatePlanContentRequest,
    UpdatePlanDayIn,
    UpdatePlanExerciseIn,
)
from app.services.plan_service import PlanService

USER_A = "11111111-1111-1111-1111-111111111111"


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    now = datetime.now(UTC)
    db.add(User(id=USER_A, email="a@test.com", password_hash="x", display_name="A", role="hlv", created_at=now))
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


def test_manual_plan_round_trips_cues_and_superset():
    db = _session()
    pushup, plank = db.query(Exercise).order_by(Exercise.id.asc()).all()
    created = PlanService(db).create_plan(
        USER_A,
        CreatePlanRequest(
            title_vi="Manual cues",
            source="manual",
            days=[PlanDayIn(day_number=1, title_vi="Push", exercises=[], meals=[])],
        ),
    )
    updated = PlanService(db).update_plan_content(
        USER_A,
        created["id"],
        UpdatePlanContentRequest(
            days=[
                UpdatePlanDayIn(
                    day_number=1,
                    exercises=[
                        UpdatePlanExerciseIn(
                            exercise_id=pushup.id,
                            sets=3,
                            reps="10",
                            rest_seconds=60,
                            rir=2,
                            rpe=8,
                            tempo="3-1-1-0",
                            technique="super_set",
                            superset_group=1,
                        ),
                        UpdatePlanExerciseIn(
                            exercise_id=plank.id,
                            sets=3,
                            reps="12",
                            rest_seconds=0,
                            technique="super_set",
                            superset_group=1,
                        ),
                    ],
                )
            ]
        ),
    )
    pair = updated["days"][0]["exercises"]
    assert pair[0]["rir"] == 2
    assert pair[0]["rpe"] == 8
    assert pair[0]["tempo"] == "3-1-1-0"
    assert pair[0]["technique"] == "super_set"
    assert pair[0]["superset_group"] == 1
    assert pair[1]["technique"] == "super_set"
    assert pair[1]["superset_group"] == 1

    dropped = PlanService(db).update_plan_content(
        USER_A,
        created["id"],
        UpdatePlanContentRequest(
            days=[
                UpdatePlanDayIn(
                    day_number=1,
                    exercises=[
                        UpdatePlanExerciseIn(
                            exercise_id=pushup.id,
                            sets=3,
                            reps="8",
                            rest_seconds=90,
                            technique="drop_set",
                            superset_group=1,
                        )
                    ],
                )
            ]
        ),
    )
    row = dropped["days"][0]["exercises"][0]
    assert row["technique"] == "drop_set"
    assert row["superset_group"] is None


def test_set_prescriptions_round_trip_and_summary():
    db = _session()
    pushup = db.query(Exercise).order_by(Exercise.id.asc()).first()
    created = PlanService(db).create_plan(
        USER_A,
        CreatePlanRequest(
            title_vi="Per set",
            source="ai",
            days=[PlanDayIn(day_number=1, title_vi="Push", exercises=[], meals=[])],
        ),
    )
    updated = PlanService(db).update_plan_content(
        USER_A,
        created["id"],
        UpdatePlanContentRequest(
            days=[
                UpdatePlanDayIn(
                    day_number=1,
                    exercises=[
                        UpdatePlanExerciseIn(
                            exercise_id=pushup.id,
                            sets=2,
                            reps="12",
                            rest_seconds=90,
                            technique="super_set",
                            superset_group=1,
                            set_prescriptions=[
                                {
                                    "reps": "12",
                                    "rest_seconds": 90,
                                    "rir": 2,
                                    "rpe": 8,
                                    "tempo": "3-1-1-0",
                                    "technique": None,
                                },
                                {
                                    "reps": "8",
                                    "rest_seconds": 120,
                                    "rir": 1,
                                    "rpe": 9.5,
                                    "technique": "drop_set",
                                },
                            ],
                        )
                    ],
                )
            ]
        ),
    )
    row = updated["days"][0]["exercises"][0]
    assert row["sets"] == 2
    assert row["reps"] == "12"
    assert row["rest_seconds"] == 90
    assert row["rir"] == 2
    assert row["rpe"] == 8
    assert row["technique"] == "super_set"
    assert row["superset_group"] == 1
    assert row["set_prescriptions"][1]["reps"] == "8"
    assert row["set_prescriptions"][1]["technique"] == "drop_set"
    assert row["set_prescriptions"][1]["rpe"] == 9.5

    collapsed = PlanService(db).update_plan_content(
        USER_A,
        created["id"],
        UpdatePlanContentRequest(
            days=[
                UpdatePlanDayIn(
                    day_number=1,
                    exercises=[
                        UpdatePlanExerciseIn(
                            exercise_id=pushup.id,
                            sets=2,
                            reps="12",
                            rest_seconds=90,
                            rir=2,
                            rpe=8,
                            set_prescriptions=None,
                        )
                    ],
                )
            ]
        ),
    )
    gone = collapsed["days"][0]["exercises"][0]
    assert gone["set_prescriptions"] is None
    assert gone["rir"] == 2
