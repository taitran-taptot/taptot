from fastapi import APIRouter

from app.api.v1.crud_factory import create_crud_router
from app.core.permissions import AccessPolicy
from app.models.entities import (
    Equipment,
    FoodCategory,
    KnowledgeArticle,
    MuscleGroup,
    UserProfile,
)
from app.repositories.base import ResourceConfig

PUBLIC = AccessPolicy.PUBLIC_READ.value
OWNER = AccessPolicy.OWNER.value

RESOURCE_CONFIGS: list[ResourceConfig] = [
    ResourceConfig(
        "MuscleGroup",
        MuscleGroup,
        "muscle-groups",
        "Catalog",
        PUBLIC,
        filterable_fields=("slug",),
    ),
    ResourceConfig(
        "Equipment",
        Equipment,
        "equipment",
        "Catalog",
        PUBLIC,
        filterable_fields=("slug", "category", "is_active"),
    ),
    ResourceConfig("FoodCategory", FoodCategory, "food-categories", "Catalog", PUBLIC),
    ResourceConfig(
        "KnowledgeArticle",
        KnowledgeArticle,
        "knowledge-articles",
        "Catalog",
        PUBLIC,
        list_omit_fields=("content_md",),
    ),
    ResourceConfig(
        "UserProfile",
        UserProfile,
        "user-profiles",
        "Users",
        OWNER,
        owner_field="user_id",
    ),
]


def build_resource_routers() -> APIRouter:
    router = APIRouter()
    for config in RESOURCE_CONFIGS:
        router.include_router(create_crud_router(config))
    return router
