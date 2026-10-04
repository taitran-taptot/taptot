"""Pydantic schemas for user daily plans (nested workout + meals)."""

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Section = Literal["warmup", "main", "cooldown", "cardio"]
MealType = Literal["breakfast", "lunch", "dinner", "snack", "snack_2", "flex"]
ExerciseTechnique = Literal["drop_set", "super_set"]


class PlanSetPrescription(BaseModel):
    reps: str | int | None = "12"
    rest_seconds: int = Field(ge=0, le=600, default=90)
    rir: int | None = Field(default=None, ge=0, le=5)
    rpe: float | None = Field(default=None, ge=1, le=10)
    tempo: str | None = Field(default=None, max_length=16)
    technique: Literal["drop_set"] | None = None

    @field_validator("tempo", mode="before")
    @classmethod
    def _blank_tempo(cls, v: object) -> str | None:
        if v is None:
            return None
        s = str(v).strip()[:16]
        return s or None

    @field_validator("technique", mode="before")
    @classmethod
    def _blank_set_technique(cls, v: object) -> object:
        if v in (None, "", "none", "super_set"):
            return None
        return v


class PlanExerciseCueMixin(BaseModel):
    rir: int | None = Field(default=None, ge=0, le=5)
    rpe: float | None = Field(default=None, ge=1, le=10)
    tempo: str | None = Field(default=None, max_length=16)
    technique: ExerciseTechnique | None = None
    superset_group: int | None = Field(default=None, ge=1, le=99)
    set_prescriptions: list[PlanSetPrescription] | None = Field(default=None, max_length=20)

    @field_validator("tempo", mode="before")
    @classmethod
    def _blank_tempo(cls, v: object) -> str | None:
        if v is None:
            return None
        s = str(v).strip()[:16]
        return s or None

    @field_validator("technique", mode="before")
    @classmethod
    def _blank_technique(cls, v: object) -> object:
        if v in (None, "", "none"):
            return None
        return v

    @field_validator("set_prescriptions", mode="before")
    @classmethod
    def _empty_prescriptions(cls, v: object) -> object:
        if v in (None, [], ()):
            return None
        return v


PlanSource = Literal["manual", "ai", "template", "imported"]
ExportFormat = Literal["pdf"]
DurationUnit = Literal["day", "week", "month"]


class PlanStaffKnowledgeRef(BaseModel):
    slug: str = Field(min_length=1, max_length=200)
    title_vi: str = Field(default="", max_length=300)


class PlanClientProfile(BaseModel):
    height_cm: float | None = Field(default=None, ge=50, le=250)
    weight_kg: float | None = Field(default=None, ge=20, le=400)
    gender: Literal["male", "female"] | None = None
    notes: str | None = Field(default=None, max_length=2000)


class PlanExerciseIn(PlanExerciseCueMixin):
    exercise_id: int = Field(ge=1)
    sets: int = Field(ge=1, le=20, default=3)
    reps: str | int | None = "12"
    rest_seconds: int = Field(ge=0, le=600, default=90)
    section: Section = "main"
    notes_vi: str | None = None
    sort_order: int | None = None


class PlanMealIn(BaseModel):
    food_id: int
    meal_type: MealType = "lunch"
    servings: float = Field(gt=0, le=20, default=1)
    notes_vi: str | None = None
    sort_order: int | None = None


class PlanDayIn(BaseModel):
    day_number: int = Field(ge=1, le=100)
    title_vi: str | None = None
    notes_vi: str | None = None
    split_role: str | None = None
    # Per meal-slot notes: breakfast / lunch / dinner / snack_0 / ...
    meal_notes: dict[str, str] | None = None
    # Per exercise-section notes: warmup / main / cooldown / cardio
    section_notes: dict[str, str] | None = None
    meals_flexible: bool | None = None
    target_calories: int | None = Field(default=None, ge=500, le=10000)
    target_protein_g: float | None = Field(default=None, ge=0, le=500)
    target_carbs_g: float | None = Field(default=None, ge=0, le=1000)
    target_fat_g: float | None = Field(default=None, ge=0, le=500)
    exercises: list[PlanExerciseIn] = Field(default_factory=list)
    meals: list[PlanMealIn] = Field(default_factory=list)


class CreatePlanRequest(BaseModel):
    title_vi: str = Field(min_length=1, max_length=255)
    description_vi: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    target_calories: int | None = Field(default=None, ge=500, le=10000)
    target_protein_g: float | None = Field(default=None, ge=0, le=500)
    target_carbs_g: float | None = Field(default=None, ge=0, le=1000)
    target_fat_g: float | None = Field(default=None, ge=0, le=500)
    source: PlanSource = "manual"
    is_template: bool = False
    duration_weeks: int = Field(default=1, ge=1, le=14)
    experience_level: int | None = Field(default=None, ge=1, le=5)
    strength_tier: str | None = None
    challenge_100_days: bool = False
    day_count: int | None = Field(default=None, ge=1, le=100)
    duration_unit: DurationUnit | None = None
    duration_count: int | None = Field(default=None, ge=1, le=100)
    share_slug: str | None = Field(default=None, max_length=64)
    client: PlanClientProfile | None = None
    days: list[PlanDayIn] = Field(default_factory=list)


class PlanExerciseOut(BaseModel):
    id: int
    exercise_id: int
    name_vi: str
    name_en: str | None = None
    body_part: str | None = None
    gif_url: str | None = None
    image_url: str | None = None
    video_url: str | None = None
    instruction_vi: str | None = None
    instruction_steps_vi: list[str] | None = None
    section: str
    sets: int
    reps: str | None
    rest_seconds: int
    sort_order: int
    notes_vi: str | None = None
    rir: int | None = None
    rpe: float | None = None
    tempo: str | None = None
    technique: str | None = None
    superset_group: int | None = None
    set_prescriptions: list[PlanSetPrescription] | None = None


class PlanMealOut(BaseModel):
    id: int
    food_id: int
    name_vi: str
    meal_type: str
    servings: float
    calories: int
    protein_g: float | None = None
    carbs_g: float | None = None
    fat_g: float | None = None
    serving_size: str | None = None
    serving_grams: float | None = None
    sort_order: int
    notes_vi: str | None = None
    image_url: str | None = None


class PlanDayOut(BaseModel):
    id: int
    day_number: int
    title_vi: str | None
    notes_vi: str | None = None
    split_role: str | None = None
    meal_notes: dict[str, str] = Field(default_factory=dict)
    section_notes: dict[str, str] = Field(default_factory=dict)
    meals_flexible: bool = False
    target_calories: int | None = None
    target_protein_g: float | None = None
    target_carbs_g: float | None = None
    target_fat_g: float | None = None
    exercises: list[PlanExerciseOut]
    meals: list[PlanMealOut]


class PlanInsightOverview(BaseModel):
    schedule_vi: str | None = None
    nutrition_vi: str | None = None
    periodization_vi: str | None = None
    summary_vi: str | None = None
    mission_vi: str | None = None
    outcome_vi: str | None = None


class PlanExerciseInsight(BaseModel):
    exercise_id: int
    why_vi: str


class PlanMealInsight(BaseModel):
    food_id: int
    meal_type: str
    why_vi: str


class PlanDayInsight(BaseModel):
    day_number: int
    split_role: str | None = None
    section_notes: dict[str, str] = Field(default_factory=dict)
    meal_notes: dict[str, str] = Field(default_factory=dict)
    exercises: list[PlanExerciseInsight] = Field(default_factory=list)
    meals: list[PlanMealInsight] = Field(default_factory=list)


class PlanWizardInputsOut(BaseModel):
    model_config = ConfigDict(extra="ignore")

    recap_vi: str | None = None
    chips: list[str] = Field(default_factory=list)
    goal_vi: str | None = None
    location_vi: str | None = None
    equipment_vi: str | None = None
    experience_vi: str | None = None
    experience_level: int | None = None
    sessions_per_week: int | None = None
    session_minutes: int | None = None
    duration_weeks: int | None = None
    focus_vi: list[str] = Field(default_factory=list)
    gender_vi: str | None = None
    age: int | None = None
    challenge_100_days: bool = False
    location: str | None = None
    no_equipment: bool = False
    equipment_list: list[str] = Field(default_factory=list)


class PlanCurriculumMesocycleOut(BaseModel):
    month: int
    key: str | None = None
    label_vi: str | None = None
    blurb_vi: str | None = None
    rpe_vi: str | None = None
    deload_week: int | None = None
    weeks: list[int] = Field(default_factory=list)
    rationale_vi: str | None = None


class PlanCurriculumOut(BaseModel):
    mesocycles: list[PlanCurriculumMesocycleOut] = Field(default_factory=list)
    deload_weeks: list[int] = Field(default_factory=list)
    duration_weeks: int | None = None


class PlanWeightGoalOut(BaseModel):
    model_config = ConfigDict(extra="ignore")

    bmi: float | None = None
    band: str | None = None
    band_vi: str | None = None
    goal: str | None = None
    current_kg: float | None = None
    target_kg: float | None = None
    target_bmi: float | None = None
    weeks: int | None = None
    daily_kcal: int | None = None
    protein_g: float | None = None
    copy_vi: str | None = None


class PlanInsightsOut(BaseModel):
    """AI insights blob — tolerate partial / hybrid metadata shapes."""

    model_config = ConfigDict(extra="ignore")

    overview: PlanInsightOverview = Field(default_factory=PlanInsightOverview)
    advice_vi: list[str] = Field(default_factory=list)
    days: list[PlanDayInsight] = Field(default_factory=list)
    inputs: PlanWizardInputsOut | None = None
    challenge_100_days: bool | None = None
    challenge_kind: str | None = None
    curriculum_12_weeks: bool | None = None
    curriculum: PlanCurriculumOut | None = None
    nutrition_blocks: list[dict[str, Any]] | None = None
    nutrition_block_size: int | None = None
    nutrition_checkin_interval_days: int | None = None
    nutrition_checkins: list[dict[str, Any]] | None = None
    last_nutrition_checkin_at: str | None = None
    next_nutrition_checkin_due: str | None = None
    rest_day_nutrition: dict[str, Any] | None = None
    rest_day_meals: list[dict[str, Any]] | None = None
    effective_level: int | None = None
    staff_knowledge: list[PlanStaffKnowledgeRef] = Field(default_factory=list)
    client: PlanClientProfile | None = None
    # Familiarization / free-home metadata (must not be stripped — FE gates UI on these)
    generation_mode: str | None = None
    generator: str | None = None
    familiarization_path: str | None = None
    duration_days: int | None = None
    duration_weeks: int | None = None
    sessions_per_week: int | None = None
    weight_goal: PlanWeightGoalOut | None = None
    fitness_test_href: str | None = None


class PlanSummaryOut(BaseModel):
    id: int
    title_vi: str
    description_vi: str | None
    source: str
    target_calories: int | None
    target_protein_g: float | None = None
    target_carbs_g: float | None = None
    target_fat_g: float | None = None
    is_template: bool = False
    start_date: date | None
    end_date: date | None
    ai_generation_id: int | None = None
    share_token: str | None = None
    redeem_code: str | None = None
    share_url_path: str | None = None
    day_count: int
    exercise_count: int
    meal_count: int
    created_at: datetime
    updated_at: datetime
    is_guest: bool = False
    challenge_100_days: bool = False
    expires_at: datetime | None = None
    days_left: int | None = None


class PlanDetailOut(PlanSummaryOut):
    days: list[PlanDayOut]
    insights: PlanInsightsOut | None = None


class PlanExportOptions(BaseModel):
    customer_name: str | None = Field(default=None, max_length=200)
    header_text: str | None = Field(default=None, max_length=2000)
    footer_text: str | None = Field(default=None, max_length=2000)
    image_data_urls: list[str] = Field(default_factory=list, max_length=2)
    image_position: Literal["header", "before_days", "footer"] = "header"


class PlanExportRequest(BaseModel):
    format: ExportFormat = "pdf"
    options: PlanExportOptions | None = None


class UpdatePlanExerciseIn(PlanExerciseCueMixin):
    """Editable exercise row — plan metadata / calories stay locked."""

    exercise_id: int = Field(ge=1)
    sets: int = Field(ge=1, le=20, default=3)
    reps: str | int | None = "12"
    rest_seconds: int = Field(ge=0, le=600, default=90)
    section: Section = "main"
    sort_order: int | None = None
    notes_vi: str | None = None


class UpdatePlanMealIn(BaseModel):
    food_id: int
    meal_type: MealType = "lunch"
    servings: float = Field(gt=0, le=20, default=1)
    sort_order: int | None = None
    notes_vi: str | None = None


class UpdatePlanDayIn(BaseModel):
    day_number: int = Field(ge=1, le=100)
    title_vi: str | None = None
    notes_vi: str | None = None
    split_role: str | None = None
    meal_notes: dict[str, str] | None = None
    section_notes: dict[str, str] | None = None
    meals_flexible: bool | None = None
    exercises: list[UpdatePlanExerciseIn] = Field(default_factory=list)
    meals: list[UpdatePlanMealIn] = Field(default_factory=list)


class UpdatePlanContentRequest(BaseModel):
    """Replace exercises, meals, and optionally days/title for staff editors."""

    title_vi: str | None = Field(default=None, min_length=1, max_length=255)
    description_vi: str | None = None
    share_slug: str | None = Field(default=None, max_length=64)
    overview_summary_vi: str | None = None
    staff_knowledge: list[PlanStaffKnowledgeRef] | None = None
    client: PlanClientProfile | None = None
    sync_days: bool = False
    days: list[UpdatePlanDayIn] = Field(min_length=1)


class NutritionCheckinRequest(BaseModel):
    weight_kg: float = Field(ge=30, le=300)


class NutritionCheckinPreviewOut(BaseModel):
    weight_kg: float
    avg_target_calories: int
    delta_from_current: int
    protein_g: float
    current_week: int
    block_index: int


class NutritionCheckinOut(BaseModel):
    preview: NutritionCheckinPreviewOut
    plan: PlanDetailOut


class ClaimPlansRequest(BaseModel):
    share_tokens: list[str] = Field(default_factory=list, max_length=20)


class PlanQuotaOut(BaseModel):
    used: int
    limit: int | None = None
    remaining: int | None = None
    unlimited: bool = True


class ClaimPlansOut(BaseModel):
    claimed_count: int
    claimed: list[PlanSummaryOut]
    skipped_full: list[str] = Field(default_factory=list)
    not_found: list[str] = Field(default_factory=list)
    already_owned: list[str] = Field(default_factory=list)
    quota: PlanQuotaOut


# ── Meal templates (day-level, stored in meal_plans) ──


class MealTemplateItemIn(BaseModel):
    food_id: int
    meal_type: MealType = "lunch"
    servings: float = Field(gt=0, le=20, default=1)
    notes_vi: str | None = None
    sort_order: int | None = None


class CreateMealTemplateRequest(BaseModel):
    title_vi: str = Field(min_length=1, max_length=255)
    target_calories: int | None = Field(default=None, ge=0, le=10000)
    meal_notes: dict[str, str] = Field(default_factory=dict)
    items: list[MealTemplateItemIn] = Field(default_factory=list, max_length=80)


class MealTemplateItemOut(BaseModel):
    id: int
    food_id: int
    name_vi: str
    meal_type: str
    servings: float
    calories: int
    protein_g: float | None = None
    carbs_g: float | None = None
    fat_g: float | None = None
    serving_size: str | None = None
    serving_grams: float | None = None
    sort_order: int
    notes_vi: str | None = None


class MealTemplateOut(BaseModel):
    id: int
    title_vi: str | None
    target_calories: int | None
    meal_notes: dict[str, str] = Field(default_factory=dict)
    item_count: int
    total_calories: int
    created_at: datetime
    items: list[MealTemplateItemOut] = Field(default_factory=list)


class MealTemplateSummaryOut(BaseModel):
    id: int
    title_vi: str | None
    target_calories: int | None
    item_count: int
    total_calories: int
    created_at: datetime


class AssignPlanRequest(BaseModel):
    """Trainer assigns a clone of a plan (or template) to a client."""

    client_id: str = Field(min_length=1, max_length=64)
    source_plan_id: int = Field(ge=1)
    title_vi: str | None = Field(default=None, max_length=255)
    notes_vi: str | None = None
    # Trainer-entered client info
    full_name: str | None = Field(default=None, max_length=120)
    goal: str | None = Field(default=None, max_length=40)
    gender: str | None = Field(default=None, max_length=20)
    age: int | None = Field(default=None, ge=10, le=100)
    height_cm: float | None = Field(default=None, ge=80, le=250)
    weight_kg: float | None = Field(default=None, ge=20, le=400)


class AssignPlanOut(BaseModel):
    assignment_id: int
    plan_id: int
    client_id: str
    title_vi: str
    share_token: str | None = None
    share_url_path: str | None = None
