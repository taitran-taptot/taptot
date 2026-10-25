"""Kit anchors, bar/rings gates, and the home dumbbell venue exception."""

import json
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.entities import Exercise, MuscleGroup
from app.schemas.plans import PlanDayIn, PlanExerciseIn
from app.services.food_picker_roles import is_starchy_vegetable
from app.services.workout_generation.focus import bump_focus_sets, resistance_kind_list
from app.services.workout_generation.kit_schedule import (
    apply_kit_mains,
    bar_rings_slots,
    challenge_finisher_kind,
    challenge_strength_kinds,
    gear_main_slots,
    gear_plan,
    kit_anchor_slots,
    kit_kind_list,
    resistance_slot_count,
    rotate_db_accessories_across_days,
)
from app.services.workout_generation.shortlist import (
    exercise_passes_location_gear,
    is_home_denied_exercise,
)

ROOT = Path(__file__).resolve().parents[2]


def _ens(slots):
    return [[name for name, _vi in slot] for slot in slots]


def test_seed_potatoes_and_corn_stay_on_the_produce_aisle():
    catalog = json.loads((ROOT / "seeds" / "foods_catalog_v2.json").read_text(encoding="utf-8"))
    wanted = {
        "khoai-lang",
        "khoai-lang-song",
        "khoai-tay-luoc",
        "khoai-mi-luoc",
        "khoai-mon-luoc",
        "khoai-so-luoc",
        "bap-ngot-luoc",
    }
    found = {item["slug"]: item for item in catalog if item.get("slug") in wanted}
    assert set(found) == wanted
    for item in found.values():
        assert item["category_slug"] == "rau-cu-qua"
        assert item["macro_roles"] == ["carb"]
    assert is_starchy_vegetable(slug="khoai-lang", name_vi="Khoai lang")
    assert not is_starchy_vegetable(slug="cai-bap", name_vi="Cải bắp")
    assert not is_starchy_vegetable(slug="dau-bap", name_vi="Đậu bắp")
    assert not is_starchy_vegetable(slug="ca-khoai", name_vi="Cá khoai")


def test_dumbbell_and_band_anchors_are_the_test_lifts():
    assert _ens(kit_anchor_slots("dumbbell", "push"))[0] == ["Dumbbell Bench Press"]
    assert _ens(kit_anchor_slots("dumbbell", "pull"))[0] == ["Dumbbell Row Bilateral"]
    assert _ens(kit_anchor_slots("dumbbell", "legs"))[0] == ["Dumbbell Goblet Squat"]
    assert _ens(kit_anchor_slots("dumbbell", "upper")) == [
        ["Dumbbell Bench Press"],
        ["Dumbbell Row Bilateral"],
    ]
    assert _ens(kit_anchor_slots("dumbbell", "lower"))[0] == ["Dumbbell Goblet Squat"]
    assert _ens(kit_anchor_slots("band", "push"))[0] == ["Band Chest Press"]
    assert _ens(kit_anchor_slots("band", "pull"))[0] == ["Band Seated Pulldown"]
    assert _ens(kit_anchor_slots("band", "legs"))[0] == ["Band Squat"]
    assert _ens(kit_anchor_slots("bar_rings", "push"))[0] == ["Ring Push-Up"]
    assert _ens(kit_anchor_slots("bar_rings", "pull"))[0][0] == "Pull Ups"
    assert _ens(kit_anchor_slots("bar_rings", "legs"))[0] == ["Bodyweight Squat"]
    assert len(kit_anchor_slots("bar_rings", "upper")) == 2


def test_dumbbell_60_mains_are_chest_shoulder_arm_not_core():
    push = [slot[0][0] for slot in gear_main_slots("dumbbell", "push", 4)]
    pull = [slot[0][0] for slot in gear_main_slots("dumbbell", "pull", 4)]
    legs = [slot[0][0] for slot in gear_main_slots("dumbbell", "legs", 4)]
    assert push == [
        "Dumbbell Bench Press",
        "Dumbbell Chest Fly",
        "Dumbbell Lateral Raise",
        "Dumbbell Seated Overhead Press",
        "Dumbbell Skullcrusher",
    ]
    assert pull == [
        "Dumbbell Row Bilateral",
        "Dumbbell Row Unilateral",
        "Dumbbell Seated Rear Delt Fly",
        "Dumbbell Rear Delt Fly",
        "Dumbbell Hammer Curl",
    ]
    next_push = [slot[0][0] for slot in gear_main_slots("dumbbell", "push", 4, month=1)]
    assert next_push[0] == "Dumbbell Bench Press"
    assert next_push[2] == "Dumbbell Seated Overhead Press"
    later = [slot[0][0] for slot in gear_main_slots("dumbbell", "push", 4, month=2)]
    assert later[0] == "Dumbbell Bench Press"
    assert later[2] == "Dumbbell Front Raise"
    assert later[-1] == "Dumbbell Tricep Kickback"
    assert legs == [
        "Dumbbell Goblet Squat",
        "Dumbbell Lateral Lunge",
        "Dumbbell Leg Curl",
        "Dumbbell Single Leg Calf Raise",
    ]
    assert [slot[0][0] for slot in gear_main_slots("dumbbell", "legs", 3)] == [
        "Dumbbell Goblet Squat",
        "Dumbbell Lateral Lunge",
        "Dumbbell Leg Curl",
    ]
    assert [slot[0][0] for slot in gear_main_slots("dumbbell", "legs", 2)] == [
        "Dumbbell Goblet Squat",
        "Dumbbell Leg Curl",
    ]
    assert [slot[0][0] for slot in gear_main_slots("dumbbell", "legs", 4, month=4)][-2] == "Dumbbell Deadlift"
    assert "Bird Dog" not in push


def test_apply_replaces_push_core_fillers_with_the_minute_frame():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    muscle = MuscleGroup(slug="chest-mid", name_vi="Ngực")
    db.add(muscle)
    db.flush()
    now = datetime.now(UTC)
    names = [
        ("Dumbbell Bench Press", "Đẩy ngực tạ đơn"),
        ("Dumbbell Front Raise", "Nâng tay trước tạ đơn"),
        ("Dumbbell Seated Overhead Tricep Extension", "Duỗi tay sau tạ đơn"),
        ("Dumbbell Chest Fly", "Ép ngực tạ đơn"),
        ("Front Plank on Elbows", "Plank chống khuỷu"),
        ("Bird Dog", "Chim chó"),
        ("Bodyweight Russian Twist", "Xoay người"),
        ("Hiking", "Đi bộ đường dài"),
    ]
    ids = {}
    for en, vi in names:
        row = Exercise(
            name_en=en,
            name_vi=vi,
            muscle_group_id=muscle.id,
            exercise_type="main",
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        db.add(row)
        db.flush()
        ids[en] = row.id
    db.commit()
    day = PlanDayIn(
        day_number=1,
        split_role="push",
        exercises=[
            PlanExerciseIn(exercise_id=ids["Dumbbell Bench Press"], sets=3, reps="8-12", section="main"),
            PlanExerciseIn(exercise_id=ids["Bird Dog"], sets=2, reps="10", section="main"),
            PlanExerciseIn(exercise_id=ids["Bodyweight Russian Twist"], sets=2, reps="12", section="main"),
            PlanExerciseIn(exercise_id=ids["Hiking"], sets=1, reps="16 phút", section="cardio"),
        ],
    )
    apply_kit_mains(
        day,
        db,
        equipment_slugs=["dumbbell"],
        fitness_baseline={"test_kit": "dumbbell"},
        experience_level=1,
        session_minutes=60,
        meta_by_id={},
        home_session=True,
    )
    mains = [ex for ex in day.exercises if ex.section == "main"]
    main_ids = [ex.exercise_id for ex in mains]
    assert main_ids[:4] == [
        ids["Dumbbell Bench Press"],
        ids["Dumbbell Chest Fly"],
        ids["Dumbbell Front Raise"],
        ids["Dumbbell Seated Overhead Tricep Extension"],
    ]
    assert ids["Front Plank on Elbows"] in main_ids
    plank = next(ex for ex in mains if ex.exercise_id == ids["Front Plank on Elbows"])
    assert plank.sets == 1
    assert "giây" in str(plank.reps)
    assert ids["Bird Dog"] not in main_ids
    assert ids["Glute Bridge"] not in main_ids if "Glute Bridge" in ids else True
    assert len(set(main_ids)) == len(main_ids)
    assert not any(ex.section == "cardio" for ex in day.exercises)
    db.close()


def _challenge_catalog():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    muscle = MuscleGroup(slug="chest-mid", name_vi="Ngực")
    db.add(muscle)
    db.flush()
    now = datetime.now(UTC)
    names = [
        "Dumbbell Bench Press",
        "Dumbbell Chest Fly",
        "Dumbbell Lateral Raise",
        "Dumbbell Seated Overhead Press",
        "Dumbbell Front Raise",
        "Dumbbell Seated Overhead Tricep Extension",
        "Dumbbell Skullcrusher",
        "Dumbbell Seated Rear Delt Fly",
        "Dumbbell Row Bilateral",
        "Dumbbell Row Unilateral",
        "Dumbbell Rear Delt Fly",
        "Dumbbell Curl",
        "Dumbbell Goblet Squat",
        "Dumbbell Deadlift",
        "Dumbbell Leg Curl",
        "Dumbbell Single Leg Calf Raise",
        "Front Plank on Elbows",
        "Hand Plank",
        "Dead Bug",
        "Elbow Side Plank",
        "V-Up",
        "Bodyweight Russian Twist",
        "Dumbbell Situp",
        "Glute Bridge",
        "Shadow Boxing",
        "Jumping Jack",
        "Trail Run",
        "Hiking",
        "Bird Dog",
    ]
    ids = {}
    for en in names:
        row = Exercise(
            name_en=en,
            name_vi=en,
            muscle_group_id=muscle.id,
            exercise_type="main",
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        db.add(row)
        db.flush()
        ids[en] = row.id
    db.commit()
    return db, ids


def _apply_challenge(
    db,
    ids,
    *,
    role: str,
    day_number: int,
    minutes: int,
    first: str,
    phase_index: int | None = None,
):
    day = PlanDayIn(
        day_number=day_number,
        split_role=role,
        exercises=[
            PlanExerciseIn(exercise_id=ids[first], sets=3, reps="8-12", section="main"),
            PlanExerciseIn(exercise_id=ids["Bird Dog"], sets=2, reps="10", section="main"),
            PlanExerciseIn(exercise_id=ids["Hiking"], sets=1, reps="16 phút", section="cardio"),
        ],
    )
    apply_kit_mains(
        day,
        db,
        equipment_slugs=["dumbbell"],
        fitness_baseline={"test_kit": "dumbbell"},
        experience_level=1,
        session_minutes=minutes,
        meta_by_id={},
        home_session=True,
        challenge_session=True,
        phase_index=phase_index,
    )
    return day


def test_kit_keeps_bench_main_when_warmup_already_has_it():
    db, ids = _challenge_catalog()
    day = PlanDayIn(
        day_number=1,
        split_role="push",
        exercises=[
            PlanExerciseIn(
                exercise_id=ids["Jumping Jack"], sets=2, reps="20-30 giây", section="warmup"
            ),
            PlanExerciseIn(
                exercise_id=ids["Dumbbell Bench Press"], sets=2, reps="4-6", section="warmup"
            ),
            PlanExerciseIn(
                exercise_id=ids["Dumbbell Bench Press"], sets=3, reps="8-12", section="main"
            ),
            PlanExerciseIn(exercise_id=ids["Bird Dog"], sets=2, reps="10", section="main"),
        ],
    )
    apply_kit_mains(
        day,
        db,
        equipment_slugs=["dumbbell"],
        fitness_baseline={"test_kit": "dumbbell"},
        experience_level=1,
        session_minutes=45,
        meta_by_id={},
        home_session=True,
        challenge_session=True,
    )
    mains = [ex for ex in day.exercises if ex.section == "main"]
    assert mains[0].exercise_id == ids["Dumbbell Bench Press"]
    wu = [ex for ex in day.exercises if ex.section == "warmup"]
    assert ids["Dumbbell Bench Press"] in {ex.exercise_id for ex in wu}
    db.close()


def test_challenge_60_alternates_plank_and_interval_cardio():
    db, ids = _challenge_catalog()
    push = _apply_challenge(db, ids, role="push", day_number=1, minutes=60, first="Dumbbell Bench Press")
    pull = _apply_challenge(db, ids, role="pull", day_number=2, minutes=60, first="Dumbbell Row Bilateral")
    legs = _apply_challenge(db, ids, role="legs", day_number=3, minutes=60, first="Dumbbell Goblet Squat")
    extra_ids = {
        ids["Dead Bug"],
        ids["Elbow Side Plank"],
        ids["V-Up"],
        ids["Bodyweight Russian Twist"],
    }
    push_mains = [ex.exercise_id for ex in push.exercises if ex.section == "main"]
    assert ids["Dumbbell Chest Fly"] in push_mains
    assert ids["Front Plank on Elbows"] in push_mains
    assert ids["Glute Bridge"] not in push_mains
    assert extra_ids.intersection(push_mains)
    assert len({eid for eid in push_mains}) == len(push_mains)
    plank = next(ex for ex in push.exercises if ex.exercise_id == ids["Front Plank on Elbows"])
    assert plank.sets == 1
    assert "giây" in str(plank.reps)
    assert len([ex for ex in push.exercises if ex.section == "cardio"]) == 1
    pull_mains = [ex.exercise_id for ex in pull.exercises if ex.section == "main"]
    assert ids["Dumbbell Chest Fly"] not in pull_mains
    assert ids["Front Plank on Elbows"] in pull_mains
    cardio = [ex for ex in pull.exercises if ex.section == "cardio"]
    assert len(cardio) == 1
    assert cardio[0].exercise_id == ids["Shadow Boxing"]
    assert "giây" not in str(cardio[0].reps)
    assert cardio[0].sets == 4
    assert cardio[0].reps == "20-30"
    legs_mains = [ex.exercise_id for ex in legs.exercises if ex.section == "main"]
    assert ids["Front Plank on Elbows"] in legs_mains
    assert extra_ids.intersection(legs_mains)
    assert ids["Dumbbell Front Raise"] not in legs_mains
    assert len([ex for ex in legs.exercises if ex.section == "cardio"]) == 1
    db.close()


def test_challenge_45_keeps_abs_and_cardio_and_full_sets():
    db, ids = _challenge_catalog()
    day = _apply_challenge(db, ids, role="push", day_number=1, minutes=45, first="Dumbbell Bench Press")
    mains = [ex for ex in day.exercises if ex.section == "main"]
    abs_ids = {
        ids["Front Plank on Elbows"],
        ids["Dead Bug"],
        ids["Elbow Side Plank"],
        ids["V-Up"],
        ids["Bodyweight Russian Twist"],
        ids["Dumbbell Situp"],
    }
    main_ids = [ex.exercise_id for ex in mains]
    strength = [ex for ex in mains if ex.exercise_id not in abs_ids]
    assert ids["Front Plank on Elbows"] in main_ids
    assert len(strength) == 4
    assert mains[0].exercise_id == ids["Dumbbell Bench Press"]
    assert mains[0].sets == 3
    assert mains[0].rest_seconds == 120
    assert all(ex.sets == 3 for ex in strength)
    assert ids["Dumbbell Chest Fly"] in main_ids
    assert any(ex.rest_seconds == 90 for ex in strength[1:])
    cardio = [ex for ex in day.exercises if ex.section == "cardio"]
    assert len(cardio) == 1
    assert cardio[0].exercise_id == ids["Shadow Boxing"]
    assert cardio[0].sets == 2
    assert "giây" not in str(cardio[0].reps)
    assert not any(ex.exercise_id == ids["Hiking"] for ex in day.exercises)
    db.close()


def test_challenge_trail_run_uses_minutes():
    db, ids = _challenge_catalog()
    day = PlanDayIn(
        day_number=2,
        split_role="pull",
        exercises=[
            PlanExerciseIn(exercise_id=ids["Dumbbell Row Bilateral"], sets=3, reps="8-12", section="main"),
        ],
    )
    apply_kit_mains(
        day,
        db,
        equipment_slugs=["dumbbell"],
        fitness_baseline={"test_kit": "dumbbell"},
        experience_level=1,
        session_minutes=60,
        meta_by_id={},
        home_session=True,
        challenge_session=True,
    )
    # Month 0 of day 2 is boxing; force trail by using month-2 day (day 58 = month 2).
    later = PlanDayIn(
        day_number=58,
        split_role="pull",
        exercises=[
            PlanExerciseIn(exercise_id=ids["Dumbbell Row Bilateral"], sets=3, reps="8-12", section="main"),
        ],
    )
    apply_kit_mains(
        later,
        db,
        equipment_slugs=["dumbbell"],
        fitness_baseline={"test_kit": "dumbbell"},
        experience_level=1,
        session_minutes=60,
        meta_by_id={},
        home_session=True,
        challenge_session=True,
    )
    cardio = [ex for ex in later.exercises if ex.section == "cardio"]
    assert len(cardio) == 1
    assert cardio[0].exercise_id == ids["Trail Run"]
    assert cardio[0].sets == 1
    assert cardio[0].reps == "12 phút"
    db.close()


def test_home_dumbbell_pool_accepts_gym_venue_bench():
    assert exercise_passes_location_gear(
        venue="gym",
        equipment_slugs=["dumbbell"],
        name_en="Dumbbell Bench Press",
        name_vi="Đẩy ngực tạ đơn",
        location="home",
        user_slugs=["dumbbell"],
    )
    assert not exercise_passes_location_gear(
        venue="gym",
        equipment_slugs=["barbell"],
        name_en="Barbell Bench Press",
        name_vi="Đẩy ngực tạ đòn",
        location="home",
        user_slugs=["dumbbell"],
    )


def test_ring_push_gates_ignore_gender_and_experience():
    strong = _ens(
        bar_rings_slots(
            "push",
            pushups_max=16,
            pullups_max=0,
            experience_level=1,
            slots=resistance_slot_count(60),
        )
    )
    mid = _ens(
        bar_rings_slots(
            "push",
            pushups_max=12,
            pullups_max=0,
            experience_level=3,
            slots=resistance_slot_count(45),
        )
    )
    weak = _ens(
        bar_rings_slots(
            "push",
            pushups_max=8,
            pullups_max=0,
            experience_level=3,
            slots=resistance_slot_count(60),
        )
    )
    assert strong[0] == ["Ring Push-Up"]
    assert "Ring Dip" in strong[1]
    assert mid[0] == ["Ring Push-Up"]
    assert all("Ring Dip" not in slot for slot in mid)
    assert weak[0] == ["Push Up"]
    assert ["Ring Push-Up"] not in weak
    assert all("Ring Dip" not in slot for slot in weak)
    assert not is_home_denied_exercise(
        name_en="Ring Dip",
        name_vi="Dip vòng treo",
        location="home",
        no_equipment=False,
        user_slugs=["gymnastic-rings", "pull-up-bar"],
        experience_level=1,
        fitness_baseline={"pushups_max": 16},
    )


def test_ring_legs_always_use_bulgarian_and_hamstring():
    trained = _ens(
        bar_rings_slots(
            "legs",
            pushups_max=8,
            pullups_max=0,
            experience_level=2,
            slots=resistance_slot_count(45),
        )
    )
    newer = _ens(
        bar_rings_slots(
            "legs",
            pushups_max=8,
            pullups_max=0,
            experience_level=1,
            slots=resistance_slot_count(45),
        )
    )
    hour = _ens(
        bar_rings_slots(
            "legs",
            pushups_max=8,
            pullups_max=0,
            experience_level=1,
            slots=resistance_slot_count(60),
        )
    )
    assert [slot[0] for slot in trained] == [
        "Bodyweight Squat",
        "Bulgarian Ring Squat",
        "Ring Hamstring Curl",
        "Walking Lunge",
        "Glute Bridge",
    ]
    assert [slot[0] for slot in newer] == [slot[0] for slot in trained]
    assert [slot[0] for slot in hour][:3] == [
        "Bodyweight Squat",
        "Bulgarian Ring Squat",
        "Ring Hamstring Curl",
    ]
    assert hour[3][0] == "Walking Lunge"


def _db_catalog(names):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    muscle = MuscleGroup(slug="chest-mid", name_vi="Ngực")
    db.add(muscle)
    db.flush()
    now = datetime.now(UTC)
    ids = {}
    for en in names:
        row = Exercise(
            name_en=en,
            name_vi=en,
            muscle_group_id=muscle.id,
            exercise_type="main",
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        db.add(row)
        db.flush()
        ids[en] = row.id
    db.commit()
    return db, ids


def test_dumbbell_accessories_rotate_on_next_same_role_session():
    db, ids = _db_catalog(
        [
            "Dumbbell Bench Press",
            "Dumbbell Chest Fly",
            "Dumbbell Lateral Raise",
            "Dumbbell Seated Overhead Press",
            "Dumbbell Front Raise",
            "Dumbbell Skullcrusher",
            "Dumbbell Seated Overhead Tricep Extension",
            "Hiking",
        ]
    )
    first = PlanDayIn(
        day_number=1,
        split_role="push",
        exercises=[
            PlanExerciseIn(exercise_id=ids["Dumbbell Bench Press"], sets=3, reps="16-20", section="main"),
            PlanExerciseIn(exercise_id=ids["Hiking"], sets=1, reps="16 phút", section="cardio"),
        ],
    )
    second = PlanDayIn(
        day_number=4,
        split_role="push",
        exercises=[
            PlanExerciseIn(exercise_id=ids["Dumbbell Bench Press"], sets=3, reps="16-20", section="main"),
        ],
    )
    baseline = {"test_kit": "dumbbell", "db_press_reps": 12, "db_press_kg": 10}
    apply_kit_mains(
        first,
        db,
        equipment_slugs=["dumbbell"],
        fitness_baseline=baseline,
        experience_level=1,
        session_minutes=45,
        meta_by_id={},
        home_session=True,
        variety_index=0,
    )
    apply_kit_mains(
        second,
        db,
        equipment_slugs=["dumbbell"],
        fitness_baseline=baseline,
        experience_level=1,
        session_minutes=45,
        meta_by_id={},
        home_session=True,
        variety_index=1,
    )
    first_mains = [ex.exercise_id for ex in first.exercises if ex.section == "main"]
    second_mains = [ex.exercise_id for ex in second.exercises if ex.section == "main"]
    assert len(first_mains) == 5
    assert first_mains[0] == ids["Dumbbell Bench Press"]
    assert ids["Dumbbell Chest Fly"] in first_mains
    assert ids["Dumbbell Lateral Raise"] in first_mains
    assert second_mains[0] == ids["Dumbbell Bench Press"]
    assert ids["Dumbbell Seated Overhead Press"] in second_mains
    assert first_mains != second_mains
    bench = next(ex for ex in first.exercises if ex.exercise_id == ids["Dumbbell Bench Press"])
    raise_ex = next(ex for ex in first.exercises if ex.exercise_id == ids["Dumbbell Lateral Raise"])
    assert bench.reps == "8-12"
    assert raise_ex.reps == "12-16"
    db.close()


def test_db_accessories_rotate_across_cloned_weeks():
    db, ids = _db_catalog(
        [
            "Dumbbell Bench Press",
            "Dumbbell Lateral Raise",
            "Dumbbell Seated Overhead Press",
            "Dumbbell Front Raise",
            "Dumbbell Skullcrusher",
            "Dumbbell Seated Overhead Tricep Extension",
            "Dumbbell Tricep Kickback",
        ]
    )

    def cloned_push(day_number: int) -> PlanDayIn:
        return PlanDayIn(
            day_number=day_number,
            split_role="push",
            exercises=[
                PlanExerciseIn(
                    exercise_id=ids["Dumbbell Bench Press"],
                    sets=3,
                    reps="8-12",
                    section="main",
                ),
                PlanExerciseIn(
                    exercise_id=ids["Dumbbell Lateral Raise"],
                    sets=3,
                    reps="12-16",
                    section="main",
                ),
                PlanExerciseIn(
                    exercise_id=ids["Dumbbell Skullcrusher"],
                    sets=3,
                    reps="12-16",
                    section="main",
                ),
            ],
        )

    days = [cloned_push(1), cloned_push(4), cloned_push(7)]
    rotate_db_accessories_across_days(
        days,
        db,
        equipment_slugs=["dumbbell"],
        fitness_baseline={"test_kit": "dumbbell"},
        session_minutes=45,
        meta_by_id={},
        home_session=True,
    )
    assert [ex.exercise_id for ex in days[0].exercises] == [
        ids["Dumbbell Bench Press"],
        ids["Dumbbell Lateral Raise"],
        ids["Dumbbell Skullcrusher"],
    ]
    assert [ex.exercise_id for ex in days[1].exercises] == [
        ids["Dumbbell Bench Press"],
        ids["Dumbbell Seated Overhead Press"],
        ids["Dumbbell Seated Overhead Tricep Extension"],
    ]
    assert [ex.exercise_id for ex in days[2].exercises] == [
        ids["Dumbbell Bench Press"],
        ids["Dumbbell Front Raise"],
        ids["Dumbbell Tricep Kickback"],
    ]
    db.close()


def test_bar_rings_accessories_rotate_keep_test_lifts():
    pull0 = [slot[0] for slot in _ens(
        bar_rings_slots(
            "pull",
            pushups_max=20,
            pullups_max=8,
            experience_level=1,
            slots=4,
            variety=0,
        )
    )]
    pull1 = [slot[0] for slot in _ens(
        bar_rings_slots(
            "pull",
            pushups_max=20,
            pullups_max=8,
            experience_level=1,
            slots=4,
            variety=1,
        )
    )]
    assert pull0[0] == "Pull Ups"
    assert pull1[0] == "Pull Ups"
    assert pull0[1] == "Ring Row"
    assert pull1[1] == "Ring Face-down Row"
    assert pull0[2] != pull1[2]


def _rings_catalog():
    names = [
        "Ring Push-Up",
        "Push Up",
        "Ring Dip",
        "Ring Chest Fly",
        "Pike Push-Up",
        "Elevated Pike Push-Up",
        "Ring Triceps Extension",
        "Diamond Push Ups",
        "Pull Ups",
        "Ring Row",
        "Ring Face-down Row",
        "Ring Rear Delt Fly",
        "Ring Face Pull",
        "Ring Biceps Curl",
        "Chin-Up",
        "Bodyweight Squat",
        "Bulgarian Ring Squat",
        "Ring Hamstring Curl",
        "Walking Lunge",
        "Glute Bridge",
        "Standing Calf Raise",
        "Single Leg Glute Bridge",
        "Bodyweight Alternating Reverse Lunges",
        "Ring Hanging Knee Raise",
        "Ring Hanging Leg Raise",
        "Dead Bug",
        "Elbow Side Plank",
        "V-Up",
        "Bodyweight Russian Twist",
        "Front Plank on Elbows",
        "Hand Plank",
        "Shadow Boxing",
        "Jumping Jack",
        "Trail Run",
        "Hiking",
        "Bird Dog",
    ]
    return _db_catalog(names)


def test_bar_rings_challenge_60_keeps_four_mains_abs_and_cardio():
    db, ids = _rings_catalog()
    day = PlanDayIn(
        day_number=1,
        split_role="push",
        exercises=[
            PlanExerciseIn(exercise_id=ids["Ring Push-Up"], sets=3, reps="8-12", section="main"),
            PlanExerciseIn(exercise_id=ids["Bird Dog"], sets=2, reps="10", section="main"),
            PlanExerciseIn(exercise_id=ids["Hiking"], sets=1, reps="16 phút", section="cardio"),
        ],
    )
    apply_kit_mains(
        day,
        db,
        equipment_slugs=["gymnastic-rings", "pull-up-bar"],
        fitness_baseline={
            "test_kit": "bar_rings",
            "pushups_max": 16,
            "pullups_max": 8,
        },
        experience_level=1,
        session_minutes=60,
        meta_by_id={},
        home_session=True,
        challenge_session=True,
    )
    mains = [ex for ex in day.exercises if ex.section == "main"]
    cardio = [ex for ex in day.exercises if ex.section == "cardio"]
    extra_ids = {
        ids["Dead Bug"],
        ids["Elbow Side Plank"],
        ids["V-Up"],
        ids["Bodyweight Russian Twist"],
    }
    assert len(mains) >= 5
    assert mains[0].exercise_id == ids["Ring Push-Up"]
    assert ids["Front Plank on Elbows"] in [ex.exercise_id for ex in mains]
    assert extra_ids.intersection(ex.exercise_id for ex in mains)
    assert ids["Glute Bridge"] not in [ex.exercise_id for ex in mains]
    assert len({ex.exercise_id for ex in mains}) == len(mains)
    assert len(cardio) == 1
    assert cardio[0].exercise_id != ids["Hiking"]
    db.close()


def test_rings_challenge_p2_push_uses_chest_fly_not_second_pike():
    db, ids = _rings_catalog()
    day = PlanDayIn(
        day_number=25,
        split_role="push",
        exercises=[
            PlanExerciseIn(exercise_id=ids["Ring Push-Up"], sets=3, reps="8-12", section="main"),
        ],
    )
    apply_kit_mains(
        day,
        db,
        equipment_slugs=["gymnastic-rings", "pull-up-bar"],
        fitness_baseline={
            "test_kit": "bar_rings",
            "pushups_max": 16,
            "pullups_max": 8,
        },
        experience_level=2,
        session_minutes=45,
        meta_by_id={},
        home_session=True,
        challenge_session=True,
        phase_index=1,
    )
    mains = [ex for ex in day.exercises if ex.section == "main"]
    force = [
        ex
        for ex in mains
        if ex.exercise_id
        not in {
            ids["Front Plank on Elbows"],
            ids["Dead Bug"],
            ids["Elbow Side Plank"],
            ids["V-Up"],
            ids["Bodyweight Russian Twist"],
            ids["Hand Plank"],
        }
    ]
    force_ids = [ex.exercise_id for ex in force]
    assert len(force_ids) == 5
    assert len(set(force_ids)) == 5
    assert force_ids[0] == ids["Ring Push-Up"]
    assert ids["Ring Dip"] in force_ids
    assert ids["Pike Push-Up"] in force_ids
    assert ids["Ring Chest Fly"] in force_ids
    assert ids["Ring Triceps Extension"] in force_ids
    assert force_ids.count(ids["Pike Push-Up"]) == 1
    db.close()


def test_rings_60_push_triceps_focus_mains_are_unique():
    db, ids = _rings_catalog()
    day = PlanDayIn(
        day_number=1,
        split_role="push",
        exercises=[
            PlanExerciseIn(exercise_id=ids["Ring Push-Up"], sets=3, reps="8-12", section="main"),
        ],
    )
    apply_kit_mains(
        day,
        db,
        equipment_slugs=["gymnastic-rings", "pull-up-bar"],
        fitness_baseline={
            "test_kit": "bar_rings",
            "pushups_max": 16,
            "pullups_max": 8,
        },
        experience_level=1,
        session_minutes=60,
        meta_by_id={},
        home_session=True,
        challenge_session=True,
        focus_keys=["tay"],
    )
    mains = [ex.exercise_id for ex in day.exercises if ex.section == "main"]
    assert len(mains) == len(set(mains))
    assert mains.count(ids["Ring Triceps Extension"]) <= 1
    db.close()


def test_rings_60_legs_mains_are_unique_and_lead_abs_with_plank():
    db, ids = _rings_catalog()
    day = PlanDayIn(
        day_number=1,
        split_role="legs",
        exercises=[
            PlanExerciseIn(exercise_id=ids["Bodyweight Squat"], sets=3, reps="8-12", section="main"),
            PlanExerciseIn(exercise_id=ids["Glute Bridge"], sets=2, reps="10-12", section="main"),
            PlanExerciseIn(exercise_id=ids["Hiking"], sets=1, reps="16 phút", section="cardio"),
        ],
    )
    apply_kit_mains(
        day,
        db,
        equipment_slugs=["gymnastic-rings", "pull-up-bar"],
        fitness_baseline={"test_kit": "bar_rings", "pushups_max": 16, "pullups_max": 8},
        experience_level=1,
        session_minutes=60,
        meta_by_id={},
        home_session=True,
        challenge_session=True,
    )
    mains = [ex for ex in day.exercises if ex.section == "main"]
    main_ids = [ex.exercise_id for ex in mains]
    assert len(main_ids) == len(set(main_ids))
    assert main_ids.count(ids["Glute Bridge"]) <= 1
    assert ids["Front Plank on Elbows"] in main_ids
    abs_ids = {
        ids["Front Plank on Elbows"],
        ids["Dead Bug"],
        ids["Elbow Side Plank"],
        ids["V-Up"],
        ids["Bodyweight Russian Twist"],
    }
    first_abs = next(ex.exercise_id for ex in mains if ex.exercise_id in abs_ids)
    assert first_abs == ids["Front Plank on Elbows"]
    db.close()


def test_rotate_ring_leg_finisher_across_weeks():
    db, ids = _rings_catalog()

    def cloned_legs(day_number: int) -> PlanDayIn:
        return PlanDayIn(
            day_number=day_number,
            split_role="legs",
            exercises=[
                PlanExerciseIn(exercise_id=ids["Bodyweight Squat"], sets=3, reps="8-12", section="main"),
                PlanExerciseIn(exercise_id=ids["Bulgarian Ring Squat"], sets=3, reps="8-12", section="main"),
                PlanExerciseIn(exercise_id=ids["Ring Hamstring Curl"], sets=3, reps="8-12", section="main"),
                PlanExerciseIn(exercise_id=ids["Walking Lunge"], sets=3, reps="8-12", section="main"),
            ],
        )

    days = [cloned_legs(1), cloned_legs(4), cloned_legs(7)]
    rotate_db_accessories_across_days(
        days,
        db,
        equipment_slugs=["gymnastic-rings", "pull-up-bar"],
        fitness_baseline={"test_kit": "bar_rings"},
        session_minutes=60,
        meta_by_id={},
        home_session=True,
    )
    assert days[0].exercises[0].exercise_id == ids["Bodyweight Squat"]
    assert days[0].exercises[1].exercise_id == ids["Bulgarian Ring Squat"]
    assert days[0].exercises[2].exercise_id == ids["Ring Hamstring Curl"]
    assert days[0].exercises[3].exercise_id == ids["Walking Lunge"]
    assert days[1].exercises[1].exercise_id == ids["Bulgarian Ring Squat"]
    assert days[1].exercises[2].exercise_id == ids["Ring Hamstring Curl"]
    assert days[1].exercises[3].exercise_id == ids["Bodyweight Alternating Reverse Lunges"]
    db.close()


def _band_catalog():
    return _db_catalog(
        [
            "Band Chest Press",
            "Band Chest Fly",
            "Band Front Raise",
            "Band Lateral Raise",
            "Band Tricep Pushdown",
            "Band Overhead Tricep Extension",
            "Band Seated Pulldown",
            "Band Row",
            "Band Reverse Fly",
            "Band Curl",
            "Band Squat",
            "Band Lunge",
            "Band Romanian Deadlift",
            "Band Pull-Through",
            "Band Hip Thrust",
            "Band Glute Kickback",
            "Band Leg Curl",
            "Band Calf Raise",
            "Dead Bug",
            "Hand Plank",
            "Front Plank on Elbows",
            "Elbow Side Plank",
            "V-Up",
            "Glute Bridge",
            "Bodyweight Russian Twist",
            "Shadow Boxing",
            "Hiking",
            "Bird Dog",
        ]
    )


def _apply_band(db, ids, *, role: str, day_number: int, minutes: int, first: str):
    day = PlanDayIn(
        day_number=day_number,
        split_role=role,
        exercises=[
            PlanExerciseIn(exercise_id=ids[first], sets=3, reps="8-12", section="main"),
            PlanExerciseIn(exercise_id=ids["Bird Dog"], sets=2, reps="10", section="main"),
            PlanExerciseIn(exercise_id=ids["Hiking"], sets=1, reps="16 phút", section="cardio"),
        ],
    )
    apply_kit_mains(
        day,
        db,
        equipment_slugs=["resistance-band"],
        fitness_baseline={"test_kit": "band"},
        experience_level=1,
        session_minutes=minutes,
        meta_by_id={},
        home_session=True,
        challenge_session=True,
    )
    return day


def test_band_pull_does_not_get_chest_or_front_raise():
    db, ids = _band_catalog()
    pull_abs = _apply_band(
        db, ids, role="pull", day_number=1, minutes=60, first="Band Seated Pulldown"
    )
    pull_cardio = _apply_band(
        db, ids, role="pull", day_number=2, minutes=60, first="Band Seated Pulldown"
    )
    leak = {ids["Band Chest Fly"], ids["Band Front Raise"], ids["Band Chest Press"]}
    extra_ids = {
        ids["Dead Bug"],
        ids["Elbow Side Plank"],
        ids["V-Up"],
        ids["Bodyweight Russian Twist"],
    }
    pull_mains = [ex.exercise_id for ex in pull_abs.exercises if ex.section == "main"]
    assert pull_mains[0] == ids["Band Seated Pulldown"]
    assert leak.isdisjoint(pull_mains)
    assert ids["Front Plank on Elbows"] in pull_mains
    assert extra_ids.intersection(pull_mains)
    assert ids["Glute Bridge"] not in pull_mains
    assert len([ex for ex in pull_abs.exercises if ex.section == "cardio"]) == 1
    cardio_mains = [ex.exercise_id for ex in pull_cardio.exercises if ex.section == "main"]
    assert leak.isdisjoint(cardio_mains)
    assert ids["Front Plank on Elbows"] in cardio_mains
    cardio = [ex for ex in pull_cardio.exercises if ex.section == "cardio"]
    assert len(cardio) == 1
    assert cardio[0].exercise_id != ids["Hiking"]
    db.close()


def test_band_push_60_stays_on_split():
    db, ids = _band_catalog()
    day = _apply_band(
        db, ids, role="push", day_number=1, minutes=60, first="Band Chest Press"
    )
    mains = [ex.exercise_id for ex in day.exercises if ex.section == "main"]
    assert mains[0] == ids["Band Chest Press"]
    assert ids["Band Seated Pulldown"] not in mains
    assert ids["Band Curl"] not in mains
    db.close()


def test_focus_adds_isolation_at_60_keeps_45_layout():
    two_two_one = ["chest", "chest", "shoulder", "shoulder", "triceps"]
    assert kit_kind_list("dumbbell", "push", 3, ["vai"]) == ["chest", "shoulder", "triceps"]
    assert kit_kind_list("dumbbell", "push", 4, None) == two_two_one
    assert kit_kind_list("dumbbell", "push", 4, ["nguc"]) == two_two_one
    assert kit_kind_list("dumbbell", "push", 4, ["vai"]) == two_two_one
    assert kit_kind_list("dumbbell", "push", 4, ["tay"]) == [
        "chest",
        "chest",
        "shoulder",
        "triceps",
        "triceps",
    ]
    assert resistance_kind_list("push", 4, ["tay"]) == [
        "chest",
        "chest",
        "shoulder",
        "triceps",
        "triceps",
    ]
    pull_221 = ["back", "back", "rear", "rear", "biceps"]
    assert kit_kind_list("dumbbell", "pull", 3, ["lung"]) == ["back", "rear", "biceps"]
    assert kit_kind_list("dumbbell", "pull", 4, None) == pull_221
    assert kit_kind_list("dumbbell", "pull", 4, ["lung"]) == pull_221
    assert kit_kind_list("dumbbell", "pull", 4, ["vai"]) == pull_221
    assert kit_kind_list("dumbbell", "pull", 4, ["tay"]) == [
        "back",
        "back",
        "rear",
        "biceps",
        "biceps",
    ]
    legs_60 = kit_kind_list("dumbbell", "legs", 4, None)
    assert kit_kind_list("dumbbell", "legs", 4, ["chan"]) == legs_60
    assert kit_kind_list("dumbbell", "legs", 4, ["mong"]) == legs_60
    vai = [kind for kind, _c in gear_plan("dumbbell", "push", 4, focus_keys=["vai"])]
    assert vai.count("shoulder") == 2
    assert vai.count("chest") == 2
    rings = bar_rings_slots(
        "push",
        pushups_max=20,
        pullups_max=8,
        experience_level=2,
        slots=4,
        focus_keys=["tay"],
    )
    assert len(rings) == 5
    assert rings[-1][0][0] in {"Ring Triceps Extension", "Diamond Push Ups"}
    baseline = bar_rings_slots(
        "push",
        pushups_max=20,
        pullups_max=8,
        experience_level=2,
        slots=4,
    )
    assert len(baseline) == 5
    assert baseline != rings


def test_bump_focus_sets_on_45_priority_lift():
    from types import SimpleNamespace

    day = SimpleNamespace(
        exercises=[
            SimpleNamespace(exercise_id=1, sets=2, section="main"),
            SimpleNamespace(exercise_id=2, sets=2, section="main"),
            SimpleNamespace(exercise_id=3, sets=2, section="main"),
        ]
    )
    meta = {
        1: {"muscle_slug": "chest-mid", "movement_role": "compound", "name_en": "Bench"},
        2: {"muscle_slug": "shoulders-lateral", "movement_role": "isolation", "name_en": "Raise"},
        3: {"muscle_slug": "triceps", "movement_role": "isolation", "name_en": "Kickback"},
    }
    bump_focus_sets(
        [day],
        session_minutes=45,
        focus_keys=["vai"],
        meta_by_id=meta,
        experience_level=2,
    )
    assert day.exercises[0].sets == 2
    assert day.exercises[1].sets == 3
    assert day.exercises[2].sets == 2
    bump_focus_sets(
        [day],
        session_minutes=60,
        focus_keys=["vai"],
        meta_by_id=meta,
        experience_level=2,
    )
    assert day.exercises[1].sets == 3


def test_apply_kit_mains_60_focus_shifts_sets_keeps_abs_cardio():
    db, ids = _db_catalog(
        [
            "Dumbbell Bench Press",
            "Dumbbell Chest Fly",
            "Dumbbell Lateral Raise",
            "Dumbbell Seated Overhead Press",
            "Dumbbell Front Raise",
            "Dumbbell Skullcrusher",
            "Dumbbell Seated Overhead Tricep Extension",
            "Dumbbell Tricep Kickback",
            "Dumbbell Row Bilateral",
            "Dumbbell Hammer Curl",
            "Front Plank on Elbows",
            "Hand Plank",
            "Dead Bug",
            "Elbow Side Plank",
            "V-Up",
            "Bodyweight Russian Twist",
            "Glute Bridge",
            "Dumbbell Situp",
            "Shadow Boxing",
            "Jumping Jack",
            "Trail Run",
            "Hiking",
            "Bird Dog",
        ]
    )
    abs_ids = {
        ids["Front Plank on Elbows"],
        ids["Dead Bug"],
        ids["Elbow Side Plank"],
        ids["V-Up"],
        ids["Bodyweight Russian Twist"],
    }

    def apply(*, role: str, focus, day_number: int):
        day = PlanDayIn(
            day_number=day_number,
            split_role=role,
            exercises=[
                PlanExerciseIn(
                    exercise_id=ids["Dumbbell Bench Press"],
                    sets=3,
                    reps="8-12",
                    section="main",
                ),
                PlanExerciseIn(exercise_id=ids["Bird Dog"], sets=2, reps="10", section="main"),
            ],
        )
        apply_kit_mains(
            day,
            db,
            equipment_slugs=["dumbbell"],
            fitness_baseline={"test_kit": "dumbbell"},
            experience_level=1,
            session_minutes=60,
            meta_by_id={},
            home_session=True,
            challenge_session=True,
            focus_keys=focus,
        )
        return day

    def resistance(day):
        return [ex for ex in day.exercises if ex.section == "main" and ex.exercise_id not in abs_ids]

    nguc = apply(role="push", focus=["nguc"], day_number=1)
    nguc_mains = resistance(nguc)
    chest_sets = sum(
        ex.sets
        for ex in nguc_mains
        if ex.exercise_id in {ids["Dumbbell Bench Press"], ids["Dumbbell Chest Fly"]}
    )
    shoulder_sets = sum(
        ex.sets
        for ex in nguc_mains
        if ex.exercise_id
        in {
            ids["Dumbbell Lateral Raise"],
            ids["Dumbbell Seated Overhead Press"],
            ids["Dumbbell Front Raise"],
        }
    )
    assert chest_sets > shoulder_sets
    assert next(ex.sets for ex in nguc_mains if ex.exercise_id == ids["Dumbbell Bench Press"]) == 3
    assert len([ex for ex in nguc.exercises if ex.section == "cardio"]) == 1
    assert sum(1 for ex in nguc.exercises if ex.section == "main" and ex.exercise_id in abs_ids) >= 1

    vai = apply(role="push", focus=["vai"], day_number=1)
    vai_mains = resistance(vai)
    assert any(
        ex.exercise_id
        in {
            ids["Dumbbell Lateral Raise"],
            ids["Dumbbell Seated Overhead Press"],
            ids["Dumbbell Front Raise"],
        }
        for ex in vai_mains
    )

    even = apply(role="push", focus=["nguc"], day_number=2)
    assert sum(1 for ex in even.exercises if ex.section == "main" and ex.exercise_id in abs_ids) >= 1
    assert len([ex for ex in even.exercises if ex.section == "cardio"]) == 1

    upper = apply(role="upper", focus=["nguc"], day_number=1)
    bench = next(ex for ex in upper.exercises if ex.exercise_id == ids["Dumbbell Bench Press"])
    row = next(ex for ex in upper.exercises if ex.exercise_id == ids["Dumbbell Row Bilateral"])
    assert bench.sets == 3
    assert row.sets == 3
    db.close()


def test_apply_kit_mains_stamps_numeric_reps_when_template_is_timed():
    db, ids = _db_catalog(
        [
            "Dumbbell Bench Press",
            "Dumbbell Chest Fly",
            "Dumbbell Lateral Raise",
            "Dumbbell Seated Overhead Press",
            "Dumbbell Front Raise",
            "Dumbbell Skullcrusher",
            "Dumbbell Row Bilateral",
            "Dumbbell Hammer Curl",
            "Front Plank on Elbows",
        ]
    )
    day = PlanDayIn(
        day_number=1,
        split_role="upper",
        exercises=[
            PlanExerciseIn(
                exercise_id=ids["Front Plank on Elbows"],
                sets=3,
                reps="20-30 giây",
                section="main",
            )
        ],
    )
    apply_kit_mains(
        day,
        db,
        equipment_slugs=["dumbbell"],
        fitness_baseline={
            "test_kit": "dumbbell",
            "db_press_reps": 16,
            "db_press_kg": 10,
            "db_row_reps": 16,
            "db_row_kg": 10,
        },
        experience_level=2,
        session_minutes=60,
        meta_by_id={},
        home_session=True,
        challenge_session=True,
        focus_keys=["nguc"],
    )
    bench = next(ex for ex in day.exercises if ex.exercise_id == ids["Dumbbell Bench Press"])
    assert "giây" not in str(bench.reps).lower()
    assert str(bench.reps) == "8-12"
    db.close()


def test_apply_kit_mains_45_has_five_resistance_kinds():
    db, ids = _challenge_catalog()
    day = _apply_challenge(db, ids, role="push", day_number=1, minutes=45, first="Dumbbell Bench Press")
    mains = [ex for ex in day.exercises if ex.section == "main"]
    assert len(mains) >= 4
    pull = _apply_challenge(db, ids, role="pull", day_number=2, minutes=45, first="Dumbbell Row Bilateral")
    pull_ids = [ex.exercise_id for ex in pull.exercises if ex.section == "main"]
    assert ids["Dumbbell Row Bilateral"] in pull_ids
    assert ids["Dumbbell Row Unilateral"] in pull_ids
    db.close()


def test_challenge_kind_list_phase0_vs_phase1():
    p1_push = ["chest", "chest", "shoulder", "triceps"]
    p2_push = ["chest", "chest", "shoulder", "shoulder", "triceps"]
    rings_p2_push = ["chest", "chest", "shoulder", "chest", "triceps"]
    assert kit_kind_list("dumbbell", "push", 4, phase_index=0) == p1_push
    assert kit_kind_list("dumbbell", "push", 4, phase_index=1) == p2_push
    assert kit_kind_list("dumbbell", "push", 4, phase_index=2) == p2_push
    assert kit_kind_list("band", "push", 5, phase_index=0) == p1_push
    assert kit_kind_list("bar_rings", "push", 5, phase_index=1) == rings_p2_push
    assert challenge_strength_kinds("pull", 0) == ["back", "back", "rear", "biceps"]
    assert challenge_strength_kinds("pull", 1) == ["back", "back", "rear", "rear", "biceps"]
    assert challenge_strength_kinds("legs", 0) == ["legs", "quad"]
    assert challenge_strength_kinds("legs", 2) == ["legs", "quad", "ham"]
    assert kit_kind_list("band", "legs", 4, phase_index=0) == [
        "legs",
        "quad",
        "hinge",
        "glute",
    ]
    assert kit_kind_list("band", "legs", 5, phase_index=1) == [
        "legs",
        "quad",
        "ham",
        "hinge",
        "glute",
    ]
    band_p1 = [name for _k, cands in gear_plan("band", "legs", 4, phase_index=0) for name, _vi in cands]
    assert band_p1[0] == "Band Squat"
    assert "Band Lunge" in band_p1
    assert "Band Romanian Deadlift" in band_p1
    assert "Band Hip Thrust" in band_p1
    band_p2 = [name for _k, cands in gear_plan("band", "legs", 5, phase_index=1) for name, _vi in cands]
    assert "Band Leg Curl" in band_p2
    assert "Band Glute Kickback" in band_p2
    assert "Band Pull-Through" in band_p2
    two_two_one = ["chest", "chest", "shoulder", "shoulder", "triceps"]
    assert kit_kind_list("dumbbell", "push", 4, None) == two_two_one
    p1_kinds = [kind for kind, _c in gear_plan("dumbbell", "push", 4, phase_index=0)]
    p2_kinds = [kind for kind, _c in gear_plan("dumbbell", "push", 4, phase_index=1)]
    assert p1_kinds.count("shoulder") == 1
    assert p2_kinds.count("shoulder") == 2
    assert p1_kinds.count("chest") == 2
    rings_p1 = bar_rings_slots(
        "push",
        pushups_max=20,
        pullups_max=8,
        experience_level=2,
        slots=5,
        phase_index=0,
    )
    rings_p2 = bar_rings_slots(
        "push",
        pushups_max=20,
        pullups_max=8,
        experience_level=2,
        slots=5,
        phase_index=1,
    )
    assert len(rings_p1) == 4
    assert len(rings_p2) == 5
    assert [slot[0][0] for slot in rings_p2] == [
        "Ring Push-Up",
        "Ring Dip",
        "Pike Push-Up",
        "Ring Chest Fly",
        "Ring Triceps Extension",
    ]


def test_challenge_p2_alternates_abs_and_cardio():
    assert challenge_finisher_kind(0, 0) == "both"
    assert challenge_finisher_kind(1, 0) == "abs"
    assert challenge_finisher_kind(1, 1) == "cardio"
    assert challenge_finisher_kind(2, 2) == "abs"
    db, ids = _challenge_catalog()
    abs_ids = {
        ids["Front Plank on Elbows"],
        ids["Dead Bug"],
        ids["Elbow Side Plank"],
        ids["V-Up"],
        ids["Bodyweight Russian Twist"],
        ids["Dumbbell Situp"],
    }
    day1 = _apply_challenge(
        db, ids, role="push", day_number=1, minutes=45, first="Dumbbell Bench Press", phase_index=1
    )
    day2 = _apply_challenge(
        db, ids, role="pull", day_number=2, minutes=45, first="Dumbbell Row Bilateral", phase_index=1
    )
    d1_mains = [ex.exercise_id for ex in day1.exercises if ex.section == "main"]
    d2_mains = [ex.exercise_id for ex in day2.exercises if ex.section == "main"]
    assert abs_ids.intersection(d1_mains)
    assert not [ex for ex in day1.exercises if ex.section == "cardio"]
    assert not abs_ids.intersection(d2_mains)
    assert len([ex for ex in day2.exercises if ex.section == "cardio"]) == 1
    strength1 = [eid for eid in d1_mains if eid not in abs_ids]
    assert len(strength1) == 5
    assert d1_mains.count(ids["Dumbbell Bench Press"]) == 1
    db.close()


def test_challenge_test_lift_sets_by_phase():
    db, ids = _challenge_catalog()
    p1 = _apply_challenge(
        db, ids, role="push", day_number=1, minutes=45, first="Dumbbell Bench Press", phase_index=0
    )
    p2 = _apply_challenge(
        db, ids, role="push", day_number=1, minutes=45, first="Dumbbell Bench Press", phase_index=1
    )
    p3 = _apply_challenge(
        db, ids, role="push", day_number=1, minutes=45, first="Dumbbell Bench Press", phase_index=2
    )
    fly = ids["Dumbbell Chest Fly"]
    bench = ids["Dumbbell Bench Press"]

    def _sets(day, eid):
        return next(ex.sets for ex in day.exercises if ex.exercise_id == eid)

    assert _sets(p1, bench) == 3
    assert _sets(p2, bench) == 4
    assert _sets(p3, bench) == 3
    assert _sets(p1, fly) == 3
    assert _sets(p2, fly) == 3
    assert _sets(p3, fly) == 3
    db.close()


def test_bump_focus_p3_prefers_chest_accessory():
    from types import SimpleNamespace

    day = SimpleNamespace(
        exercises=[
            SimpleNamespace(exercise_id=1, sets=3, section="main"),
            SimpleNamespace(exercise_id=2, sets=3, section="main"),
            SimpleNamespace(exercise_id=3, sets=3, section="main"),
        ]
    )
    meta = {
        1: {"muscle_slug": "chest-mid", "movement_role": "compound", "name_en": "Bench"},
        2: {"muscle_slug": "chest-mid", "movement_role": "isolation", "name_en": "Fly"},
        3: {"muscle_slug": "shoulders-lateral", "movement_role": "isolation", "name_en": "Raise"},
    }
    bump_focus_sets(
        [day],
        session_minutes=45,
        focus_keys=["nguc"],
        meta_by_id=meta,
        experience_level=1,
        skip_test_lift=True,
    )
    assert day.exercises[0].sets == 3
    assert day.exercises[1].sets == 4
    assert day.exercises[2].sets == 3


