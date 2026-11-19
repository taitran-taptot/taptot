"""Wizard equipment slugs for the three home kits."""

from app.services.workout_generation.shortlist import coerce_wizard_gen_equipment


def test_coerce_wizard_accepts_vietnamese_shop_slugs():
    assert coerce_wizard_gen_equipment(["ta-don"]) == ["dumbbell"]
    assert coerce_wizard_gen_equipment(["day-khang-luc"]) == ["resistance-band-2"]
    assert set(coerce_wizard_gen_equipment(["xa-don-va-vong-treo"])) == {
        "pull-up-bar",
        "gymnastic-rings",
    }
