"""Classic Atwater 4-4-9 alignment (no fiber)."""

from __future__ import annotations

from app.services.food_energy import (
    ATWATER_TOLERANCE,
    apply_energy_alignment_dict,
    classic_atwater_kcal,
    relative_error,
)


def test_classic_atwater() -> None:
    assert classic_atwater_kcal(10, 20, 5) == 4 * 10 + 4 * 20 + 9 * 5


def test_vn_fct_raw_row_is_aligned_when_kcal_drifts() -> None:
    row = {
        "slug": "gia-do-xanh",
        "source_ref": "vn-fct:gia-dau-xanh-tuoi",
        "food_kind": "ingredient",
        "prep_state": "raw",
        "category_slug": "rau-cu-qua",
        "kcal_100g": 80,
        "protein_100g": 5.5,
        "carbs_100g": 7.17,
        "fat_100g": 0.13,
        "serving_grams": 100,
        "calories": 80,
        "protein_g": 5.5,
        "carbs_g": 7.17,
        "fat_g": 0.13,
    }
    classic = classic_atwater_kcal(5.5, 7.17, 0.13)
    assert relative_error(80, classic) > ATWATER_TOLERANCE
    assert apply_energy_alignment_dict(row) is True
    assert row["carbs_100g"] == 7.17
    assert relative_error(row["kcal_100g"], classic) <= ATWATER_TOLERANCE


def test_produce_does_not_rewrite_carbs() -> None:
    row = {
        "slug": "rau-muong",
        "category_slug": "rau-cu-qua",
        "food_kind": "ingredient",
        "prep_state": "raw",
        "kcal_100g": 19,
        "protein_100g": 2.6,
        "carbs_100g": 3.14,
        "fat_100g": 0.2,
        "serving_grams": 100,
        "calories": 19,
        "protein_g": 2.6,
        "carbs_g": 3.14,
        "fat_g": 0.2,
        "tags": ["produce"],
    }
    apply_energy_alignment_dict(row)
    assert row["carbs_100g"] == 3.14
    expected = classic_atwater_kcal(2.6, 3.14, 0.2)
    assert relative_error(row["kcal_100g"], expected) <= ATWATER_TOLERANCE


def test_dish_is_not_rewritten() -> None:
    row = {
        "slug": "pho-bo",
        "food_kind": "dish",
        "prep_state": "cooked",
        "kcal_100g": 90,
        "protein_100g": 8,
        "carbs_100g": 10,
        "fat_100g": 2,
        "serving_grams": 100,
    }
    assert apply_energy_alignment_dict(row) is False
    assert row["kcal_100g"] == 90


def test_non_produce_only_fixes_kcal() -> None:
    row = {
        "slug": "uc-ga-khong-da-song",
        "category_slug": "thit-gia-cam-noi-tang",
        "food_kind": "ingredient",
        "prep_state": "raw",
        "kcal_100g": 200,
        "protein_100g": 23.1,
        "carbs_100g": 0,
        "fat_100g": 1.2,
        "serving_grams": 100,
        "calories": 200,
        "protein_g": 23.1,
        "carbs_g": 0,
        "fat_g": 1.2,
    }
    classic = classic_atwater_kcal(23.1, 0, 1.2)
    assert relative_error(200, classic) > ATWATER_TOLERANCE
    assert apply_energy_alignment_dict(row) is True
    assert row["carbs_100g"] == 0
    assert relative_error(row["kcal_100g"], classic) < 0.02
