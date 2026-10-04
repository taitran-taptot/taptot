"""Household amount labels for cooking BOMs."""

from app.services.cooking_amount import format_amount_label, line_calories


class _Food:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


def test_liquid_keeps_spoon_count_and_adds_ml_grams() -> None:
    label = format_amount_label(
        grams=30,
        slug="nuoc-mam",
        existing="2 muỗng canh nước mắm",
        portions=[{"label_vi": "1 muỗng canh (15ml)", "grams": 18}],
    )
    assert "2 muỗng canh" in label
    assert "30ml" in label
    assert "30g" in label


def test_solid_household_keeps_tep_and_grams() -> None:
    label = format_amount_label(grams=15, slug="toi-ta-toi-tia", existing="3 tép tỏi")
    assert "3 tép tỏi" in label
    assert "15g" in label


def test_portion_fit_oil_tbsp() -> None:
    label = format_amount_label(
        grams=28,
        slug="dau-an",
        existing="dầu",
        portions=[{"label_vi": "1 muỗng canh (15ml)", "grams": 14}],
    )
    assert "2 muỗng canh" in label
    assert "30ml" in label
    assert "28g" in label


def test_line_calories_from_kcal_100g() -> None:
    food = _Food(kcal_100g=365)
    assert line_calories(320, food) == 1168
