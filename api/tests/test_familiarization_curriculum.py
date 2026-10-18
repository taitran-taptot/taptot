from app.core.exceptions import BadRequestError
from app.schemas.plans import PlanDayIn, PlanExerciseIn, UpdatePlanDayIn
from app.services.workout_generation.familiarization_curriculum import (
    FIRST_PUSH_PULL_BAR_START_DAY,
    FIRST_PUSH_PULL_DAYS,
    FIRST_PUSH_PULL_EARLY_BAR_DAY,
    FIRST_PUSH_PULL_INVERTED_ROW_DAY,
    FIRST_PUSH_PULL_SCAPULAR_DAY,
    _FIRST_PUSH_PULL_TRAIN_DAYS,
    _TRAIN_DAYS_60,
    _baseline_capacity_zero,
    _day_title,
    _families_for_day,
    _familiarization_required_keys,
    _female_can_knee,
    _female_l1_prescription,
    _first_match,
    _first_push_pull_training_exercises,
    _is_excluded,
    _keep_for_nhap_mon,
    _parse_start_time,
    _parse_weekdays,
    _pull_prep_for_ordinal,
    _pull_prep_keys,
    _raise_if_catalog_missing,
    _session_role,
    _week_from_day,
    _pick_inverted_row,
    expand_familiarization_weeks,
    progression_step_for_week,
)


class _NamedEx:
    def __init__(self, name_vi, name_en, venue="gym", notes_vi=None):
        self.name_vi = name_vi
        self.name_en = name_en
        self.venue = venue
        self.notes_vi = notes_vi


def test_nhap_mon_keeps_wall_push_and_cap_sach_row():
    wall = _NamedEx("Chống đẩy tường", "Wall Push-up", venue="gym")
    row = _NamedEx("Chèo cặp sách hai tay", "Bent-Over Backpack Row", venue="gym")
    cable = _NamedEx("Kéo cáp máy", "Cable Seated Row", venue="gym")
    assert _is_excluded(wall) is False
    assert _is_excluded(row) is False
    assert _keep_for_nhap_mon(wall) is True
    assert _keep_for_nhap_mon(row) is True
    assert _keep_for_nhap_mon(cable) is False
    band_squat = _NamedEx("Ngồi xổm với dây", "Band Squat", venue="home")
    assert _is_excluded(band_squat) is True
    assert _keep_for_nhap_mon(band_squat) is False
    found = _first_match(
        [row],
        require=("backpack", "balo", "ba lo", "cap sach"),
        predicate=lambda ex: True,
    )
    assert found is row


def test_first_push_pull_has_exact_28_day_cadence():
    assert FIRST_PUSH_PULL_DAYS == 28
    assert len(_FIRST_PUSH_PULL_TRAIN_DAYS) == 12
    assert _TRAIN_DAYS_60 == _FIRST_PUSH_PULL_TRAIN_DAYS
    assert _FIRST_PUSH_PULL_TRAIN_DAYS[:3] == (1, 3, 5)
    assert _TRAIN_DAYS_60[-2:] == (24, 26)
    assert _session_role(1) == "full"
    assert _session_role(2) == "full"
    assert _session_role(3) == "full"


def test_pull_prep_rotates_backpack_with_floor():
    catalog = {
        "backpack_bent": object(),
        "backpack_one_arm": object(),
        "floor_pull": object(),
    }
    assert _pull_prep_keys(catalog, day=1) == [
        "backpack_bent",
        "backpack_one_arm",
        "floor_pull",
    ]
    assert _pull_prep_for_ordinal(catalog, 1, day=1)[0] == "backpack_bent"
    assert _pull_prep_for_ordinal(catalog, 2, day=1)[0] == "backpack_one_arm"
    assert _pull_prep_for_ordinal(catalog, 3, day=1)[0] == "floor_pull"
    assert _pull_prep_for_ordinal(catalog, 4, day=1)[0] == "backpack_bent"
    assert "balo" in _pull_prep_for_ordinal(catalog, 1, day=1)[2].lower()
    assert "inverted_row" not in _pull_prep_keys(catalog, day=14)


def test_pull_prep_stays_on_backpack_through_week_three():
    catalog = {
        "inverted_row": object(),
        "backpack_bent": object(),
        "floor_pull": object(),
    }
    assert _pull_prep_keys(catalog, day=14) == ["backpack_bent", "floor_pull"]
    assert _pull_prep_keys(catalog, day=15) == ["backpack_bent", "floor_pull"]
    assert _pull_prep_for_ordinal(catalog, 1, day=15)[0] == "backpack_bent"
    blob = " ".join(_pull_prep_for_ordinal(catalog, 1, day=15)).lower()
    assert "inverted" not in blob


def test_plan_schemas_accept_day_60():
    assert PlanDayIn(day_number=60).day_number == 60
    assert UpdatePlanDayIn(day_number=60).day_number == 60


def test_first_rep_path_reaches_test_variations_by_week_eight():
    assert progression_step_for_week("first_push_pull", "push", 0, 1) == 0
    assert progression_step_for_week("first_push_pull", "push", 0, 8) == 5
    assert progression_step_for_week("first_push_pull", "pull", 0, 8) == 6


def test_path_caps_prevent_out_of_catalog_progression():
    assert progression_step_for_week("first_push_pull", "push", 5, 8) == 5
    assert progression_step_for_week("first_push_pull", "pull", 6, 8) == 6
    assert progression_step_for_week("basic_foundation", "push", 5, 8) == 5


def test_gender_max_step_clamps_female_first_rep_path():
    assert progression_step_for_week("first_push_pull", "push", 0, 8, max_step=1) == 1
    assert progression_step_for_week("first_push_pull", "pull", 0, 8, max_step=0) == 0


def test_first_push_pull_session_is_always_full_body():
    assert _families_for_day("first_push_pull", 0) == ["push", "pull", "squat", "plank", "run"]
    assert _families_for_day("first_push_pull", 1) == ["push", "pull", "squat", "plank", "run"]
    assert _families_for_day("first_push_pull", 2) == ["push", "pull", "squat", "plank", "run"]


def test_weekday_and_time_title_format():
    assert _parse_weekdays([1, 3, 5], 3) == [1, 3, 5]
    assert _parse_start_time("19:30") == "19:30"
    title = _day_title(
        week=1,
        day_index=0,
        phase="Làm quen kỹ thuật",
        weekdays=[1, 3, 5],
        start_time="18:00",
    )
    assert title == "Tuần 1 · Buổi 1 — Làm quen kỹ thuật"


def test_expand_templates_renumbers_without_meals():
    templates: list[list[PlanDayIn]] = []
    for week in range(1, 9):
        templates.append(
            [
                PlanDayIn(
                    day_number=day,
                    title_vi=f"Tuần {week} · Buổi {day}",
                    exercises=[
                        PlanExerciseIn(
                            exercise_id=day,
                            sets=2,
                            reps="6–8",
                            rest_seconds=90,
                            notes_vi="RIR 3",
                        )
                    ],
                )
                for day in (1, 2, 3)
            ]
        )
    expanded = expand_familiarization_weeks(templates)
    assert len(expanded) == 24
    assert [day.day_number for day in expanded] == list(range(1, 25))
    assert all(not day.meals for day in expanded)


class _Row:
    def __init__(self, exercise_id: int):
        self.id = exercise_id


_CATALOG_KEYS = (
    "wall_push",
    "incline_push",
    "knee_push",
    "strict_push",
    "decline_push",
    "diamond_push",
    "backpack_bent",
    "backpack_one_arm",
    "floor_pull",
    "inverted_row",
    "elevated_row",
    "band_pull",
    "scapular",
    "dead_hang",
    "strict_pull",
    "negative_pull",
    "chin_hold_negative",
    "squat",
    "lunge",
    "walking_lunge",
    "bulgarian",
    "jump_squat",
    "box_squat",
    "glute_bridge",
    "glute_single",
    "hip_thrust",
    "backpack_rdl",
    "backpack_rdl_sl",
    "backpack_gm",
    "hand_plank",
    "plank",
    "hollow",
    "cardio",
    "bird_dog",
    "jumping_jack",
)
_FOUNDATION_CATALOG = {
    key: _Row(index) for index, key in enumerate(_CATALOG_KEYS, start=1)
}


def _main_ids(items):
    return {int(row.exercise_id) for row in items if row.section != "warmup"}


def _blob(items):
    return " ".join(f"{row.reps} {row.notes_vi}" for row in items).lower()


def test_l1_warmup_includes_jumping_jack_both_genders():
    for gender in ("male", "female"):
        items = _first_push_pull_training_exercises(
            _FOUNDATION_CATALOG, gender=gender, day=1, ordinal=1
        )
        warmups = [row for row in items if row.section == "warmup"]
        assert len(warmups) == 1
        jj = warmups[0]
        assert jj.exercise_id == _FOUNDATION_CATALOG["jumping_jack"].id
        assert jj.sets == 3
        assert jj.rest_seconds == 90
        assert "20–40" in (jj.reps or "")


def test_obese_l1_warmup_still_uses_jumping_jack():
    items = _first_push_pull_training_exercises(
        _FOUNDATION_CATALOG, gender="male", day=1, ordinal=1, bmi_band="obese_1"
    )
    warmups = [row for row in items if row.section == "warmup"]
    assert len(warmups) == 1
    jj = warmups[0]
    assert jj.exercise_id == _FOUNDATION_CATALOG["jumping_jack"].id
    assert jj.sets == 3
    assert jj.rest_seconds == 90
    assert "20–40" in (jj.reps or "")


def test_l1_early_weeks_use_backpack_not_inverted_or_bar():
    items = _first_push_pull_training_exercises(
        _FOUNDATION_CATALOG, gender="male", day=3, ordinal=2
    )
    ids = _main_ids(items)
    assert _FOUNDATION_CATALOG["backpack_bent"].id in ids
    assert _FOUNDATION_CATALOG["inverted_row"].id not in ids
    assert _FOUNDATION_CATALOG["dead_hang"].id not in ids
    assert _FOUNDATION_CATALOG["scapular"].id not in ids
    assert _FOUNDATION_CATALOG["chin_hold_negative"].id not in ids
    assert _FOUNDATION_CATALOG["negative_pull"].id not in ids
    blob = _blob(items)
    assert "cằm" not in blob
    assert "negative" not in blob


def test_l1_week_three_introduces_one_arm_backpack():
    before = _first_push_pull_training_exercises(
        _FOUNDATION_CATALOG, gender="male", day=12, ordinal=6
    )
    after = _first_push_pull_training_exercises(
        _FOUNDATION_CATALOG, gender="male", day=17, ordinal=8
    )
    assert _FOUNDATION_CATALOG["inverted_row"].id not in _main_ids(before)
    assert _FOUNDATION_CATALOG["inverted_row"].id not in _main_ids(after)
    assert _FOUNDATION_CATALOG["backpack_one_arm"].id in _main_ids(after)
    assert _FOUNDATION_CATALOG["dead_hang"].id not in _main_ids(after)


def test_l1_never_adds_hang_or_inverted_row():
    male = _first_push_pull_training_exercises(
        _FOUNDATION_CATALOG, gender="male", day=17, ordinal=8
    )
    female = _first_push_pull_training_exercises(
        _FOUNDATION_CATALOG, gender="female", day=17, ordinal=8
    )
    for items in (male, female):
        ids = _main_ids(items)
        assert _FOUNDATION_CATALOG["inverted_row"].id not in ids
        assert _FOUNDATION_CATALOG["dead_hang"].id not in ids
        assert _FOUNDATION_CATALOG["scapular"].id not in ids
        assert "cằm" not in _blob(items)
        assert "negative" not in _blob(items)


def test_l1_last_session_is_deload_full_body():
    male = _first_push_pull_training_exercises(
        _FOUNDATION_CATALOG, gender="male", day=26, ordinal=12
    )
    female = _first_push_pull_training_exercises(
        _FOUNDATION_CATALOG, gender="female", day=26, ordinal=12
    )
    for items in (male, female):
        main = [row for row in items if row.section == "main"]
        assert main
        assert all(int(row.sets or 0) <= 2 for row in main)
        assert "deload" in _blob(items)
        ids = _main_ids(items)
        assert _FOUNDATION_CATALOG["inverted_row"].id not in ids
        assert _FOUNDATION_CATALOG["backpack_one_arm"].id in ids or _FOUNDATION_CATALOG["backpack_bent"].id in ids


def test_l1_week_four_midweek_is_not_deload():
    male = _first_push_pull_training_exercises(
        _FOUNDATION_CATALOG, gender="male", day=22, ordinal=10
    )
    main = [row for row in male if row.section == "main"]
    assert any(int(row.sets or 0) >= 3 for row in main)
    assert "deload" not in _blob(male)


def test_l1_week_three_prefers_single_leg_glute_over_backpack_rdl():
    items = _first_push_pull_training_exercises(
        _FOUNDATION_CATALOG, gender="male", day=17, ordinal=8
    )
    ids = _main_ids(items)
    assert _FOUNDATION_CATALOG["glute_single"].id in ids
    assert _FOUNDATION_CATALOG["backpack_rdl"].id not in ids


def test_run_ladder_prefers_trail_run_not_walking_lunge():
    from app.services.workout_generation.familiarization_curriculum import (
        _build_run_ladder,
    )

    class _Ex:
        def __init__(self, eid, name_vi, name_en):
            self.id = eid
            self.name_vi = name_vi
            self.name_en = name_en
            self.notes_vi = None

    pool = [
        _Ex(1, "Chùng chân bước đi", "Walking Lunge"),
        _Ex(2, "Chạy bền/Đi bộ nhanh", "Trail Run"),
        _Ex(3, "Đi bộ tại chỗ", "March in Place"),
    ]
    ladder = _build_run_ladder(pool)
    assert ladder
    assert ladder[0][1].name_en == "Trail Run"
    assert all(row.name_en != "Walking Lunge" for _, row in ladder)


def test_plank_ladder_prefers_elbow_over_hand():
    from app.services.workout_generation.familiarization_curriculum import (
        _build_plank_ladder,
    )

    class _Ex:
        def __init__(self, eid, name_vi, name_en):
            self.id = eid
            self.name_vi = name_vi
            self.name_en = name_en
            self.notes_vi = None

    pool = [
        _Ex(277, "Chống người chống thẳng tay", "Hand Plank"),
        _Ex(671, "Chống người chống khuỷu", "Front Plank on Elbows"),
    ]
    ladder = _build_plank_ladder(pool)
    assert ladder
    assert ladder[-1][1].id == 671
    assert all(row.id != 277 for _, row in ladder)








def test_week_from_day_and_female_can_knee():
    assert _week_from_day(1) == 1
    assert _week_from_day(14) == 2
    assert _week_from_day(15) == 3
    assert _week_from_day(22) == 4
    assert _week_from_day(57) == 4
    assert _female_can_knee({}) is False
    assert _female_can_knee({"pushup_variant": "knee", "pushups_max": 3}) is False
    assert _female_can_knee({"pushup_variant": "knee", "pushups_max": 4}) is True
    assert _female_can_knee({"pushup_variant": "wall", "pushups_max": 10}) is False


def test_female_zero_baseline_push_uses_wall_incline_before_week_four():
    for day, ordinal in ((1, 1), (8, 4), (15, 7)):
        items = _first_push_pull_training_exercises(
            _FOUNDATION_CATALOG,
            gender="female",
            day=day,
            ordinal=ordinal,
            can_knee=False,
        )
        ids = _main_ids(items)
        if day <= 8:
            assert _FOUNDATION_CATALOG["knee_push"].id not in ids
        assert (
            _FOUNDATION_CATALOG["wall_push"].id in ids
            or _FOUNDATION_CATALOG["knee_push"].id in ids
        )


def test_female_zero_baseline_week_four_last_session_is_deload():
    items = _first_push_pull_training_exercises(
        _FOUNDATION_CATALOG,
        gender="female",
        day=26,
        ordinal=12,
        can_knee=False,
    )
    main = [row for row in items if row.section == "main"]
    assert all(int(row.sets or 0) <= 2 for row in main)
    blob = _blob(items)
    assert "deload" in blob


def test_female_zero_baseline_week_three_uses_knee():
    items = _first_push_pull_training_exercises(
        _FOUNDATION_CATALOG,
        gender="female",
        day=15,
        ordinal=7,
        can_knee=False,
    )
    ids = _main_ids(items)
    assert _FOUNDATION_CATALOG["knee_push"].id in ids


def test_male_week_four_last_session_is_deload():
    week4_last = _first_push_pull_training_exercises(
        _FOUNDATION_CATALOG, gender="male", day=26, ordinal=12
    )
    week3 = _first_push_pull_training_exercises(
        _FOUNDATION_CATALOG, gender="male", day=17, ordinal=8
    )
    main = [row for row in week4_last if row.section == "main"]
    assert main
    assert all(int(row.sets or 0) <= 2 for row in main)
    assert "deload" in _blob(week4_last)
    week3_main = [row for row in week3 if row.section == "main"]
    assert any(int(row.sets or 0) >= 3 for row in week3_main)


def test_female_can_knee_starts_knee_earlier():
    week3 = _first_push_pull_training_exercises(
        _FOUNDATION_CATALOG,
        gender="female",
        day=15,
        ordinal=7,
        can_knee=True,
    )
    assert _FOUNDATION_CATALOG["knee_push"].id in _main_ids(week3)


def test_female_squat_and_cardio_every_train_day():
    week2 = _first_push_pull_training_exercises(
        _FOUNDATION_CATALOG,
        gender="female",
        day=10,
        ordinal=5,
        can_knee=False,
    )
    assert _FOUNDATION_CATALOG["dead_hang"].id not in _main_ids(week2)
    assert _FOUNDATION_CATALOG["squat"].id in _main_ids(week2)
    blob = " ".join(row.reps or "" for row in week2)
    assert "phút" in blob


def test_female_full_day_includes_plank():
    full = _first_push_pull_training_exercises(
        _FOUNDATION_CATALOG,
        gender="female",
        day=5,
        ordinal=3,
        can_knee=False,
    )
    assert _FOUNDATION_CATALOG["plank"].id in _main_ids(full) or _FOUNDATION_CATALOG[
        "hand_plank"
    ].id in _main_ids(full)


def test_female_prescription_ramps_push_reps():
    w1 = _female_l1_prescription(1, can_knee=False)
    w7 = _female_l1_prescription(7, can_knee=False)
    assert w1["push_keys"][0] in {"wall_push", "incline_push"}
    assert "knee_push" in w7["push_keys"]
    assert "8–10" in str(w7["push_reps"])


def test_underweight_cardio_is_shorter():
    items = _first_push_pull_training_exercises(
        _FOUNDATION_CATALOG,
        gender="male",
        day=1,
        ordinal=1,
        bmi_band="underweight",
    )
    blob = _blob(items)
    assert "8–10 phút" in blob


def test_obese_l1_stays_on_wall():
    items = _first_push_pull_training_exercises(
        _FOUNDATION_CATALOG,
        gender="male",
        day=17,
        ordinal=8,
        bmi_band="obese_1",
    )
    ids = _main_ids(items)
    assert _FOUNDATION_CATALOG["strict_push"].id not in ids
    assert _FOUNDATION_CATALOG["wall_push"].id in ids


def test_l1_male_week_three_stays_on_knee_not_floor():
    items = _first_push_pull_training_exercises(
        _FOUNDATION_CATALOG, gender="male", day=17, ordinal=8
    )
    ids = _main_ids(items)
    assert _FOUNDATION_CATALOG["knee_push"].id in ids
    assert _FOUNDATION_CATALOG["strict_push"].id not in ids


def test_pick_inverted_row_keeps_table_without_bar_and_bar_when_owned():
    assert _pick_inverted_row(
        has_bar_or_rings=False, ring="ring", bar="bar", table="table"
    ) == "table"
    assert _pick_inverted_row(
        has_bar_or_rings=True, ring=None, bar="bar", table="table"
    ) == "bar"
    assert _pick_inverted_row(
        has_bar_or_rings=True, ring=None, bar=None, table="table"
    ) == "table"


def test_required_keys_omit_dead_hang_without_bar():
    no_bar = _familiarization_required_keys(
        gender="male", has_bar_or_rings=False, has_backpack=True
    )
    assert "dead_hang" not in no_bar
    assert "inverted_row" not in no_bar
    assert "backpack_bent" in no_bar
    with_bar = _familiarization_required_keys(
        gender="female", has_bar_or_rings=True, has_backpack=True
    )
    assert "dead_hang" not in with_bar
    assert "strict_push" not in with_bar
    assert "inverted_row" not in with_bar


def test_catalog_missing_required_raises_kho_bai():
    rows = {
        "wall_push": object(),
        "knee_push": None,
        "squat": object(),
        "plank": object(),
        "cardio": object(),
        "jumping_jack": object(),
        "glute_bridge": object(),
        "floor_pull": object(),
        "backpack_bent": object(),
    }
    required = _familiarization_required_keys(
        gender="female", has_bar_or_rings=False, has_backpack=True
    )
    try:
        _raise_if_catalog_missing(rows, required)
    except BadRequestError as exc:
        assert "Kho bài tập thiếu bài" in str(exc)
        assert "chống đẩy quỳ gối" in str(exc)
    else:
        raise AssertionError("expected BadRequestError")






def test_baseline_capacity_zero_only_when_keys_present():
    assert _baseline_capacity_zero({}, "pushups_max") is False
    assert _baseline_capacity_zero({"pushups_max": 0}, "pushups_max") is True
    assert _baseline_capacity_zero({"pushups_max": 8}, "pushups_max") is False
    assert (
        _baseline_capacity_zero(
            {"pullups_max": 0, "inverted_rows_max": 6},
            "pullups_max",
            "inverted_rows_max",
        )
        is False
    )
    assert (
        _baseline_capacity_zero(
            {"pullups_max": 0, "inverted_rows_max": 0},
            "pullups_max",
            "inverted_rows_max",
        )
        is True
    )


def test_attach_meals_skips_without_food_ids():
    from app.services.workout_generation.familiarization_curriculum import (
        _attach_familiarization_meals,
    )

    templates = [
        [
            PlanDayIn(
                day_number=1,
                title_vi="Ngày 1",
                split_role="recovery",
                exercises=[],
                meals=[],
            )
        ]
    ]
    out, result = _attach_familiarization_meals(None, {"food_ids": []}, templates, None)
    assert out is templates
    assert result is None


def test_attach_meals_applies_user_pool(monkeypatch):
    from app.schemas.plans import PlanMealIn
    from app.services.workout_generation.familiarization_curriculum import (
        _attach_familiarization_meals,
    )

    templates = [
        [
            PlanDayIn(
                day_number=day,
                title_vi=f"Ngày {day}",
                split_role="Full Body" if day % 2 else "recovery",
                exercises=[],
                meals=[],
            )
            for day in range(1, 8)
        ]
    ]

    class _Result:
        schedule = object()
        templates_by_kind = {"fullbody": object()}
        templates = []
        rest_day_template = None
        foods_by_id = {}
        warning_vi = "Thực đơn ráp từ món bạn chọn"

    def _fake_generate(*_args, **_kwargs):
        return _Result()

    def _fake_apply(days, *_args, **_kwargs):
        meal = PlanMealIn(food_id=11, meal_type="lunch", servings=1)
        return [day.model_copy(update={"meals": [meal]}) for day in days]

    monkeypatch.setattr(
        "app.services.workout_generation.familiarization_curriculum.estimate_targets",
        lambda *_args, **_kwargs: object(),
    )
    monkeypatch.setattr(
        "app.services.workout_generation.familiarization_curriculum.generate_meals",
        _fake_generate,
    )
    monkeypatch.setattr(
        "app.services.workout_generation.familiarization_curriculum.apply_meals_with_schedule",
        _fake_apply,
    )

    out, result = _attach_familiarization_meals(
        None,
        {
            "food_ids": [11, 12, 13, 14],
            "height_cm": 170,
            "weight_kg": 70,
            "gender": "male",
            "age": 25,
            "activity": "light",
        },
        templates,
        {"goal": "maintain"},
    )
    assert result.warning_vi.startswith("Thực đơn ráp")
    assert len(out) == 1
    assert all(day.meals for day in out[0])
