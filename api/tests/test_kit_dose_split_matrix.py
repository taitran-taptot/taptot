"""Gender × sessions split occupancy vs band/DB load hints (no OpenAI)."""

from __future__ import annotations

import pytest

from app.services.schedule_spec_master import (
    day_label_to_split_role,
    expand_week_days,
    experience_to_master_key,
    lookup_week_split,
)
from app.services.workout_generation.dose_bounds import (
    dose_bounds_for_item,
    free_weight_preset_reps,
)
from app.services.workout_generation.load_estimate import (
    BAND_LEVEL_ORDER,
    apply_challenge_load,
    compound_working_reps,
    hint_for_item,
    isolation_working_reps,
    progress_band_prescription,
    progress_db_prescription,
    suggest_band_level,
)

GENDERS = ("male", "female")
SESSIONS = (2, 3, 4, 5, 6)

DB_BASELINE = {
    "test_kit": "dumbbell",
    "db_press_reps": 16,
    "db_press_kg": 10,
    "db_row_reps": 16,
    "db_row_kg": 10,
    "goblet_reps": 16,
    "goblet_kg": 20,
    "plank_seconds": 40,
}
BAND_BASELINE = {
    "test_kit": "band",
    "pushups_max": 16,
    "pullups_max": 16,
    "squats_max": 16,
    "band_level_push": "yellow",
    "band_level_pull": "black",
    "band_level_squat": "blue",
    "plank_seconds": 40,
}

STUBS: dict[str, list[dict]] = {
    "push": [
        {
            "name_en": "Dumbbell Bench Press",
            "name_vi": "Đẩy ngực tạ đơn",
            "movement_role": "compound",
            "movement_pattern": "h_push",
            "equipment_slugs": ["dumbbell"],
        },
        {
            "name_en": "Band Chest Press",
            "name_vi": "Đẩy ngực dây kháng lực",
            "movement_role": "compound",
            "movement_pattern": "h_push",
            "equipment_slugs": ["resistance-band"],
        },
    ],
    "pull": [
        {
            "name_en": "Dumbbell Row",
            "name_vi": "Chèo tạ đơn",
            "movement_role": "compound",
            "movement_pattern": "h_pull",
            "equipment_slugs": ["dumbbell"],
        },
        {
            "name_en": "Band Pulldown",
            "name_vi": "Kéo xô dây kháng lực",
            "movement_role": "compound",
            "movement_pattern": "v_pull",
            "equipment_slugs": ["resistance-band"],
        },
    ],
    "legs": [
        {
            "name_en": "Goblet Squat",
            "name_vi": "Squat tạ ấm",
            "movement_role": "compound",
            "movement_pattern": "squat",
            "equipment_slugs": ["dumbbell"],
        },
        {
            "name_en": "Band Squat",
            "name_vi": "Squat dây kháng lực",
            "movement_role": "compound",
            "movement_pattern": "squat",
            "equipment_slugs": ["resistance-band"],
        },
    ],
    "upper": [
        {
            "name_en": "Dumbbell Overhead Press",
            "name_vi": "Đẩy vai tạ đơn",
            "movement_role": "compound",
            "movement_pattern": "v_push",
            "equipment_slugs": ["dumbbell"],
        },
        {
            "name_en": "Band Row",
            "name_vi": "Chèo dây kháng lực",
            "movement_role": "compound",
            "movement_pattern": "h_pull",
            "equipment_slugs": ["resistance-band"],
        },
    ],
    "core": [
        {
            "name_en": "Plank",
            "name_vi": "Plank",
            "movement_role": "core",
            "movement_pattern": "core",
        },
    ],
    "fb": [
        {
            "name_en": "Goblet Squat",
            "name_vi": "Squat tạ ấm",
            "movement_role": "compound",
            "movement_pattern": "squat",
            "equipment_slugs": ["dumbbell"],
        },
    ],
}

ISO_PRESS = {
    "name_en": "Dumbbell Fly",
    "name_vi": "Ép ngực tạ đơn",
    "movement_role": "isolation",
    "movement_pattern": "h_push",
    "equipment_slugs": ["dumbbell"],
}
ISO_BAND = {
    "name_en": "Band Chest Fly",
    "name_vi": "Ép ngực dây kháng lực",
    "movement_role": "isolation",
    "movement_pattern": "h_push",
    "equipment_slugs": ["resistance-band"],
}


def _roles(gender: str, sessions: int) -> tuple[str, ...]:
    code = lookup_week_split(
        experience=experience_to_master_key(2),
        sessions=sessions,
        gender=gender,
        location="home",
        home_equip="with_equip",
    )
    assert code
    labels = expand_week_days(code)
    assert len(labels) == sessions
    return tuple(day_label_to_split_role(lbl) for lbl in labels)


def _db_loaded(gender: str) -> dict:
    return apply_challenge_load(
        DB_BASELINE,
        weight_kg=70 if gender == "male" else 56,
        gender=gender,
        equipment_list=["dumbbell"],
    )


def _band_loaded(gender: str) -> dict:
    return apply_challenge_load(
        BAND_BASELINE,
        weight_kg=70 if gender == "male" else 56,
        gender=gender,
        equipment_list=["resistance-band"],
    )


def _bounds(item: dict, loaded: dict, *, level: int = 2, challenge: bool = True) -> dict:
    return dose_bounds_for_item(
        item,
        experience_level=level,
        fitness_baseline=loaded,
        plan_section="main",
        home_session=True,
        challenge=challenge,
    )


@pytest.mark.parametrize("gender", GENDERS)
@pytest.mark.parametrize("sessions", SESSIONS)
def test_split_cell_db_and_band_dose(gender: str, sessions: int):
    roles = _roles(gender, sessions)
    assert set(roles) <= {"push", "pull", "legs", "upper", "core", "fb"}
    db = _db_loaded(gender)
    band = _band_loaded(gender)
    for role in roles:
        stubs = STUBS[role]
        if role == "core":
            plank = _bounds(stubs[0], db)
            assert plank["work_mode"] == "hold"
            assert plank["sets_min"] == 2
            assert plank["seconds_min"] == 20
            assert plank["seconds_max"] == 25
            continue
        for item in stubs:
            slugs = item.get("equipment_slugs") or []
            loaded = band if "resistance-band" in slugs else db
            hint = hint_for_item(item, loaded["_load_hints"])
            assert hint is not None, item
            bounds = _bounds(item, loaded)
            assert bounds["work_mode"] == "reps"
            assert bounds["sets_min"] == 2
            assert bounds["sets_max"] == 4
            if "resistance-band" in slugs:
                assert bounds.get("band_level") == hint.get("band_level")
                assert (bounds["reps_min"], bounds["reps_max"]) == free_weight_preset_reps(
                    experience_level=2, role="compound"
                )
            else:
                assert bounds.get("load_kg_each") == hint.get("load_kg_each")
                assert (bounds["reps_min"], bounds["reps_max"]) == free_weight_preset_reps(
                    experience_level=2, role="compound"
                )


@pytest.mark.parametrize("gender", GENDERS)
def test_isolation_and_warmup_step_down(gender: str):
    db = _db_loaded(gender)
    band = _band_loaded(gender)
    iso_db = _bounds(ISO_PRESS, db)
    assert iso_db.get("load_kg_each") == 5.0
    assert (iso_db["reps_min"], iso_db["reps_max"]) == free_weight_preset_reps(
        experience_level=2, role="isolation"
    )

    iso_band = _bounds(ISO_BAND, band)
    assert iso_band.get("band_level") == suggest_band_level("yellow", role="isolation")
    assert (iso_band["reps_min"], iso_band["reps_max"]) == free_weight_preset_reps(
        experience_level=2, role="isolation"
    )

    kg, _cal = progress_db_prescription(
        10, 16, slot="press", section="warmup", role="warmup"
    )
    assert kg == 5.0
    color, extra = progress_band_prescription(
        "black", 16, section="warmup", role="warmup"
    )
    assert color == suggest_band_level("black", section="warmup")
    assert extra is None

    primer = dose_bounds_for_item(
        STUBS["push"][0],
        experience_level=2,
        fitness_baseline=db,
        plan_section="warmup",
        home_session=True,
        challenge=True,
    )
    assert primer["work_mode"] == "reps"
    assert primer["sets_min"] == 2


@pytest.mark.parametrize("sessions", SESSIONS)
def test_same_numeric_tests_gender_invariant_load(sessions: int):
    male_db = _db_loaded("male")
    female_db = _db_loaded("female")
    male_band = _band_loaded("male")
    female_band = _band_loaded("female")
    roles = set(_roles("male", sessions)) | set(_roles("female", sessions))
    for role in roles:
        for item in STUBS[role]:
            if role == "core":
                a = _bounds(item, male_db)
                b = _bounds(item, female_db)
                assert a["seconds_min"] == b["seconds_min"]
                assert a["seconds_max"] == b["seconds_max"]
                continue
            slugs = item.get("equipment_slugs") or []
            if "resistance-band" in slugs:
                a = _bounds(item, male_band)
                b = _bounds(item, female_band)
                assert a.get("band_level") == b.get("band_level")
            else:
                a = _bounds(item, male_db)
                b = _bounds(item, female_db)
                assert a.get("load_kg_each") == b.get("load_kg_each")
            assert (a["reps_min"], a["reps_max"]) == (b["reps_min"], b["reps_max"])
            assert a["sets_max"] == b["sets_max"]


@pytest.mark.parametrize("level", (1, 2, 3))
def test_challenge_sets_max_by_level(level: int):
    loaded = _db_loaded("male")
    bounds = _bounds(STUBS["push"][0], loaded, level=level, challenge=True)
    assert bounds["sets_min"] == 2
    assert bounds["sets_max"] == (3 if level <= 1 else 4)


@pytest.mark.parametrize("amrap", (8, 16, 25))
@pytest.mark.parametrize("slot,test_kg", (("press", 10.0), ("row", 10.0), ("squat", 20.0)))
def test_db_amrap_ladder(amrap: int, slot: str, test_kg: float):
    work, cal = progress_db_prescription(
        test_kg, amrap, slot=slot, section="main", role="compound"
    )
    iso, iso_cal = progress_db_prescription(
        test_kg, amrap, slot=slot, section="main", role="isolation"
    )
    assert iso_cal == cal
    if amrap == 16:
        assert work == test_kg
        assert cal == 16
        assert iso == (5.0 if slot != "squat" else 15.0)
    elif amrap == 8:
        assert work == (7.5 if slot != "squat" else 17.5)
        assert cal == 15
        assert iso < work or iso == work == (2.5 if slot != "squat" else 2.5)
    else:
        assert work == (12.5 if slot != "squat" else 22.5)
        assert cal == 15
        assert iso == (7.5 if slot != "squat" else 17.5)

    item = {
        "press": STUBS["push"][0],
        "row": STUBS["pull"][0],
        "squat": STUBS["legs"][0],
    }[slot]
    key = {
        "press": ("db_press_reps", "db_press_kg"),
        "row": ("db_row_reps", "db_row_kg"),
        "squat": ("goblet_reps", "goblet_kg"),
    }[slot]
    loaded = apply_challenge_load(
        {"test_kit": "dumbbell", key[0]: amrap, key[1]: test_kg},
        weight_kg=70,
        equipment_list=["dumbbell"],
    )
    bounds = _bounds(item, loaded)
    assert bounds.get("load_kg_each") == work
    lo, hi = free_weight_preset_reps(experience_level=2, role="compound")
    assert bounds["reps_min"] == lo
    assert bounds["reps_max"] == hi


@pytest.mark.parametrize("level", (1, 2, 3))
@pytest.mark.parametrize("role", ("compound", "isolation"))
def test_home_non_challenge_uses_free_weight_preset(level: int, role: str):
    item = dict(ISO_PRESS if role == "isolation" else STUBS["push"][0])
    bounds = _bounds(item, {"pushups_max": 20}, level=level, challenge=False)
    lo, hi = free_weight_preset_reps(experience_level=level, role=role)
    assert (bounds["reps_min"], bounds["reps_max"]) == (lo, hi)
    assert bounds["sets_max"] == 4
    assert bounds.get("load_kg_each") is None


@pytest.mark.parametrize("color", BAND_LEVEL_ORDER)
@pytest.mark.parametrize("amrap", (8, 16, 25))
@pytest.mark.parametrize("slot", ("push", "pull", "squat"))
def test_band_color_amrap_slots(color: str, amrap: int, slot: str):
    working, extra = progress_band_prescription(
        color, amrap, section="main", role="compound"
    )
    iso, iso_extra = progress_band_prescription(
        color, amrap, section="main", role="isolation"
    )
    wu, wu_extra = progress_band_prescription(
        color, amrap, section="warmup", role="warmup"
    )
    assert iso == suggest_band_level(working, role="isolation")
    assert wu == suggest_band_level(working, section="warmup")
    assert iso_extra is None and wu_extra is None
    if color == "black" and amrap > 20:
        assert extra == "yellow"
        assert working == "black"
    else:
        assert extra is None

    base = {
        "test_kit": "band",
        "pushups_max": amrap,
        "pullups_max": amrap,
        "squats_max": amrap,
        "band_level_push": color,
        "band_level_pull": color,
        "band_level_squat": color,
    }
    loaded = apply_challenge_load(
        base, weight_kg=70, equipment_list=["resistance-band"]
    )
    item = {
        "push": STUBS["push"][1],
        "pull": STUBS["pull"][1],
        "squat": STUBS["legs"][1],
    }[slot]
    bounds = _bounds(item, loaded)
    assert bounds.get("band_level") == working
    assert bounds["sets_min"] == 2
    assert bounds["reps_min"] >= 6
    assert bounds["reps_max"] >= bounds["reps_min"]
