from app.services.search_service import expand_search_equipment_keys


def test_resistance_band_group_expands_full_family():
    keys, has_band = expand_search_equipment_keys(["resistance-band"])
    assert has_band is True
    assert keys == [
        "resistance-band",
        "resistance-band-1",
        "resistance-band-2",
        "day-mini-band",
    ]


def test_loop_or_tube_slug_also_expands_family():
    keys, has_band = expand_search_equipment_keys(["resistance-band-1", "dumbbell"])
    assert has_band is True
    assert "dumbbell" in keys
    assert "resistance-band-2" in keys
    assert "day-mini-band" in keys


def test_non_band_keys_pass_through():
    keys, has_band = expand_search_equipment_keys(["dumbbell", "pull-up-bar"])
    assert has_band is False
    assert keys == ["dumbbell", "pull-up-bar"]
