from fastapi import APIRouter

from app.api.v1.crud_factory import create_crud_router
from app.core.permissions import AccessPolicy
from app.models.entities import (
    Equipment,
    FoodCategory,
    KnowledgeArticle,
    MuscleGroup,
)
from app.repositories.base import ResourceConfig

PUBLIC = AccessPolicy.PUBLIC_READ.value

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
]


def build_resource_routers() -> APIRouter:
    router = APIRouter()
    for config in RESOURCE_CONFIGS:
        router.include_router(create_crud_router(config))
    return router
