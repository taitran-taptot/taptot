from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base
from app.models.entities import (
    AiGeneration,
    Equipment,
    Export,
    Food,
    FoodCategory,
    MuscleGroup,
    User,
    UserDailyPlan,
    UserDailyPlanDay,
    UserDailyPlanExercise,
    UserDailyPlanMeal,
)
from scripts.wipe_dev_generated_plans import (
    WipeBlockedError,
    assert_wipe_allowed,
    is_local_database_url,
    wipe_generated_plans,
)


def test_local_url_detection():
    assert is_local_database_url("sqlite:///:memory:")
    assert is_local_database_url("postgresql+psycopg://postgres:x@localhost:5432/taptot")
    assert is_local_database_url("postgresql+psycopg://postgres:x@127.0.0.1/taptot")
    assert not is_local_database_url(
        "postgresql+psycopg://postgres:x@db.example.com:5432/taptot"
    )


def test_assert_wipe_blocks_production_even_on_localhost():
    with pytest.raises(WipeBlockedError, match="production"):
        assert_wipe_allowed(
            "production",
            "postgresql+psycopg://postgres:x@localhost:5432/taptot",
        )


def test_assert_wipe_blocks_remote_without_flag():
    with pytest.raises(WipeBlockedError, match="localhost"):
        assert_wipe_allowed(
            "development",
            "postgresql+psycopg://postgres:x@db.example.com:5432/taptot",
        )


def test_assert_wipe_allows_remote_non_prod_with_flag():
    assert_wipe_allowed(
        "development",
        "postgresql+psycopg://postgres:x@db.example.com:5432/taptot",
        allow_remote=True,
    )


def _session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _fk(dbapi_connection, _record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _seed(db):
    now = datetime.now(UTC)
    user_id = str(uuid4())
    db.add(
        User(
            id=user_id,
            email="dev@test.com",
            password_hash="x",
            display_name="Dev",
            role="user",
            created_at=now,
        )
    )
    mg = MuscleGroup(slug="chest", name_vi="Ngực", sort_order=0)
    cat = FoodCategory(slug="protein", name_vi="Đạm", sort_order=0)
    eq = Equipment(slug="barbell", name_vi="Tạ đòn", is_active=True, sort_order=0)
    db.add_all([mg, cat, eq])
    db.flush()
    food = Food(
        slug="ga",
        name_vi="Gà",
        serving_size="100g",
        calories=100,
        protein_g=20,
        carbs_g=0,
        fat_g=2,
        tags=[],
        created_at=now,
        category_id=cat.id,
    )
    db.add(food)
    db.flush()
    gen = AiGeneration(
        user_id=user_id,
        generation_type="workout_schedule",
        input_params={},
        output_data={"days": []},
        created_at=now,
    )
    db.add(gen)
    db.flush()
    plan = UserDailyPlan(
        user_id=user_id,
        title_vi="Lịch test",
        source="ai",
        ai_generation_id=gen.id,
        created_at=now,
        updated_at=now,
    )
    db.add(plan)
    db.flush()
    day = UserDailyPlanDay(plan_id=plan.id, day_number=1, title_vi="Ngày 1")
    db.add(day)
    db.flush()
    from app.models.entities import Exercise

    ex = Exercise(
        name_vi="Bench",
        muscle_group_id=mg.id,
        exercise_type="main",
        difficulty=2,
        secondary_muscles=[],
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    db.add(ex)
    db.flush()
    db.add(
        UserDailyPlanExercise(
            plan_day_id=day.id,
            exercise_id=ex.id,
            sort_order=0,
            sets=3,
            reps="8",
            rest_seconds=60,
            section="main",
        )
    )
    db.add(
        UserDailyPlanMeal(
            plan_day_id=day.id,
            meal_type="lunch",
            food_id=food.id,
            servings=1,
            sort_order=0,
        )
    )
    db.add(
        Export(
            user_id=user_id,
            export_type="daily_plan",
            source_id=plan.id,
            format="json",
            template_id="default",
            created_at=now,
        )
    )
    db.commit()
    return user_id, mg.id, cat.id, eq.id, food.id, ex.id


def test_dry_run_does_not_delete():
    db = _session()
    _seed(db)
    result = wipe_generated_plans(db, execute=False)
    assert result["dry_run"] is True
    assert result["before"]["user_daily_plans"] == 1
    assert result["after"]["user_daily_plans"] == 1
    assert db.query(UserDailyPlan).count() == 1
    assert db.query(AiGeneration).count() == 1
    assert db.query(Food).count() == 1
    assert db.query(MuscleGroup).count() == 1


def test_execute_wipes_plans_keeps_catalog():
    db = _session()
    user_id, mg_id, cat_id, eq_id, food_id, ex_id = _seed(db)
    result = wipe_generated_plans(db, execute=True)
    assert result["dry_run"] is False
    assert result["deleted"]["user_daily_plans"] == 1
    assert result["deleted"]["ai_generations"] == 1
    assert result["after"]["user_daily_plans"] == 0
    assert result["after"]["ai_generations"] == 0
    assert result["after"]["user_daily_plan_days"] == 0
    assert result["after"]["exports_daily_plan"] == 0
    assert db.query(User).filter(User.id == user_id).count() == 1
    assert db.query(Food).filter(Food.id == food_id).count() == 1
    assert db.query(MuscleGroup).filter(MuscleGroup.id == mg_id).count() == 1
    assert db.query(Equipment).filter(Equipment.id == eq_id).count() == 1
    from app.models.entities import Exercise

    assert db.query(Exercise).filter(Exercise.id == ex_id).count() == 1
    assert db.query(FoodCategory).filter(FoodCategory.id == cat_id).count() == 1
