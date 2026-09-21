from fastapi import APIRouter

from app.api.v1.crud_factory import create_crud_router
from app.core.permissions import AccessPolicy
from app.models.entities import (
    AiGeneration,
    AiQaMessage,
    AuthSession,
    CalculatorLog,
    Equipment,
    Exercise,
    Export,
    Food,
    FoodAlias,
    FoodCategory,
    KnowledgeArticle,
    MealPlan,
    MealPlanItem,
    MuscleGroup,
    PaymentTransaction,
    Subscription,
    SubscriptionPlan,
    User,
    UserAiUsage,
    UserDailyPlan,
    UserDailyPlanDay,
    UserDailyPlanExercise,
    UserDailyPlanMeal,
    UserProfile,
    WorkoutSession,
)
from app.repositories.base import ResourceConfig

PUBLIC = AccessPolicy.PUBLIC_READ.value
AUTH = AccessPolicy.AUTH_READ.value
OWNER = AccessPolicy.OWNER.value
ADMIN = AccessPolicy.ADMIN.value

RESOURCE_CONFIGS: list[ResourceConfig] = [
    # ── Catalog (public read, admin write) ──
    ResourceConfig("Exercise", Exercise, "exercises", "Catalog", PUBLIC, pk_fields=("id",),
                   filterable_fields=("muscle_group_id", "exercise_type", "difficulty", "movement_role", "movement_pattern", "venue", "is_active")),
    ResourceConfig("MuscleGroup", MuscleGroup, "muscle-groups", "Catalog", PUBLIC,
                   filterable_fields=("slug",)),
    ResourceConfig("Equipment", Equipment, "equipment", "Catalog", PUBLIC,
                   filterable_fields=("slug", "category", "is_active")),
    ResourceConfig("FoodCategory", FoodCategory, "food-categories", "Catalog", PUBLIC),
    ResourceConfig("Food", Food, "foods", "Catalog", PUBLIC, filterable_fields=("category_id", "is_common", "food_kind", "status", "prep_state", "ai_eligible", "ai_priority", "region_slug", "province_id")),
    ResourceConfig("FoodAlias", FoodAlias, "food-aliases", "Catalog", PUBLIC),
    ResourceConfig(
        "KnowledgeArticle",
        KnowledgeArticle,
        "knowledge-articles",
        "Catalog",
        PUBLIC,
        list_omit_fields=("content_md",),
    ),
    ResourceConfig("SubscriptionPlan", SubscriptionPlan, "subscription-plans", "Catalog", PUBLIC, read_only=True),
    # ── User-owned data ──
    ResourceConfig("UserProfile", UserProfile, "user-profiles", "Users", OWNER, owner_field="user_id"),
    ResourceConfig("WorkoutSession", WorkoutSession, "workout-sessions", "Workouts", OWNER, owner_field="user_id"),
    ResourceConfig("MealPlan", MealPlan, "meal-plans", "Nutrition", OWNER, owner_field="user_id"),
    ResourceConfig("MealPlanItem", MealPlanItem, "meal-plan-items", "Nutrition", AUTH,
                   ownership_hops=(("meal_plan_id", MealPlan),)),
    ResourceConfig("CalculatorLog", CalculatorLog, "calculator-logs", "Tools", OWNER, owner_field="user_id"),
    ResourceConfig("UserDailyPlan", UserDailyPlan, "daily-plans", "Plans", OWNER, owner_field="user_id"),
    ResourceConfig("UserDailyPlanDay", UserDailyPlanDay, "daily-plan-days", "Plans", AUTH,
                   ownership_hops=(("plan_id", UserDailyPlan),)),
    ResourceConfig("UserDailyPlanExercise", UserDailyPlanExercise, "daily-plan-exercises", "Plans", AUTH,
                   ownership_hops=(("plan_day_id", UserDailyPlanDay), ("plan_id", UserDailyPlan))),
    ResourceConfig("UserDailyPlanMeal", UserDailyPlanMeal, "daily-plan-meals", "Plans", AUTH,
                   ownership_hops=(("plan_day_id", UserDailyPlanDay), ("plan_id", UserDailyPlan))),
    ResourceConfig("Export", Export, "exports", "Tools", OWNER, owner_field="user_id"),
    ResourceConfig("Subscription", Subscription, "subscriptions", "Billing", OWNER, owner_field="user_id"),
    ResourceConfig("AiGeneration", AiGeneration, "ai-generations", "AI", OWNER, owner_field="user_id"),
    ResourceConfig("AiQaMessage", AiQaMessage, "ai-qa-messages", "AI", OWNER, owner_field="user_id"),
    ResourceConfig("UserAiUsage", UserAiUsage, "ai-usage", "AI", OWNER, owner_field="user_id"),
    ResourceConfig("PaymentTransaction", PaymentTransaction, "payments", "Billing", OWNER, owner_field="user_id"),
    # ── Admin-only ──
    ResourceConfig("User", User, "users", "Admin", ADMIN, read_only=True),
    ResourceConfig("AuthSession", AuthSession, "auth-sessions", "Admin", ADMIN, read_only=True),
]


def build_resource_routers() -> APIRouter:
    router = APIRouter()
    for config in RESOURCE_CONFIGS:
        router.include_router(create_crud_router(config))
    return router
