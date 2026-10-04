"""Raw-weight batch nutrition: cooked per 100g and k/N slices."""

from app.services.recipe_nutrition import cooked_profile, food_per_100g, scale_line, sum_lines


def test_chicken_breast_500g_is_550_kcal():
    per100 = food_per_100g({"kcal_100g": 110, "protein_100g": 23.1, "carbs_100g": 0, "fat_100g": 1.2})
    assert per100 is not None
    line = scale_line(per100, 500)
    shown = cooked_profile(line, 1, 500)
    assert shown["batch"]["calories"] == 550
    assert shown["per_100g"]["kcal_100g"] == 110
    assert shown["per_100g"]["protein_100g"] == 23.1


def test_yield_changes_density_not_batch_total():
    batch = sum_lines([scale_line({"kcal": 110, "protein_g": 23, "carbs_g": 0, "fat_g": 1, "fiber_g": 0}, 200)])
    raw = cooked_profile(batch, 1, 200)
    cooked = cooked_profile(batch, 1, 150)
    assert raw["batch"]["calories"] == cooked["batch"]["calories"]
    assert cooked["per_100g"]["kcal_100g"] > raw["per_100g"]["kcal_100g"]


def test_quarter_portions_split_the_batch():
    batch = {"kcal": 400, "protein_g": 40, "carbs_g": 20, "fat_g": 10, "fiber_g": 4}
    profile = cooked_profile(batch, 4, 800)
    labels = [row["label"] for row in profile["portions"]]
    assert labels == ["1/4", "2/4", "3/4", "4/4"]
    assert profile["portions"][0]["calories"] == 100
    assert profile["portions"][1]["calories"] == 200
    assert profile["portions"][0]["grams"] == 200
    assert profile["serving"]["calories"] == 100
    assert profile["per_100g"]["kcal_100g"] == 50
