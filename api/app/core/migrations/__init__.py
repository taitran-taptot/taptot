"""Startup schema/seed helpers. Public names stay stable."""

from sqlalchemy.engine import Engine

from app.core.migrations.ensures import (
    ensure_ai_prompt_meta,
    ensure_auth_extensions,
    ensure_base_schema,
    ensure_cooking_posts,
    ensure_deactivate_plate_equipment,
    ensure_deprecated_foods,
    ensure_drop_meal_timing,
    ensure_drop_unused_legacy,
    ensure_equipment_image_columns,
    ensure_exercise_content_columns,
    ensure_exercise_copy_vi,
    ensure_exercise_movement_pattern,
    ensure_exercise_movement_role,
    ensure_exercise_prescription_defaults,
    ensure_exercise_secondary_muscles,
    ensure_exercise_venue_and_difficulty_v2,
    ensure_familiarization_exercises,
    ensure_feedback_contact_tables,
    ensure_feedback_plan_url_column,
    ensure_feedback_user_id_nullable,
    ensure_food_ai_metadata,
    ensure_food_catalog_images,
    ensure_food_catalog_v2,
    ensure_foods_catalog_v2_rows,
    ensure_food_region_metadata,
    ensure_grain_nut_foods,
    ensure_cooking_pantry_foods,
    ensure_gymnastic_rings_exercises,
    ensure_home_equipment_catalog_v2,
    ensure_muscle_groups_hierarchy,
    ensure_phase3_polish,
    ensure_plan_ai_generation,
    ensure_plan_day_nutrition,
    ensure_plan_exercise_reps_text,
    ensure_plan_guest_ttl,
    ensure_plan_insights_json,
    ensure_plan_macros_and_meal_templates,
    ensure_plan_section_column,
    ensure_plan_share_token,
    ensure_product_redeem_codes,
    ensure_pushup_challenge_entries,
    ensure_pushup_challenge_sessions,
    ensure_challenge_payments,
    ensure_resistance_band_2_exercises,
    ensure_purge_exercises_missing_video,
    ensure_reactivate_spec_library_exercises,
    ensure_session_block_templates,
    ensure_shop_tables,
    ensure_traditional_dish_seeds,
    ensure_trainer_client_fields,
    ensure_trainer_profile_fields,
    ensure_user_roles_normalized,
    ensure_workout_session_plan_fks,
)

__all__ = [
    "run_startup_migrations",
    "ensure_ai_prompt_meta",
    "ensure_auth_extensions",
    "ensure_base_schema",
    "ensure_cooking_posts",
    "ensure_deactivate_plate_equipment",
    "ensure_deprecated_foods",
    "ensure_drop_meal_timing",
    "ensure_drop_unused_legacy",
    "ensure_equipment_image_columns",
    "ensure_exercise_content_columns",
    "ensure_exercise_copy_vi",
    "ensure_exercise_movement_pattern",
    "ensure_exercise_movement_role",
    "ensure_exercise_prescription_defaults",
    "ensure_exercise_secondary_muscles",
    "ensure_exercise_venue_and_difficulty_v2",
    "ensure_familiarization_exercises",
    "ensure_feedback_contact_tables",
    "ensure_feedback_plan_url_column",
    "ensure_feedback_user_id_nullable",
    "ensure_food_ai_metadata",
    "ensure_food_catalog_images",
    "ensure_food_catalog_v2",
    "ensure_foods_catalog_v2_rows",
    "ensure_food_region_metadata",
    "ensure_grain_nut_foods",
    "ensure_cooking_pantry_foods",
    "ensure_gymnastic_rings_exercises",
    "ensure_home_equipment_catalog_v2",
    "ensure_muscle_groups_hierarchy",
    "ensure_phase3_polish",
    "ensure_plan_ai_generation",
    "ensure_plan_day_nutrition",
    "ensure_plan_exercise_reps_text",
    "ensure_plan_guest_ttl",
    "ensure_plan_insights_json",
    "ensure_plan_macros_and_meal_templates",
    "ensure_plan_section_column",
    "ensure_plan_share_token",
    "ensure_product_redeem_codes",
    "ensure_pushup_challenge_entries",
    "ensure_pushup_challenge_sessions",
    "ensure_challenge_payments",
    "ensure_resistance_band_2_exercises",
    "ensure_purge_exercises_missing_video",
    "ensure_reactivate_spec_library_exercises",
    "ensure_session_block_templates",
    "ensure_shop_tables",
    "ensure_traditional_dish_seeds",
    "ensure_trainer_client_fields",
    "ensure_trainer_profile_fields",
    "ensure_user_roles_normalized",
    "ensure_workout_session_plan_fks",
]


def run_startup_migrations(engine: Engine, *, logger=None) -> None:
    """Apply all ensure_* steps in the same order as the previous main.py thread."""
    ensure_base_schema(engine)
    ensure_auth_extensions(engine)
    ensure_plan_section_column(engine)
    ensure_plan_exercise_reps_text(engine)
    ensure_plan_share_token(engine)
    ensure_plan_guest_ttl(engine)
    if logger is not None:
        try:
            from app.core.database import SessionLocal
            from app.services.plan_service import purge_expired_guest_plans

            db = SessionLocal()
            try:
                n = purge_expired_guest_plans(db)
                if n:
                    logger.info("Purged %s expired plan(s)", n)
            finally:
                db.close()
        except Exception:
            logger.exception("Plan TTL purge skipped")
    ensure_equipment_image_columns(engine)
    ensure_exercise_content_columns(engine)
    ensure_exercise_movement_role(engine)
    ensure_exercise_movement_pattern(engine)
    ensure_exercise_secondary_muscles(engine)
    ensure_exercise_venue_and_difficulty_v2(engine)
    ensure_exercise_prescription_defaults(engine)
    ensure_session_block_templates(engine)
    ensure_feedback_contact_tables(engine)
    ensure_feedback_plan_url_column(engine)
    ensure_feedback_user_id_nullable(engine)
    ensure_plan_macros_and_meal_templates(engine)
    ensure_phase3_polish(engine)
    ensure_food_catalog_v2(engine)
    ensure_food_ai_metadata(engine)
    ensure_food_region_metadata(engine)
    ensure_foods_catalog_v2_rows(engine)
    ensure_traditional_dish_seeds(engine)
    ensure_food_catalog_images(engine)
    ensure_deprecated_foods(engine)
    ensure_grain_nut_foods(engine)
    ensure_cooking_pantry_foods(engine)
    ensure_trainer_client_fields(engine)
    ensure_trainer_profile_fields(engine)
    ensure_user_roles_normalized(engine)
    ensure_ai_prompt_meta(engine)
    ensure_plan_ai_generation(engine)
    ensure_plan_insights_json(engine)
    ensure_plan_day_nutrition(engine)
    ensure_workout_session_plan_fks(engine)
    ensure_cooking_posts(engine)
    ensure_shop_tables(engine)
    ensure_product_redeem_codes(engine)
    ensure_muscle_groups_hierarchy(engine)
    ensure_drop_meal_timing(engine)
    ensure_drop_unused_legacy(engine)
    ensure_deactivate_plate_equipment(engine)
    ensure_home_equipment_catalog_v2(engine)
    ensure_familiarization_exercises(engine)
    ensure_gymnastic_rings_exercises(engine)
    ensure_resistance_band_2_exercises(engine)
    ensure_purge_exercises_missing_video(engine)
    ensure_reactivate_spec_library_exercises(engine)
    ensure_exercise_copy_vi(engine)
    ensure_pushup_challenge_entries(engine)
    ensure_pushup_challenge_sessions(engine)
    ensure_challenge_payments(engine)
