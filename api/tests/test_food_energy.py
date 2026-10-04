"""Atwater / net-carb alignment."""

from __future__ import annotations

from app.services.food_energy import (
    already_net_carb,
    apply_energy_alignment_dict,
    classic_atwater_kcal,
    modified_atwater_kcal,
    relative_error,
)


def test_classic_atwater() -> None:
    assert classic_atwater_kcal(10, 20, 5) == 4 * 10 + 4 * 20 + 9 * 5


def test_modified_subtracts_fiber_from_total_carb() -> None:
    total = modified_atwater_kcal(1, 10, 0, fiber_g=4, carbs_include_fiber=True)
    net = modified_atwater_kcal(1, 6, 0, fiber_g=4, carbs_include_fiber=False)
    assert abs(total - net) < 1e-6
    assert total == 4 * 1 + 4 * 6 + 2 * 4


def test_already_net_carb_detects_converted_row() -> None:
    protein, fat, fiber = 1.0, 0.2, 4.0
    net_c = 6.0
    kcal = modified_atwater_kcal(protein, net_c, fat, fiber, carbs_include_fiber=False)
    assert already_net_carb(
        kcal_100g=kcal,
        protein_100g=protein,
        carbs_100g=net_c,
        fat_100g=fat,
        fiber_100g=fiber,
    )


def test_cited_vn_table_row_is_not_rewritten() -> None:
    row = {
        "slug": "gia-do-xanh",
        "source_ref": "vn-fct:gia-dau-xanh-tuoi",
        "food_kind": "ingredient",
        "category_slug": "rau-cu-qua",
        "kcal_100g": 52,
        "protein_100g": 5.5,
        "carbs_100g": 7.17,
        "fat_100g": 0.13,
        "fiber_100g": 1.8,
        "serving_grams": 100,
    }
    assert apply_energy_alignment_dict(row) is False
    assert row["kcal_100g"] == 52
    assert row["carbs_100g"] == 7.17


def test_apply_produce_net_carb_idempotent() -> None:
    row = {
        "slug": "rau-muong",
        "category_slug": "rau-cu-qua",
        "food_kind": "ingredient",
        "kcal_100g": 40,
        "protein_100g": 2.0,
        "carbs_100g": 8.0,
        "fat_100g": 0.2,
        "fiber_100g": 3.0,
        "serving_grams": 100,
        "calories": 40,
        "protein_g": 2.0,
        "carbs_g": 8.0,
        "fat_g": 0.2,
        "fiber_g": 3.0,
        "tags": ["produce"],
    }
    assert apply_energy_alignment_dict(row) is True
    assert row["carbs_100g"] == 5.0
    expected = modified_atwater_kcal(2.0, 5.0, 0.2, 3.0, carbs_include_fiber=False)
    assert relative_error(row["kcal_100g"], expected) < 0.02
    snapshot = dict(row)
    assert apply_energy_alignment_dict(row) is False
    assert row["carbs_100g"] == snapshot["carbs_100g"]
    assert row["kcal_100g"] == snapshot["kcal_100g"]


def test_condiment_not_net_carb_even_if_macro_roles_produce() -> None:
    row = {
        "slug": "nuoc-mam",
        "category_slug": "gia-vi-mam-dau",
        "food_kind": "ingredient",
        "kcal_100g": 35,
        "protein_100g": 5.1,
        "carbs_100g": 3.6,
        "fat_100g": 0.0,
        "fiber_100g": 0,
        "serving_grams": 100,
        "calories": 35,
        "protein_g": 5.1,
        "carbs_g": 3.6,
        "fat_g": 0.0,
        "macro_roles": ["produce"],
    }
    apply_energy_alignment_dict(row)
    assert row["carbs_100g"] == 3.6


def test_non_produce_only_fixes_kcal() -> None:
    row = {
        "slug": "uc-ga-khong-da-song",
        "category_slug": "thit-gia-cam-noi-tang",
        "food_kind": "ingredient",
        "kcal_100g": 200,
        "protein_100g": 23.1,
        "carbs_100g": 0,
        "fat_100g": 1.2,
        "fiber_100g": 0,
        "serving_grams": 100,
        "calories": 200,
        "protein_g": 23.1,
        "carbs_g": 0,
        "fat_g": 1.2,
    }
    classic = classic_atwater_kcal(23.1, 0, 1.2)
    assert relative_error(200, classic) > 0.10
    assert apply_energy_alignment_dict(row) is True
    assert row["carbs_100g"] == 0
    assert relative_error(row["kcal_100g"], classic) < 0.02
