import logging
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.auth import router as auth_router
from app.api.v1.ai import router as ai_router
from app.api.v1.domain import build_domain_routers
from app.api.v1.registry import build_resource_routers
from app.core.config import get_settings
from app.core.database import engine
from app.core.exceptions import AppException
from app.core.migrations import (
    ensure_base_schema,
    ensure_auth_extensions,
    ensure_ai_prompt_meta,
    ensure_equipment_image_columns,
    ensure_exercise_content_columns,
    ensure_exercise_movement_pattern,
    ensure_exercise_movement_role,
    ensure_exercise_prescription_defaults,
    ensure_exercise_secondary_muscles,
    ensure_exercise_venue_and_difficulty_v2,
    ensure_session_block_templates,
    ensure_feedback_contact_tables,
    ensure_food_catalog_v2,
    ensure_food_ai_metadata,
    ensure_food_region_metadata,
    ensure_traditional_dish_seeds,
    ensure_food_catalog_images,
    ensure_deprecated_foods,
    ensure_grain_nut_foods,
    ensure_plan_macros_and_meal_templates,
    ensure_phase3_polish,
    ensure_trainer_client_fields,
    ensure_trainer_profile_fields,
    ensure_plan_ai_generation,
    ensure_plan_insights_json,
    ensure_plan_day_nutrition,
    ensure_plan_section_column,
    ensure_plan_share_token,
    ensure_plan_guest_ttl,
    ensure_workout_schedule_frames,
    ensure_workout_session_plan_fks,
    ensure_cooking_posts,
    ensure_shop_tables,
    ensure_product_redeem_codes,
    ensure_muscle_groups_hierarchy,
    ensure_drop_meal_timing,
    ensure_deactivate_plate_equipment,
    ensure_home_equipment_catalog_v2,
    ensure_familiarization_exercises,
    ensure_gymnastic_rings_exercises,
    ensure_resistance_band_2_exercises,
    ensure_exercise_copy_vi,
)
from app.core.rate_limit import RateLimitMiddleware
from app.core.security_headers import SecurityHeadersMiddleware
from app.core.startup_checks import assert_security_settings

settings = get_settings()
logging.basicConfig(level=logging.INFO if settings.debug else logging.WARNING)
logger = logging.getLogger(__name__)


def _run_startup_migrations() -> None:
    try:
        ensure_base_schema(engine)
        ensure_auth_extensions(engine)
        ensure_plan_section_column(engine)
        ensure_plan_share_token(engine)
        ensure_plan_guest_ttl(engine)
        try:
            from app.core.database import SessionLocal
            from app.services.plan_service import purge_expired_guest_plans

            db = SessionLocal()
            try:
                n = purge_expired_guest_plans(db)
                if n:
                    logger.info("Purged %s expired guest plan(s)", n)
            finally:
                db.close()
        except Exception:
            logger.exception("Guest plan purge skipped")
        ensure_equipment_image_columns(engine)
        ensure_exercise_content_columns(engine)
        ensure_exercise_movement_role(engine)
        ensure_exercise_movement_pattern(engine)
        ensure_exercise_secondary_muscles(engine)
        ensure_exercise_venue_and_difficulty_v2(engine)
        ensure_exercise_prescription_defaults(engine)
        ensure_session_block_templates(engine)
        ensure_feedback_contact_tables(engine)
        ensure_plan_macros_and_meal_templates(engine)
        ensure_phase3_polish(engine)
        ensure_food_catalog_v2(engine)
        ensure_food_ai_metadata(engine)
        ensure_food_region_metadata(engine)
        ensure_traditional_dish_seeds(engine)
        ensure_food_catalog_images(engine)
        ensure_deprecated_foods(engine)
        ensure_grain_nut_foods(engine)
        ensure_trainer_client_fields(engine)
        ensure_trainer_profile_fields(engine)
        ensure_ai_prompt_meta(engine)
        ensure_plan_ai_generation(engine)
        ensure_plan_insights_json(engine)
        ensure_plan_day_nutrition(engine)
        ensure_workout_session_plan_fks(engine)
        ensure_workout_schedule_frames(engine)
        ensure_cooking_posts(engine)
        ensure_shop_tables(engine)
        ensure_product_redeem_codes(engine)
        ensure_muscle_groups_hierarchy(engine)
        ensure_drop_meal_timing(engine)
        ensure_deactivate_plate_equipment(engine)
        ensure_home_equipment_catalog_v2(engine)
        ensure_familiarization_exercises(engine)
        ensure_gymnastic_rings_exercises(engine)
        ensure_resistance_band_2_exercises(engine)
        ensure_exercise_copy_vi(engine)
        logger.info("Startup migrations finished")
    except Exception:
        logger.exception("Startup migrations failed")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    assert_security_settings(settings)
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    # Bind the HTTP port before schema work so Railway healthchecks are not 502.
    threading.Thread(
        target=_run_startup_migrations, name="startup-migrations", daemon=True
    ).start()
    yield


def create_app() -> FastAPI:
    show_docs = settings.debug and settings.app_env.lower() not in {"production", "prod"}
    app = FastAPI(
        title=settings.app_name,
        version="2.0.0",
        docs_url="/docs" if show_docs else None,
        redoc_url="/redoc" if show_docs else None,
        openapi_url="/openapi.json" if show_docs else None,
        lifespan=lifespan,
    )
    # Dev: allow any localhost/127.0.0.1 port (Next may run on 3001+). Prod: use CORS_ORIGINS.
    cors_origins = settings.cors_origin_list
    cors_origin_regex = None
    if (settings.app_env or "").lower() in {"development", "dev", "local"}:
        cors_origin_regex = r"https?://(localhost|127\.0\.0\.1)(:\d+)?"
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins or ["http://localhost:3000"],
        allow_origin_regex=cors_origin_regex,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept", "X-Signature"],
    )
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)

    @app.exception_handler(AppException)
    async def app_exception_handler(_request: Request, exc: AppException) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

    @app.get("/")
    def root() -> dict[str, str]:
        return {
            "app": settings.app_name,
            "status": "ok",
            "docs": "/docs",
            "frontend": "http://localhost:3000",
            "cooking_posts": "/api/v1/cooking-posts",
            "shop_products": "/api/v1/shop/products",
        }

    @app.get("/health")
    def root_health() -> dict[str, str]:
        return {"status": "ok", "env": settings.app_env}

    class RevalidatingStaticFiles(StaticFiles):
        def file_response(self, *args, **kwargs):
            response = super().file_response(*args, **kwargs)
            response.headers["Cache-Control"] = "public, max-age=3600, stale-while-revalidate=86400"
            return response

    # Only expose user media publicly — exports stay private (served via FileResponse)
    media_public = Path(settings.upload_dir) / "media"
    media_public.mkdir(parents=True, exist_ok=True)
    app.mount("/media", RevalidatingStaticFiles(directory=str(media_public)), name="media")

    api_router = APIRouter(prefix=settings.api_v1_prefix)
    api_router.include_router(auth_router)
    api_router.include_router(ai_router)
    api_router.include_router(build_domain_routers())
    api_router.include_router(build_resource_routers())
    app.include_router(api_router)

    return app


app = create_app()
