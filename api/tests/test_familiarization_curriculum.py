from app.schemas.plans import PlanDayIn, PlanExerciseIn, UpdatePlanDayIn
from app.services.workout_generation.familiarization_curriculum import (
    FIRST_PUSH_PULL_BAR_START_DAY,
    FIRST_PUSH_PULL_DAYS,
    FIRST_PUSH_PULL_EARLY_BAR_DAY,
    FIRST_PUSH_PULL_INVERTED_ROW_DAY,
    FIRST_PUSH_PULL_SCAPULAR_DAY,
    _FIRST_PUSH_PULL_TRAIN_DAYS,
    _TRAIN_DAYS_60,
    _advanced_foundation_training_exercises,
    _basic_foundation_training_exercises,
    _day_title,
    _families_for_day,
    _female_can_knee,
    _female_l1_prescription,
    _first_push_pull_training_exercises,
    _parse_start_time,
    _parse_weekdays,
    _pull_prep_for_ordinal,
    _pull_prep_keys,
    _session_role,
    _week_from_day,
    expand_familiarization_weeks,
    progression_step_for_week,
)


def test_first_push_pull_has_exact_60_day_cadence():
    assert FIRST_PUSH_PULL_DAYS == 60
    assert FIRST_PUSH_PULL_INVERTED_ROW_DAY == 15
    assert FIRST_PUSH_PULL_SCAPULAR_DAY == 29
    assert FIRST_PUSH_PULL_EARLY_BAR_DAY == 15
    assert FIRST_PUSH_PULL_BAR_START_DAY == 29
    assert len(_FIRST_PUSH_PULL_TRAIN_DAYS) == 26
    assert _TRAIN_DAYS_60 == _FIRST_PUSH_PULL_TRAIN_DAYS
    assert _FIRST_PUSH_PULL_TRAIN_DAYS[:3] == (1, 3, 5)
    assert _TRAIN_DAYS_60[-2:] == (57, 59)
    assert _session_role(1) == "push_legs"
    assert _session_role(2) == "pull_back"
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


def test_pull_prep_switches_to_inverted_row_from_week_three():
    catalog = {
        "inverted_row": object(),
        "chin_hold_negative": object(),
        "backpack_bent": object(),
        "floor_pull": object(),
    }
    assert _pull_prep_keys(catalog, day=14) == ["backpack_bent", "floor_pull"]
    assert _pull_prep_keys(catalog, day=15) == ["inverted_row", "backpack_bent"]
    assert _pull_prep_for_ordinal(catalog, 1, day=15)[0] == "inverted_row"
    blob = " ".join(_pull_prep_for_ordinal(catalog, 1, day=15)).lower()
    assert "cằm" not in blob
    assert "negative" not in blob
    assert "chin" not in blob


def test_plan_schemas_accept_day_60():
    assert PlanDayIn(day_number=60).day_number == 60
    assert UpdatePlanDayIn(day_number=60).day_number == 60


def test_first_rep_path_reaches_test_variations_by_week_eight():
    assert progression_step_for_week("first_push_pull", "push", 0, 1) == 0
    assert progression_step_for_week("first_push_pull", "push", 0, 8) == 5
    assert progression_step_for_week("first_push_pull", "pull", 0, 8) == 6


def test_path_caps_prevent_out_of_catalog_progression():
    assert progression_step_for_week("basic_foundation", "push", 5, 8) == 5
    assert progression_step_for_week("advanced_foundation", "push", 5, 8) == 6
    assert progression_step_for_week("advanced_foundation", "pull", 6, 8) == 6


def test_gender_max_step_clamps_female_first_rep_path():
    assert progression_step_for_week("first_push_pull", "push", 0, 8, max_step=1) == 1
    assert progression_step_for_week("first_push_pull", "pull", 0, 8, max_step=0) == 0


def test_first_push_pull_session_rotates_three_roles():
    assert _families_for_day("first_push_pull", 0) == ["push", "squat", "plank", "run"]
    assert _families_for_day("first_push_pull", 1) == ["pull", "plank", "run"]
    assert _families_for_day("first_push_pull", 2) == ["push", "pull", "squat", "run"]


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
        assert warmups
        jj = warmups[0]
        assert jj.exercise_id == _FOUNDATION_CATALOG["jumping_jack"].id
        assert jj.sets == 2
        assert jj.rest_seconds == 60
        assert "20–30" in (jj.reps or "")


def test_obese_l1_skips_jumping_jack_warmup():
    items = _first_push_pull_training_exercises(
        _FOUNDATION_CATALOG, gender="male", day=1, ordinal=1, bmi_band="obese_1"
    )
    warmup_ids = [int(row.exercise_id) for row in items if row.section == "warmup"]
    assert _FOUNDATION_CATALOG["jumping_jack"].id not in warmup_ids


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


def test_l1_week_three_introduces_inverted_row():
    before = _first_push_pull_training_exercises(
        _FOUNDATION_CATALOG, gender="male", day=12, ordinal=6
    )
    after = _first_push_pull_training_exercises(
        _FOUNDATION_CATALOG, gender="male", day=17, ordinal=8
    )
    assert _FOUNDATION_CATALOG["inverted_row"].id not in _main_ids(before)
    assert _FOUNDATION_CATALOG["inverted_row"].id in _main_ids(after)
    assert _FOUNDATION_CATALOG["chin_hold_negative"].id not in _main_ids(after)


def test_l1_week_five_adds_scapular_or_hang_without_negatives():
    male = _first_push_pull_training_exercises(
        _FOUNDATION_CATALOG, gender="male", day=31, ordinal=14
    )
    female = _first_push_pull_training_exercises(
        _FOUNDATION_CATALOG, gender="female", day=31, ordinal=14
    )
    male_ids = _main_ids(male)
    female_ids = _main_ids(female)
    assert (
        _FOUNDATION_CATALOG["scapular"].id in male_ids
        or _FOUNDATION_CATALOG["dead_hang"].id in male_ids
    )
    assert _FOUNDATION_CATALOG["dead_hang"].id in female_ids
    assert _FOUNDATION_CATALOG["chin_hold_negative"].id not in male_ids
    assert _FOUNDATION_CATALOG["negative_pull"].id not in male_ids
    assert "cằm" not in _blob(male)
    assert "negative" not in _blob(male)


def test_l1_day_59_has_five_excel_tests():
    male = _first_push_pull_training_exercises(
        _FOUNDATION_CATALOG, gender="male", day=59, ordinal=26
    )
    female = _first_push_pull_training_exercises(
        _FOUNDATION_CATALOG, gender="female", day=59, ordinal=26
    )
    male_reps = " ".join(row.reps or "" for row in male)
    female_reps = " ".join(row.reps or "" for row in female)
    assert "3–8" in male_reps
    assert "1–2 kéo xà hoặc 6–10 kéo người nằm (bàn/xà)" in male_reps
    assert "12–25" in male_reps
    assert "20–50" in male_reps
    assert "0,8–1,2 km" in male_reps
    assert "4–10" in female_reps
    assert "20–45" in female_reps
    assert "10–20" in female_reps
    assert "15–40" in female_reps
    assert "0,7–1,0 km" in female_reps
    assert len([row for row in male if row.section != "warmup"]) == 5
    assert len([row for row in female if row.section != "warmup"]) == 5


def test_l1_day_57_is_lighter_test_with_table_row_not_pullup():
    male = _first_push_pull_training_exercises(
        _FOUNDATION_CATALOG, gender="male", day=57, ordinal=25
    )
    female = _first_push_pull_training_exercises(
        _FOUNDATION_CATALOG, gender="female", day=57, ordinal=25
    )
    male_ids = _main_ids(male)
    female_ids = _main_ids(female)
    assert _FOUNDATION_CATALOG["strict_pull"].id not in male_ids
    assert _FOUNDATION_CATALOG["strict_pull"].id not in female_ids
    assert (
        _FOUNDATION_CATALOG["inverted_row"].id in male_ids
        or _FOUNDATION_CATALOG["elevated_row"].id in male_ids
    )
    assert "3–6" in " ".join(row.reps or "" for row in male)
    assert "5–6" in " ".join(row.reps or "" for row in male)
    assert len([row for row in male if row.section != "warmup"]) == 5
    assert len([row for row in female if row.section != "warmup"]) == 5


def test_l1_late_weeks_prefer_single_leg_glute_over_backpack_rdl():
    items = _first_push_pull_training_exercises(
        _FOUNDATION_CATALOG, gender="male", day=31, ordinal=14
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


def test_basic_foundation_day_one_uses_bar_and_skips_wall_as_main():
    items = _basic_foundation_training_exercises(
        _FOUNDATION_CATALOG, gender="male", day=1, ordinal=1
    )
    main = [row for row in items if row.section != "warmup"]
    ids = {int(row.exercise_id) for row in main}
    assert _FOUNDATION_CATALOG["strict_push"].id in ids
    assert _FOUNDATION_CATALOG["wall_push"].id not in ids
    blob = " ".join(f"{row.reps} {row.notes_vi}" for row in items).lower()
    assert "dumbbell" not in blob
    assert "ring" not in blob


def test_l2_female_is_not_stuck_on_knee_push():
    days = []
    for ordinal, day in enumerate(_TRAIN_DAYS_60, start=1):
        if day in {57, 59}:
            continue
        days.append(
            _basic_foundation_training_exercises(
                _FOUNDATION_CATALOG, gender="female", day=day, ordinal=ordinal
            )
        )
    knee = _FOUNDATION_CATALOG["knee_push"].id
    incline = _FOUNDATION_CATALOG["incline_push"].id
    floor = _FOUNDATION_CATALOG["strict_push"].id
    knee_only = 0
    progressed = 0
    for items in days:
        ids = _main_ids(items)
        if not ids & {knee, incline, floor}:
            continue
        if floor in ids or incline in ids:
            progressed += 1
        if knee in ids and floor not in ids and incline not in ids:
            knee_only += 1
    assert progressed > 0
    assert knee_only == 0


def test_basic_foundation_day_59_matches_basic_standards():
    male = _basic_foundation_training_exercises(
        _FOUNDATION_CATALOG, gender="male", day=59, ordinal=26
    )
    female = _basic_foundation_training_exercises(
        _FOUNDATION_CATALOG, gender="female", day=59, ordinal=26
    )
    male_reps = " ".join(row.reps or "" for row in male)
    female_reps = " ".join(row.reps or "" for row in female)
    assert "8–15" in male_reps
    assert "2–6" in male_reps
    assert "20–35" in male_reps
    assert "45–75" in male_reps
    assert "1,5 km" in male_reps
    assert "1–6 sàn" in female_reps or "6–12 kê bục" in female_reps
    assert "4–8 kéo người nằm" in female_reps
    assert "18–28" in female_reps
    assert "30–60" in female_reps
    assert "1,3 km" in female_reps
    assert len([row for row in male if row.section != "warmup"]) == 5


def test_advanced_foundation_day_59_matches_advanced_standards():
    male = _advanced_foundation_training_exercises(
        _FOUNDATION_CATALOG, gender="male", day=59, ordinal=26
    )
    female = _advanced_foundation_training_exercises(
        _FOUNDATION_CATALOG, gender="female", day=59, ordinal=26
    )
    male_reps = " ".join(row.reps or "" for row in male)
    female_blob = " ".join(
        f"{row.reps} {row.notes_vi}" for row in female
    ).lower()
    assert "12–25" in male_reps
    assert "4–10" in male_reps
    assert "25–45" in male_reps
    assert "60–90" in male_reps
    assert "1,8 km" in male_reps
    assert "3–8" in female_blob
    assert "1–2 kéo xà" in female_blob or "6 inverted" in female_blob
    assert "20–35" in female_blob
    assert "45–90" in female_blob
    assert "1,5 km" in female_blob
    assert "ring" not in female_blob
    assert len([row for row in male if row.section != "warmup"]) == 5


def test_week_from_day_and_female_can_knee():
    assert _week_from_day(1) == 1
    assert _week_from_day(14) == 2
    assert _week_from_day(15) == 3
    assert _week_from_day(29) == 5
    assert _week_from_day(57) == 9
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
        assert _FOUNDATION_CATALOG["knee_push"].id not in ids
        assert (
            _FOUNDATION_CATALOG["wall_push"].id in ids
            or _FOUNDATION_CATALOG["incline_push"].id in ids
        )


def test_female_zero_baseline_week_four_probes_knee():
    items = _first_push_pull_training_exercises(
        _FOUNDATION_CATALOG,
        gender="female",
        day=22,
        ordinal=10,
        can_knee=False,
    )
    ids = _main_ids(items)
    assert _FOUNDATION_CATALOG["incline_push"].id in ids
    assert _FOUNDATION_CATALOG["knee_push"].id in ids
    knee_rows = [
        row
        for row in items
        if row.section != "warmup"
        and int(row.exercise_id) == _FOUNDATION_CATALOG["knee_push"].id
    ]
    assert knee_rows and knee_rows[0].sets == 1
    assert "2–4" in (knee_rows[0].reps or "")


def test_female_can_knee_starts_knee_earlier():
    week3 = _first_push_pull_training_exercises(
        _FOUNDATION_CATALOG,
        gender="female",
        day=15,
        ordinal=7,
        can_knee=True,
    )
    assert _FOUNDATION_CATALOG["knee_push"].id in _main_ids(week3)


def test_female_hang_from_week_two_and_squat_in_late_weeks():
    week2_pull = _first_push_pull_training_exercises(
        _FOUNDATION_CATALOG,
        gender="female",
        day=10,
        ordinal=5,
        can_knee=False,
    )
    assert _FOUNDATION_CATALOG["dead_hang"].id in _main_ids(week2_pull)
    assert "8–10 giây" in " ".join(row.reps or "" for row in week2_pull)

    week5_push = _first_push_pull_training_exercises(
        _FOUNDATION_CATALOG,
        gender="female",
        day=29,
        ordinal=13,
        can_knee=False,
    )
    assert _FOUNDATION_CATALOG["squat"].id in _main_ids(week5_push)
    blob = " ".join(row.reps or "" for row in week5_push)
    assert "10 phút" in blob
    assert "0,8 km" in blob


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


def test_obese_advanced_skips_jump_squat_and_uses_walking():
    items = _advanced_foundation_training_exercises(
        _FOUNDATION_CATALOG, gender="male", day=1, ordinal=1, bmi_band="obese_1"
    )
    ids = _main_ids(items)
    assert _FOUNDATION_CATALOG["jump_squat"].id not in ids
    blob = _blob(items)
    assert "chạy bền" not in blob
    assert "đi bộ" in blob


def test_underweight_cardio_is_shorter():
    items = _basic_foundation_training_exercises(
        _FOUNDATION_CATALOG, gender="male", day=1, ordinal=1, bmi_band="underweight"
    )
    blob = _blob(items)
    assert "8–10 phút" in blob


def test_obese_l1_stays_on_incline_late_weeks():
    items = _first_push_pull_training_exercises(
        _FOUNDATION_CATALOG,
        gender="male",
        day=29,
        ordinal=13,
        bmi_band="obese_1",
    )
    ids = _main_ids(items)
    assert _FOUNDATION_CATALOG["strict_push"].id not in ids
    assert (
        _FOUNDATION_CATALOG["incline_push"].id in ids
        or _FOUNDATION_CATALOG["knee_push"].id in ids
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
