from datetime import date, datetime
from typing import Any

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

UserId = Uuid(as_uuid=False)


class MuscleGroup(Base):
    __tablename__ = "muscle_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    name_vi: Mapped[str] = mapped_column(Text, nullable=False)
    name_en: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    parent_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("muscle_groups.id", ondelete="SET NULL"), nullable=True
    )
    is_filter_only: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class Equipment(Base):
    __tablename__ = "equipment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    name_vi: Mapped[str] = mapped_column(Text, nullable=False)
    name_en: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    image_url: Mapped[str | None] = mapped_column(Text)
    image_source: Mapped[str | None] = mapped_column(Text)
    image_attribution: Mapped[str | None] = mapped_column(Text)


class Exercise(Base):
    __tablename__ = "exercises"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name_vi: Mapped[str] = mapped_column(Text, nullable=False)
    name_en: Mapped[str | None] = mapped_column(Text)
    muscle_group_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("muscle_groups.id"), nullable=False
    )
    exercise_type: Mapped[str] = mapped_column(Text, nullable=False, default="main")
    movement_role: Mapped[str | None] = mapped_column(Text)
    movement_pattern: Mapped[str | None] = mapped_column(Text)
    venue: Mapped[str | None] = mapped_column(Text)
    difficulty: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    difficulty_label: Mapped[str | None] = mapped_column(Text)
    notes_vi: Mapped[str | None] = mapped_column(Text)
    secondary_muscles: Mapped[Any] = mapped_column(JSON, nullable=False, default=list)
    instruction_vi: Mapped[str | None] = mapped_column(Text)
    instruction_steps_vi: Mapped[Any | None] = mapped_column(JSON)
    common_mistakes_vi: Mapped[str | None] = mapped_column(Text)
    tips_vi: Mapped[str | None] = mapped_column(Text)
    gif_url: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(Text)
    video_url: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class ExerciseEquipment(Base):
    __tablename__ = "exercise_equipment"

    exercise_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("exercises.id", ondelete="CASCADE"), primary_key=True
    )
    equipment_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("equipment.id", ondelete="CASCADE"), primary_key=True
    )


# Legacy label tables (may still exist in DB; kept for optional compatibility reads)
class ExerciseLocalization(Base):
    __tablename__ = "exercise_localizations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    exercise_id: Mapped[int] = mapped_column(Integer, nullable=False)
    locale: Mapped[str] = mapped_column(Text, nullable=False, default="vi")
    name: Mapped[str] = mapped_column(Text, nullable=False)
    instruction: Mapped[str | None] = mapped_column(Text)
    instruction_steps: Mapped[Any | None] = mapped_column(JSON)
    common_mistakes: Mapped[str | None] = mapped_column(Text)
    tips: Mapped[str | None] = mapped_column(Text)


class BodyPartLabel(Base):
    __tablename__ = "body_part_labels"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    label_vi: Mapped[str] = mapped_column(Text, nullable=False)


class EquipmentLabel(Base):
    __tablename__ = "equipment_labels"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    label_vi: Mapped[str] = mapped_column(Text, nullable=False)


class MuscleLabel(Base):
    __tablename__ = "muscle_labels"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    label_vi: Mapped[str] = mapped_column(Text, nullable=False)


class FoodCategory(Base):
    __tablename__ = "food_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    name_vi: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class Food(Base):
    __tablename__ = "foods"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    name_vi: Mapped[str] = mapped_column(Text, nullable=False)
    name_en: Mapped[str | None] = mapped_column(Text)
    category_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("food_categories.id"))
    serving_size: Mapped[str] = mapped_column(Text, nullable=False)
    serving_grams: Mapped[float | None] = mapped_column(Float)
    calories: Mapped[float] = mapped_column(Float, nullable=False)
    protein_g: Mapped[float] = mapped_column(Float, nullable=False)
    carbs_g: Mapped[float] = mapped_column(Float, nullable=False)
    fat_g: Mapped[float] = mapped_column(Float, nullable=False)
    fiber_g: Mapped[float | None] = mapped_column(Float)
    sugar_g: Mapped[float | None] = mapped_column(Float)
    sodium_mg: Mapped[float | None] = mapped_column(Float)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_common: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    tags: Mapped[Any] = mapped_column(JSON, nullable=False, default=list)
    vitamins_json: Mapped[Any] = mapped_column(JSON, nullable=False, default=dict)
    image_url: Mapped[str | None] = mapped_column(Text)
    owner_user_id: Mapped[str | None] = mapped_column(
        UserId, ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    food_kind: Mapped[str] = mapped_column(Text, nullable=False, default="ingredient")
    prep_state: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="active")
    merged_into_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("foods.id"))
    kcal_100g: Mapped[float | None] = mapped_column(Float)
    protein_100g: Mapped[float | None] = mapped_column(Float)
    carbs_100g: Mapped[float | None] = mapped_column(Float)
    fat_100g: Mapped[float | None] = mapped_column(Float)
    fiber_100g: Mapped[float | None] = mapped_column(Float)
    sugar_100g: Mapped[float | None] = mapped_column(Float)
    sodium_100mg: Mapped[float | None] = mapped_column(Float)
    alcohol_100g: Mapped[float | None] = mapped_column(Float)
    source_ref: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[str] = mapped_column(Text, nullable=False, default="estimated")
    yield_factor: Mapped[float | None] = mapped_column(Float)
    density_g_per_ml: Mapped[float | None] = mapped_column(Float)
    macro_roles: Mapped[Any] = mapped_column(JSON, nullable=False, default=list)
    meal_slots: Mapped[Any] = mapped_column(JSON, nullable=False, default=list)
    ai_eligible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    ai_priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_complete_meal: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    default_for_ai: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    region_slug: Mapped[str | None] = mapped_column(Text)
    province_id: Mapped[str | None] = mapped_column(Text)
    description_vi: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class FoodPortion(Base):
    __tablename__ = "food_portions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    food_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("foods.id", ondelete="CASCADE"), nullable=False
    )
    label_vi: Mapped[str] = mapped_column(Text, nullable=False)
    grams: Mapped[float] = mapped_column(Float, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class FoodAlias(Base):
    __tablename__ = "food_aliases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    food_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("foods.id", ondelete="CASCADE"), nullable=False
    )
    alias: Mapped[str] = mapped_column(Text, nullable=False)


class Program(Base):
    __tablename__ = "programs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    title_vi: Mapped[str] = mapped_column(Text, nullable=False)
    description_vi: Mapped[str | None] = mapped_column(Text)
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    level: Mapped[str] = mapped_column(Text, nullable=False)
    location: Mapped[str] = mapped_column(Text, nullable=False)
    duration_days: Mapped[int] = mapped_column(Integer, nullable=False)
    days_per_week: Mapped[int] = mapped_column(Integer, nullable=False)
    equipment_filter: Mapped[Any | None] = mapped_column(JSON)
    is_free: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    cover_image_url: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class ProgramDay(Base):
    __tablename__ = "program_days"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    program_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("programs.id", ondelete="CASCADE"), nullable=False
    )
    day_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title_vi: Mapped[str | None] = mapped_column(Text)
    is_rest_day: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notes_vi: Mapped[str | None] = mapped_column(Text)


class ProgramDayExercise(Base):
    __tablename__ = "program_day_exercises"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    program_day_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("program_days.id", ondelete="CASCADE"), nullable=False
    )
    exercise_id: Mapped[int] = mapped_column(Integer, ForeignKey("exercises.id"), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    sets: Mapped[int] = mapped_column(Integer, nullable=False)
    reps: Mapped[str | None] = mapped_column(Text)
    rest_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    notes_vi: Mapped[str | None] = mapped_column(Text)


class ProgramDayMeal(Base):
    __tablename__ = "program_day_meals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    program_day_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("program_days.id", ondelete="CASCADE"), nullable=False
    )
    meal_type: Mapped[str] = mapped_column(Text, nullable=False)
    food_id: Mapped[int] = mapped_column(Integer, ForeignKey("foods.id"), nullable=False)
    servings: Mapped[float] = mapped_column(Float, nullable=False, default=1)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    notes_vi: Mapped[str | None] = mapped_column(Text)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(UserId, primary_key=True)
    email: Mapped[str | None] = mapped_column(Text, unique=True)
    password_hash: Mapped[str | None] = mapped_column(Text)
    display_name: Mapped[str | None] = mapped_column(Text)
    role: Mapped[str] = mapped_column(Text, nullable=False, default="user")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime)


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        UserId, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    gender: Mapped[str | None] = mapped_column(Text)
    birth_year: Mapped[int | None] = mapped_column(Integer)
    height_cm: Mapped[float | None] = mapped_column(Float)
    weight_kg: Mapped[float | None] = mapped_column(Float)
    activity_level: Mapped[str | None] = mapped_column(Text)
    goal: Mapped[str | None] = mapped_column(Text)
    target_weight_kg: Mapped[float | None] = mapped_column(Float)
    training_location: Mapped[str | None] = mapped_column(Text)
    available_equipment: Mapped[Any] = mapped_column(JSON, nullable=False, default=list)
    tdee: Mapped[int | None] = mapped_column(Integer)
    target_calories: Mapped[int | None] = mapped_column(Integer)
    target_protein_g: Mapped[int | None] = mapped_column(Integer)
    target_carbs_g: Mapped[int | None] = mapped_column(Integer)
    target_fat_g: Mapped[int | None] = mapped_column(Integer)
    experience_level: Mapped[str] = mapped_column(Text, nullable=False, default="beginner")
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class UserProgramEnrollment(Base):
    __tablename__ = "user_program_enrollments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        UserId, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    program_id: Mapped[int] = mapped_column(Integer, ForeignKey("programs.id"), nullable=False)
    started_at: Mapped[date] = mapped_column(Date, nullable=False)
    current_day: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="active")
    completed_at: Mapped[date | None] = mapped_column(Date)


class WorkoutSession(Base):
    __tablename__ = "workout_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        UserId, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    program_day_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("program_days.id"))
    enrollment_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("user_program_enrollments.id")
    )
    daily_plan_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("user_daily_plans.id", ondelete="SET NULL")
    )
    daily_plan_day_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("user_daily_plan_days.id", ondelete="SET NULL")
    )
    title_vi: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)


class WorkoutSessionSet(Base):
    __tablename__ = "workout_session_sets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("workout_sessions.id", ondelete="CASCADE"), nullable=False
    )
    exercise_id: Mapped[int] = mapped_column(Integer, ForeignKey("exercises.id"), nullable=False)
    set_number: Mapped[int] = mapped_column(Integer, nullable=False)
    target_reps: Mapped[str | None] = mapped_column(Text)
    actual_reps: Mapped[int | None] = mapped_column(Integer)
    weight_kg: Mapped[float | None] = mapped_column(Float)
    is_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    rest_seconds: Mapped[int | None] = mapped_column(Integer)


class MealPlan(Base):
    """Day-level meal template (reused when building / assigning plans)."""

    __tablename__ = "meal_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        UserId, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title_vi: Mapped[str | None] = mapped_column(Text)
    target_calories: Mapped[int | None] = mapped_column(Integer)
    target_date: Mapped[date | None] = mapped_column(Date)
    source: Mapped[str] = mapped_column(Text, nullable=False, default="manual")
    meal_notes_json: Mapped[Any] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class MealPlanItem(Base):
    __tablename__ = "meal_plan_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    meal_plan_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("meal_plans.id", ondelete="CASCADE"), nullable=False
    )
    meal_type: Mapped[str] = mapped_column(Text, nullable=False)
    food_id: Mapped[int] = mapped_column(Integer, ForeignKey("foods.id"), nullable=False)
    servings: Mapped[float] = mapped_column(Float, nullable=False, default=1)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    notes_vi: Mapped[str | None] = mapped_column(Text)


class CalculatorLog(Base):
    __tablename__ = "calculator_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str | None] = mapped_column(UserId, ForeignKey("users.id"))
    session_id: Mapped[str | None] = mapped_column(Text)
    calculator_type: Mapped[str] = mapped_column(Text, nullable=False)
    input_data: Mapped[Any] = mapped_column(JSON, nullable=False)
    result_data: Mapped[Any] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class UserWorkoutPlan(Base):
    __tablename__ = "user_workout_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        UserId, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title_vi: Mapped[str] = mapped_column(Text, nullable=False)
    description_vi: Mapped[str | None] = mapped_column(Text)
    is_template: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class UserWorkoutPlanExercise(Base):
    __tablename__ = "user_workout_plan_exercises"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plan_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user_workout_plans.id", ondelete="CASCADE"), nullable=False
    )
    exercise_id: Mapped[int] = mapped_column(Integer, ForeignKey("exercises.id"), nullable=False)
    day_of_week: Mapped[int | None] = mapped_column(Integer)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    sets: Mapped[int] = mapped_column(Integer, nullable=False)
    reps: Mapped[str | None] = mapped_column(Text)
    rest_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    notes_vi: Mapped[str | None] = mapped_column(Text)


class Export(Base):
    __tablename__ = "exports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        UserId, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    export_type: Mapped[str] = mapped_column(Text, nullable=False)
    source_id: Mapped[int | None] = mapped_column(Integer)
    format: Mapped[str] = mapped_column(Text, nullable=False)
    template_id: Mapped[str] = mapped_column(Text, nullable=False, default="default")
    file_url: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class ExportTemplate(Base):
    __tablename__ = "export_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    name_vi: Mapped[str] = mapped_column(Text, nullable=False)
    format: Mapped[str] = mapped_column(Text, nullable=False)
    plan_type: Mapped[str] = mapped_column(Text, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_premium: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    template_config: Mapped[Any] = mapped_column(JSON, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    name_vi: Mapped[str] = mapped_column(Text, nullable=False)
    price_vnd: Mapped[int] = mapped_column(Integer, nullable=False)
    billing_period: Mapped[str] = mapped_column(Text, nullable=False)
    ai_generations_per_month: Mapped[int | None] = mapped_column(Integer)
    features: Mapped[Any] = mapped_column(JSON, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        UserId, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    plan_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("subscription_plans.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(Text, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime)
    payment_provider: Mapped[str | None] = mapped_column(Text)
    external_id: Mapped[str | None] = mapped_column(Text)


class AiGeneration(Base):
    __tablename__ = "ai_generations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        UserId, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    generation_type: Mapped[str] = mapped_column(Text, nullable=False)
    input_params: Mapped[Any] = mapped_column(JSON, nullable=False)
    output_data: Mapped[Any] = mapped_column(JSON, nullable=False)
    tokens_used: Mapped[int | None] = mapped_column(Integer)
    cost_usd: Mapped[float | None] = mapped_column(Float)
    is_paid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    prompt_version: Mapped[str | None] = mapped_column(Text)
    system_prompt_hash: Mapped[str | None] = mapped_column(Text)


class AiQaMessage(Base):
    __tablename__ = "ai_qa_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        UserId, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    conversation_id: Mapped[str] = mapped_column(UserId, nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    referenced_exercise_ids: Mapped[Any | None] = mapped_column(JSON)
    referenced_food_ids: Mapped[Any | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class WorkoutScheduleFrame(Base):
    """Coach schedule frame keyed by experience_level × sessions_per_week."""

    __tablename__ = "workout_schedule_frames"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    experience_level: Mapped[int] = mapped_column(Integer, nullable=False)
    sessions_per_week: Mapped[int] = mapped_column(Integer, nullable=False)
    name_vi: Mapped[str] = mapped_column(Text, nullable=False)
    experience_label_vi: Mapped[str] = mapped_column(Text, nullable=False)
    experience_range_vi: Mapped[str] = mapped_column(Text, nullable=False)
    goal_vi: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime)


class WorkoutScheduleFrameDay(Base):
    __tablename__ = "workout_schedule_frame_days"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    frame_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("workout_schedule_frames.id", ondelete="CASCADE"), nullable=False
    )
    day_index: Mapped[int] = mapped_column(Integer, nullable=False)
    label_vi: Mapped[str] = mapped_column(Text, nullable=False)
    split_role: Mapped[str] = mapped_column(Text, nullable=False)
    focus_vi: Mapped[str | None] = mapped_column(Text)
    notes_vi: Mapped[str | None] = mapped_column(Text)
    intensity: Mapped[str] = mapped_column(Text, nullable=False, default="moderate")


class ExercisePrescriptionDefault(Base):
    """Default sets/reps keyed by experience_level × movement_role."""

    __tablename__ = "exercise_prescription_defaults"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    experience_level: Mapped[int] = mapped_column(Integer, nullable=False)
    movement_role: Mapped[str] = mapped_column(Text, nullable=False)
    default_sets: Mapped[int] = mapped_column(Integer, nullable=False)
    default_reps: Mapped[int] = mapped_column(Integer, nullable=False)


class SessionBlockTemplate(Base):
    """Session structure blocks keyed by experience_level × block_key."""

    __tablename__ = "session_block_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    experience_level: Mapped[int] = mapped_column(Integer, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    block_key: Mapped[str] = mapped_column(Text, nullable=False)
    label_vi: Mapped[str] = mapped_column(Text, nullable=False)
    plan_section: Mapped[str] = mapped_column(Text, nullable=False)
    movement_role: Mapped[str | None] = mapped_column(Text)
    count_min: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    count_max: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duration_min_minutes: Mapped[int | None] = mapped_column(Integer)
    duration_max_minutes: Mapped[int | None] = mapped_column(Integer)
    is_optional: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class EquipmentProduct(Base):
    __tablename__ = "equipment_products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    name_vi: Mapped[str] = mapped_column(Text, nullable=False)
    equipment_type: Mapped[str | None] = mapped_column(Text)
    shopee_url: Mapped[str | None] = mapped_column(Text)
    lazada_url: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class ExerciseEquipmentSuggestion(Base):
    __tablename__ = "exercise_equipment_suggestions"

    exercise_id: Mapped[int] = mapped_column(Integer, ForeignKey("exercises.id", ondelete="CASCADE"), primary_key=True,)
    product_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("equipment_products.id", ondelete="CASCADE"),
        primary_key=True,
    )


class KnowledgeSeries(Base):
    __tablename__ = "knowledge_series"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    title_vi: Mapped[str] = mapped_column(Text, nullable=False)
    description_vi: Mapped[str | None] = mapped_column(Text)
    level: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class KnowledgeArticle(Base):
    __tablename__ = "knowledge_articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    series_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("knowledge_series.id"))
    slug: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    title_vi: Mapped[str] = mapped_column(Text, nullable=False)
    content_md: Mapped[str] = mapped_column(Text, nullable=False)
    level: Mapped[str] = mapped_column(Text, nullable=False)
    read_time_min: Mapped[int | None] = mapped_column(Integer)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime)
    seo_title: Mapped[str | None] = mapped_column(Text)
    seo_description: Mapped[str | None] = mapped_column(Text)


class UserDailyPlan(Base):
    __tablename__ = "user_daily_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str | None] = mapped_column(
        UserId, ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    title_vi: Mapped[str] = mapped_column(Text, nullable=False)
    description_vi: Mapped[str | None] = mapped_column(Text)
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    target_calories: Mapped[int | None] = mapped_column(Integer)
    target_protein_g: Mapped[float | None] = mapped_column(Float)
    target_carbs_g: Mapped[float | None] = mapped_column(Float)
    target_fat_g: Mapped[float | None] = mapped_column(Float)
    source: Mapped[str] = mapped_column(Text, nullable=False, default="manual")
    is_template: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    share_token: Mapped[str | None] = mapped_column(Text, unique=True, nullable=True)
    ai_generation_id: Mapped[int | None] = mapped_column(Integer)
    insights_json: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    challenge_100_days: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class UserDailyPlanDay(Base):
    __tablename__ = "user_daily_plan_days"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plan_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user_daily_plans.id", ondelete="CASCADE"), nullable=False
    )
    day_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title_vi: Mapped[str | None] = mapped_column(Text)
    notes_vi: Mapped[str | None] = mapped_column(Text)
    target_calories: Mapped[int | None] = mapped_column(Integer)
    target_protein_g: Mapped[float | None] = mapped_column(Float)
    target_carbs_g: Mapped[float | None] = mapped_column(Float)
    target_fat_g: Mapped[float | None] = mapped_column(Float)


class UserDailyPlanExercise(Base):
    __tablename__ = "user_daily_plan_exercises"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plan_day_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user_daily_plan_days.id", ondelete="CASCADE"), nullable=False
    )
    exercise_id: Mapped[int] = mapped_column(Integer, ForeignKey("exercises.id"), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    sets: Mapped[int] = mapped_column(Integer, nullable=False)
    reps: Mapped[str | None] = mapped_column(Text)
    rest_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    section: Mapped[str] = mapped_column(Text, nullable=False, default="main")
    notes_vi: Mapped[str | None] = mapped_column(Text)


class UserDailyPlanMeal(Base):
    __tablename__ = "user_daily_plan_meals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plan_day_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user_daily_plan_days.id", ondelete="CASCADE"), nullable=False
    )
    meal_type: Mapped[str] = mapped_column(Text, nullable=False)
    food_id: Mapped[int] = mapped_column(Integer, ForeignKey("foods.id"), nullable=False)
    servings: Mapped[float] = mapped_column(Float, nullable=False, default=1)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    notes_vi: Mapped[str | None] = mapped_column(Text)


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        UserId, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime)


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        UserId, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class EmailVerificationToken(Base):
    __tablename__ = "email_verification_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        UserId, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class OAuthAccount(Base):
    __tablename__ = "oauth_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        UserId, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    provider_user_id: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class UserAiUsage(Base):
    __tablename__ = "user_ai_usage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        UserId, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    usage_month: Mapped[str] = mapped_column(Text, nullable=False)
    generation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    qa_message_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tokens_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class PaymentTransaction(Base):
    __tablename__ = "payment_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        UserId, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    subscription_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("subscriptions.id"))
    amount_vnd: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(Text, nullable=False, default="VND")
    status: Mapped[str] = mapped_column(Text, nullable=False)
    payment_provider: Mapped[str] = mapped_column(Text, nullable=False)
    external_id: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    transaction_metadata: Mapped[Any] = mapped_column("metadata", JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)


class TrainerProfile(Base):
    __tablename__ = "trainer_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        UserId, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    business_name: Mapped[str | None] = mapped_column(Text)
    bio_vi: Mapped[str | None] = mapped_column(Text)
    gym_name: Mapped[str | None] = mapped_column(Text)
    logo_url: Mapped[str | None] = mapped_column(Text)
    brand_color: Mapped[str | None] = mapped_column(Text, default="#22c55e")
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    max_clients: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    full_name: Mapped[str | None] = mapped_column(Text)
    age: Mapped[int | None] = mapped_column(Integer)
    years_experience: Mapped[int | None] = mapped_column(Integer)
    share_token: Mapped[str | None] = mapped_column(Text, unique=True)


class TrainerCredential(Base):
    """Award or certificate attached to a trainer profile (requires ≥1 image)."""

    __tablename__ = "trainer_credentials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trainer_id: Mapped[str] = mapped_column(
        UserId, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(Text, nullable=False)  # award | certificate
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    image_urls: Mapped[Any] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class TrainerClient(Base):
    __tablename__ = "trainer_clients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trainer_id: Mapped[str] = mapped_column(
        UserId, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    client_id: Mapped[str] = mapped_column(
        UserId, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(Text, nullable=False, default="active")
    started_at: Mapped[date] = mapped_column(Date, nullable=False)
    ended_at: Mapped[date | None] = mapped_column(Date)
    # Trainer-entered client info (captured when assigning a plan)
    full_name: Mapped[str | None] = mapped_column(Text)
    goal: Mapped[str | None] = mapped_column(Text)
    gender: Mapped[str | None] = mapped_column(Text)
    age: Mapped[int | None] = mapped_column(Integer)
    height_cm: Mapped[float | None] = mapped_column(Float)
    weight_kg: Mapped[float | None] = mapped_column(Float)


class ClientNote(Base):
    __tablename__ = "client_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trainer_id: Mapped[str] = mapped_column(
        UserId, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    client_id: Mapped[str] = mapped_column(
        UserId, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    note: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class TrainerAssignedPlan(Base):
    __tablename__ = "trainer_assigned_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trainer_id: Mapped[str] = mapped_column(
        UserId, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    client_id: Mapped[str] = mapped_column(
        UserId, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    daily_plan_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("user_daily_plans.id", ondelete="SET NULL")
    )
    workout_plan_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("user_workout_plans.id", ondelete="SET NULL")
    )
    program_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("programs.id"))
    title_vi: Mapped[str] = mapped_column(Text, nullable=False)
    notes_vi: Mapped[str | None] = mapped_column(Text)
    assigned_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="active")


class FeedbackSuggestion(Base):
    """User feedback about missing foods / exercises (login required)."""

    __tablename__ = "feedback_suggestions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        UserId, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    category: Mapped[str] = mapped_column(Text, nullable=False)  # food | exercise | other
    title: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class TrainerContactRequest(Base):
    """Lead form for personal trainer inquiry (public, no login)."""

    __tablename__ = "trainer_contact_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    full_name: Mapped[str] = mapped_column(Text, nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    phone_zalo: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str] = mapped_column(Text, nullable=False)
    message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class CookingPost(Base):
    __tablename__ = "cooking_posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    title_vi: Mapped[str] = mapped_column(Text, nullable=False)
    excerpt: Mapped[str | None] = mapped_column(Text)
    content_md: Mapped[str] = mapped_column(Text, nullable=False)
    cover_image_url: Mapped[str | None] = mapped_column(Text)
    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime)
    author_user_id: Mapped[str | None] = mapped_column(
        UserId, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class ShopProduct(Base):
    __tablename__ = "shop_products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    name_vi: Mapped[str] = mapped_column(Text, nullable=False)
    description_vi: Mapped[str | None] = mapped_column(Text)
    price_vnd: Mapped[int] = mapped_column(Integer, nullable=False)
    stock_qty: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    image_url: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class ShopCartItem(Base):
    __tablename__ = "shop_cart_items"
    __table_args__ = (UniqueConstraint("user_id", "product_id", name="uq_shop_cart_user_product"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        UserId, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("shop_products.id", ondelete="CASCADE"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class ShopOrder(Base):
    __tablename__ = "shop_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        UserId, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    order_status: Mapped[str] = mapped_column(Text, nullable=False, default="placed")
    total_vnd: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class ShopOrderItem(Base):
    __tablename__ = "shop_order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("shop_orders.id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("shop_products.id", ondelete="SET NULL"), nullable=True
    )
    name_vi: Mapped[str] = mapped_column(Text, nullable=False)
    unit_price_vnd: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)


class ProductRedeemBatch(Base):
    __tablename__ = "product_redeem_batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("shop_products.id", ondelete="SET NULL"), nullable=True
    )
    qty: Mapped[int] = mapped_column(Integer, nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[str] = mapped_column(
        UserId, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class ProductRedeemCode(Base):
    __tablename__ = "product_redeem_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("product_redeem_batches.id", ondelete="CASCADE"), nullable=False
    )
    code: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="unused")
    reservation_token: Mapped[str | None] = mapped_column(Text)
    reserved_at: Mapped[datetime | None] = mapped_column(DateTime)
    redeemed_at: Mapped[datetime | None] = mapped_column(DateTime)
    plan_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("user_daily_plans.id", ondelete="SET NULL"), nullable=True
    )
    redeemed_user_id: Mapped[str | None] = mapped_column(
        UserId, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

