from fastapi import APIRouter

from app.api.v1.admin import router as admin_router
from app.api.v1.calculators import router as calculators_router
from app.api.v1.compliance import router as compliance_router
from app.api.v1.cooking_posts import router as cooking_posts_router
from app.api.v1.enrollments import router as enrollments_router
from app.api.v1.exports import router as exports_router
from app.api.v1.feedback import router as feedback_router
from app.api.v1.health import router as health_router
from app.api.v1.media import router as media_router
from app.api.v1.payments import router as payments_router
from app.api.v1.plans import router as plans_router
from app.api.v1.programs import router as programs_router
from app.api.v1.search import router as search_router
from app.api.v1.shop import router as shop_router
from app.api.v1.templates import router as templates_router
from app.api.v1.trainer_profile import router as trainer_profile_router


def build_domain_routers() -> APIRouter:
    router = APIRouter()
    router.include_router(health_router)
    router.include_router(search_router)
    router.include_router(programs_router)
    router.include_router(calculators_router)
    router.include_router(enrollments_router)
    router.include_router(payments_router)
    router.include_router(exports_router)
    # templates before plans so /my-plans/templates is not captured by {plan_id}
    router.include_router(templates_router)
    router.include_router(plans_router)
    router.include_router(compliance_router)
    router.include_router(trainer_profile_router)
    router.include_router(feedback_router)
    router.include_router(media_router)
    router.include_router(cooking_posts_router)
    router.include_router(shop_router)
    router.include_router(admin_router)
    return router
