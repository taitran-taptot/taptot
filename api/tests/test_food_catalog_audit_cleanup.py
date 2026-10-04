"""Unit tests for food catalog audit cleanup helpers."""

from __future__ import annotations

from app.services.food_catalog_audit_cleanup import (
    AUDIT_FOOD_MERGES,
    NUTRIENT_100G_PATCHES,
    correct_inflated_dish_serving,
    scale_serving_from_100g,
)


def test_zero_macro_fish_patches_exist() -> None:
    for slug in ("ca-bac-ma", "ca-ho", "ca-moi", "ca-ngan", "ca-nuc-bong"):
        patch = NUTRIENT_100G_PATCHES[slug]
        assert float(patch["kcal_100g"]) > 0
        assert float(patch["protein_100g"]) > 10


def test_whey_isolate_is_per_100g_not_scoop() -> None:
    patch = NUTRIENT_100G_PATCHES["whey-protein-isolate"]
    assert float(patch["kcal_100g"]) >= 350
    assert float(patch["protein_100g"]) >= 80
    serving = scale_serving_from_100g(
        kcal_100g=float(patch["kcal_100g"]),
        protein_100g=float(patch["protein_100g"]),
        carbs_100g=float(patch["carbs_100g"]),
        fat_100g=float(patch["fat_100g"]),
        fiber_100g=0,
        serving_grams=30,
    )
    assert 100 <= float(serving["calories"] or 0) <= 130
    assert 25 <= float(serving["protein_g"] or 0) <= 30


def test_egg_yolk_is_per_100g() -> None:
    patch = NUTRIENT_100G_PATCHES["long-do-trung-ga"]
    assert float(patch["kcal_100g"]) >= 300
    assert float(patch["fat_100g"]) >= 25


def test_nem_macros_fit_in_serving_mass() -> None:
    patch = NUTRIENT_100G_PATCHES["nem-ran-cha-gio-chien"]
    total = (
        float(patch["protein_100g"])
        + float(patch["carbs_100g"])
        + float(patch["fat_100g"])
    )
    assert total <= 100


def test_pho_protein_deflates_to_clinical_range() -> None:
    fixed = correct_inflated_dish_serving(
        calories=1453,
        protein_g=109.3,
        carbs_g=57.3,
        fat_g=83.9,
        fiber_g=2.3,
        serving_grams=650,
    )
    assert fixed is not None
    assert 20 <= float(fixed["protein_g"] or 0) <= 35
    assert 420 <= float(fixed["calories"] or 0) <= 700


def test_bun_cha_recipe_macros_untouched() -> None:
    assert (
        correct_inflated_dish_serving(
            calories=1228,
            protein_g=35.4,
            carbs_g=68.0,
            fat_g=87.9,
            fiber_g=1.0,
            serving_grams=400,
        )
        is None
    )


def test_com_tam_plate_untouched() -> None:
    assert (
        correct_inflated_dish_serving(
            calories=1181,
            protein_g=63.3,
            carbs_g=96.2,
            fat_g=58.8,
            fiber_g=1.0,
            serving_grams=400,
        )
        is None
    )


def test_reasonable_dish_unchanged() -> None:
    assert (
        correct_inflated_dish_serving(
            calories=292,
            protein_g=5.7,
            carbs_g=64.0,
            fat_g=0.6,
            fiber_g=0.5,
            serving_grams=150,
        )
        is None
    )


def test_audit_merges_cover_report_examples() -> None:
    assert AUDIT_FOOD_MERGES["bi-ngoi"] == "bi-ngoi-xanh-zucchini"
    assert AUDIT_FOOD_MERGES["rau-chan-vit-cai-bo-xoi"] == "cai-bo-xoi-bina"
    assert AUDIT_FOOD_MERGES["tao"] == "tao-tay-envy-fuji"
    assert AUDIT_FOOD_MERGES["trung-ga"] == "trung-ga-ca-qua-song"
