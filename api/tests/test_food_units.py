"""Household units resolve to grams before any calorie math."""

import pytest

from app.services.food_units import macros_for_grams, to_grams


def test_mass_units():
    assert to_grams(500, "g") == 500
    assert to_grams(0.5, "kg") == 500
    assert to_grams(500, "mg") == 0.5


def test_water_millilitres_use_density_one():
    assert to_grams(400, "ml", slug="nuoc-loc") == 400
    assert to_grams(1, "l", slug="nuoc-loc") == 1000


def test_fish_sauce_tablespoon_uses_portion_grams():
    portions = [
        {"label_vi": "1 muỗng canh (15ml)", "grams": 18},
        {"label_vi": "1 muỗng cà phê (5ml)", "grams": 6},
    ]
    assert to_grams(2, "thìa canh", portions=portions) == 36
    assert to_grams(1, "muỗng", portions=portions) == 18
    assert to_grams(1, "thìa cà phê", portions=portions) == 6


def test_egg_piece_uses_its_own_portion():
    portions = [
        {"label_vi": "100g", "grams": 100},
        {"label_vi": "1 quả (~50g)", "grams": 50},
    ]
    assert to_grams(2, "quả", portions=portions) == 100


def test_volume_without_density_is_rejected():
    with pytest.raises(ValueError):
        to_grams(10, "ml", slug="uc-ga-khong-da-song")


def test_macros_follow_converted_grams():
    shown = macros_for_grams(
        {"kcal": 110, "protein_g": 23.1, "carbs_g": 0, "fat_g": 1.2, "fiber_g": 0},
        to_grams(0.5, "kg"),
    )
    assert shown is not None
    assert shown["calories"] == 550
    assert shown["protein_g"] == 115.5
