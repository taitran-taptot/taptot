from app.services.plan_notes import pack_day_notes, unpack_day_notes


def test_pack_unpack_meals_flexible():
    raw = pack_day_notes(meal_notes={"lunch": "no"}, meals_flexible=True)
    assert raw
    mn, sn, free, role, flex = unpack_day_notes(raw)
    assert mn["lunch"] == "no"
    assert sn == {}
    assert free is None
    assert role is None
    assert flex is True


def test_unpack_omits_flexible_when_false():
    raw = pack_day_notes(split_role="push", meals_flexible=False)
    assert raw
    assert "meals_flexible" not in raw
    *_, flex = unpack_day_notes(raw)
    assert flex is False
