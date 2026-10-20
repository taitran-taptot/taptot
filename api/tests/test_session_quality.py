"""Session quality: mobility match, timed cardio, hamstrings, warmup rest, fill."""

from app.schemas.plans import PlanDayIn, PlanExerciseIn
from app.services.session_blocks import get_master_session_recipe
from app.services.workout_generation.muscle_quotas import repair_muscle_quotas
from app.services.workout_generation.session_duration import (
    _block_counts,
    _pick_fill_action,
    top_up_session_minutes,
)
from app.services.workout_generation.session_templates import slots_for_session
from app.services.workout_generation.shortlist import ShortlistItem
from app.services.workout_generation.split_map import mobility_match_rank
def test_gym_75_warmup_is_one_stretch():
    blocks = get_master_session_recipe(
        location="gym",
        session_minutes=60,
        split_role="push",
        experience_level=2,
    )
    by_key = {b.block_key: b for b in blocks}
    gen = by_key["general_warmup"]
    assert "dynamic_mobility" not in by_key
    assert gen.count_max == 1
    assert (gen.duration_min_minutes or 0) <= 5


def test_gym_45_cooldown_two_drills():
    blocks = get_master_session_recipe(
        location="gym",
        session_minutes=45,
        split_role="legs",
        experience_level=2,
    )
    cool = next(b for b in blocks if b.block_key == "cooldown")
    assert cool.count_max == 2
    assert (cool.duration_min_minutes or 0) <= 5


def test_home_45_strength_days_have_no_cardio():
    blocks = get_master_session_recipe(
        location="home",
        session_minutes=45,
        split_role="push",
        experience_level=2,
    )
    assert all(b.block_key not in {"conditioning", "cardio"} for b in blocks)
    blocks_60 = get_master_session_recipe(
        location="home",
        session_minutes=60,
        split_role="push",
        experience_level=2,
    )
    cond = next(b for b in blocks_60 if b.block_key == "conditioning")
    assert cond.plan_section == "cardio"
    assert (cond.duration_min_minutes or 0) >= 5


def test_home_45_warmup_is_one_stretch():
    blocks = get_master_session_recipe(
        location="home",
        session_minutes=45,
        split_role="push",
        experience_level=2,
    )
    wu = next(b for b in blocks if b.block_key == "general_warmup")
    assert wu.count_max == 1
    assert (wu.duration_min_minutes or 0) <= 5


def test_legs_30_gym_ham_iso_before_calf():
    slots = slots_for_session("legs", compound_n=1, accessory_n=3, location="gym")
    iso_keys = [s.key for s in slots if s.block == "accessory"]
    assert iso_keys[0] == "ham_iso"
    assert iso_keys[-1] == "calf_iso"
    assert "leg_extra_iso" not in iso_keys
    assert "leg_finisher_iso" not in iso_keys
    extra = next(s for s in slots_for_session("legs", compound_n=2, accessory_n=5, location="gym") if s.key == "leg_extra_iso")
    assert extra.avoid and any("calf" in a for a in extra.avoid)


def test_home_legs_repair_swaps_in_ham_curl():
    blocks = [
        {
            "block_key": "resistance",
            "pick": True,
            "count_max": 2,
            "shortlist": [
                {
                    "id": 1,
                    "movement_pattern": "squat",
                    "movement_role": "resistance",
                    "muscle": "quads",
                },
                {
                    "id": 2,
                    "movement_pattern": "other",
                    "movement_role": "resistance",
                    "muscle": "calves",
                },
                {
                    "id": 3,
                    "movement_pattern": "other",
                    "movement_role": "resistance",
                    "muscle": "hamstrings",
                    "name_vi": "Leg curl",
                },
            ],
        }
    ]
    out = repair_muscle_quotas(
        blocks, {"resistance": [1, 2]}, split_role="legs"
    )
    assert 3 in out["resistance"]


def test_cooldown_rank_prefers_trained_stretch():
    ham = mobility_match_rank(
        muscle_slug="hamstrings",
        name_vi="Giãn hamstring",
        split_role="push",
        cooldown=True,
        trained_slugs=frozenset({"chest"}),
    )
    chest = mobility_match_rank(
        muscle_slug="chest",
        name_vi="Giãn ngực",
        split_role="push",
        cooldown=True,
        trained_slugs=frozenset({"chest"}),
    )
    assert chest < ham


def test_block_counts_isolation_is_not_core():
    day = PlanDayIn(
        day_number=1,
        exercises=[
            PlanExerciseIn(
                exercise_id=1, sets=3, reps="12", rest_seconds=90, section="main"
            ),
            PlanExerciseIn(
                exercise_id=2, sets=3, reps="15", rest_seconds=60, section="main"
            ),
        ],
    )
    meta = {
        1: ShortlistItem(
            id=1,
            name_vi="Fly",
            movement_role="isolation",
            movement_pattern="other",
            muscle_slug="chest",
            difficulty=2,
        ),
        2: ShortlistItem(
            id=2,
            name_vi="Crunch",
            movement_role="isolation",
            movement_pattern="core",
            muscle_slug="core",
            difficulty=2,
        ),
    }
    counts = _block_counts(day, meta)
    assert counts.get("accessory") == 1
    assert counts.get("core") == 1


def test_top_up_does_not_inflate_warmup_or_conditioning_sets():
    day = PlanDayIn(
        day_number=1,
        exercises=[
            PlanExerciseIn(
                exercise_id=1, sets=1, reps="5 phút", rest_seconds=30, section="warmup"
            ),
            PlanExerciseIn(
                exercise_id=2, sets=3, reps="12", rest_seconds=90, section="main"
            ),
            PlanExerciseIn(
                exercise_id=3, sets=1, reps="5 phút", rest_seconds=0, section="cardio"
            ),
        ],
    )
    meta = {
        1: {"movement_role": "mobility", "muscle_slug": "shoulders"},
        2: {"movement_role": "isolation", "muscle_slug": "chest"},
        3: {"movement_role": "conditioning", "muscle_slug": "cardio"},
    }
    out = top_up_session_minutes([day], session_minutes=40, meta_by_id=meta)[0]
    wu = next(e for e in out.exercises if e.section == "warmup")
    card = next(e for e in out.exercises if e.section == "cardio")
    iso = next(e for e in out.exercises if e.section == "main")
    assert wu.reps == "5 phút"
    assert card.sets == 1
    assert iso.sets >= 3


def test_pick_fill_does_not_pad_warmup():
    exercises = [
        PlanExerciseIn(
            exercise_id=1, sets=1, reps="3 phút", rest_seconds=30, section="warmup"
        ),
        PlanExerciseIn(
            exercise_id=2, sets=4, reps="12", rest_seconds=90, section="main"
        ),
    ]
    meta = {
        1: ShortlistItem(
            id=1,
            name_vi="Xoay vai",
            movement_role="mobility",
            movement_pattern="other",
            muscle_slug="shoulders",
            difficulty=1,
        ),
        2: ShortlistItem(
            id=2,
            name_vi="Fly",
            movement_role="isolation",
            movement_pattern="other",
            muscle_slug="chest",
            difficulty=2,
        ),
    }
    changed = _pick_fill_action(exercises, meta, gap=10)
    assert exercises[0].reps == "3 phút"
    if changed:
        assert exercises[1].sets >= 4


def test_gym_core_recipe_is_single_longer_cardio():
    blocks = get_master_session_recipe(
        location="gym", session_minutes=60, split_role="core"
    )
    cardio = [b for b in blocks if b.block_key in {"cardio", "conditioning"}]
    assert len(cardio) == 1
    assert cardio[0].count_max == 1
    assert (cardio[0].duration_min_minutes or 0) >= 20


def test_warmup_drops_pullup_posing_as_stretch():
    from app.services.workout_generation.assemble import inject_main_primer_warmup

    day = PlanDayIn(
        day_number=1,
        split_role="pull",
        exercises=[
            PlanExerciseIn(
                exercise_id=103, sets=2, reps="30 giây", rest_seconds=30, section="warmup"
            ),
            PlanExerciseIn(
                exercise_id=102, sets=3, reps="3-5", rest_seconds=90, section="main"
            ),
        ],
    )
    meta = {
        103: {
            "name_vi": "Hít xà lòng bàn tay hướng vào",
            "name_en": "Chin Ups",
            "movement_role": "compound",
        },
        102: {
            "name_vi": "Hít xà",
            "name_en": "Pull Ups",
            "movement_role": "compound",
        },
    }
    out = inject_main_primer_warmup(day, meta_by_id=meta, home_session=True)
    warmup = [ex for ex in out.exercises if ex.section == "warmup"]
    assert all(ex.exercise_id != 103 for ex in warmup)
    assert warmup[-1].exercise_id == 102


def test_warmup_second_slot_is_lighter_first_main():
    from app.services.workout_generation.assemble import inject_main_primer_warmup

    day = PlanDayIn(
        day_number=1,
        exercises=[
            PlanExerciseIn(
                exercise_id=10, sets=1, reps="3 phút", rest_seconds=30, section="warmup"
            ),
            PlanExerciseIn(
                exercise_id=11, sets=1, reps="2 phút", rest_seconds=30, section="warmup"
            ),
            PlanExerciseIn(
                exercise_id=20, sets=3, reps="6-10", rest_seconds=180, section="main"
            ),
            PlanExerciseIn(
                exercise_id=21, sets=3, reps="10", rest_seconds=90, section="main"
            ),
        ],
    )
    out = inject_main_primer_warmup(day)
    warmup = [ex for ex in out.exercises if ex.section == "warmup"]
    mains = [ex for ex in out.exercises if ex.section == "main"]
    assert len(warmup) == 1
    assert warmup[-1].exercise_id == mains[0].exercise_id == 20
    assert warmup[-1].sets == 2
    assert warmup[-1].reps == "3-5"
    assert warmup[-1].rest_seconds == 90
    assert "chậm" in (warmup[-1].notes_vi or "") or "cham" in (warmup[-1].notes_vi or "").lower()
    assert mains[0].sets == 3
    assert mains[0].reps == "6-10"


def test_free_home_primer_is_one_set_on_short_sessions():
    from app.services.workout_generation.assemble import inject_main_primer_warmup

    day = PlanDayIn(
        day_number=1,
        exercises=[
            PlanExerciseIn(
                exercise_id=10, sets=1, reps="30 giây", rest_seconds=30, section="warmup"
            ),
            PlanExerciseIn(
                exercise_id=20, sets=2, reps="8-12", rest_seconds=45, section="main"
            ),
        ],
    )
    out = inject_main_primer_warmup(
        day, session_minutes=45, home_session=True
    )
    primer = [ex for ex in out.exercises if ex.section == "warmup"][-1]
    assert primer.exercise_id == 20
    assert primer.sets == 2

    long_day = PlanDayIn(
        day_number=1,
        exercises=[
            PlanExerciseIn(
                exercise_id=10, sets=2, reps="30 giây", rest_seconds=30, section="warmup"
            ),
            PlanExerciseIn(
                exercise_id=20, sets=3, reps="8-12", rest_seconds=60, section="main"
            ),
        ],
    )
    long_out = inject_main_primer_warmup(
        long_day, session_minutes=60, home_session=True
    )
    long_primer = [ex for ex in long_out.exercises if ex.section == "warmup"][-1]
    assert long_primer.sets == 2
    assert long_primer.reps == "4-6"
    assert long_primer.rest_seconds == 90


def test_general_warmup_is_jumping_jack_then_half_primer():
    from app.services.workout_generation.assemble import inject_main_primer_warmup

    day = PlanDayIn(
        day_number=1,
        exercises=[
            PlanExerciseIn(exercise_id=9, sets=1, reps="30 giây", rest_seconds=20, section="warmup"),
            PlanExerciseIn(exercise_id=20, sets=3, reps="8-12", rest_seconds=90, section="main"),
        ],
    )
    meta = {
        7: {"id": 7, "name_vi": "Nhảy dang chân", "name_en": "Jumping Jack", "movement_role": "cardio"},
        20: {"name_vi": "Đẩy ngực", "movement_role": "compound", "muscle_slug": "chest"},
    }
    out = inject_main_primer_warmup(day, meta_by_id=meta, home_session=True)
    warmup = [ex for ex in out.exercises if ex.section == "warmup"]
    assert [ex.exercise_id for ex in warmup] == [7, 20]
    assert warmup[0].sets == 2
    assert warmup[0].reps == "20-30 giây"
    assert warmup[0].rest_seconds == 60
    assert warmup[1].sets == 2
    assert warmup[1].reps == "4-6"
    assert warmup[1].rest_seconds == 90


def test_cooldown_prefers_geared_stretch_for_trained_muscle():
    from app.services.workout_generation.assemble import ensure_cooldown_stretches

    day = PlanDayIn(
        day_number=1,
        split_role="push",
        exercises=[
            PlanExerciseIn(exercise_id=20, sets=3, reps="8-12", section="main"),
            PlanExerciseIn(exercise_id=99, sets=2, reps="30 giây", section="cooldown"),
        ],
    )
    meta = {
        20: ShortlistItem(20, "Đẩy ngực", "compound", "h_push", "chest", 2, name_en="Chest Press"),
        99: ShortlistItem(99, "Giãn chân", "mobility", "other", "stretch", 1, name_en="Leg stretch"),
    }
    shortlists = {
        "cooldown": [
            ShortlistItem(99, "Giãn chân", "mobility", "other", "stretch", 1, name_en="Leg stretch"),
            ShortlistItem(
                31,
                "Giãn ngực tay không",
                "mobility",
                "other",
                "stretch",
                1,
                name_en="Chest stretch",
            ),
            ShortlistItem(
                32,
                "Giãn ngực dây",
                "mobility",
                "other",
                "stretch",
                1,
                name_en="Band chest stretch",
                equipment_slugs=frozenset({"resistance-band"}),
            ),
        ]
    }
    ensure_cooldown_stretches(
        day,
        shortlists=shortlists,
        used_ids=set(),
        meta_by_id=meta,
        session_minutes=45,
        equipment_slugs=["resistance-band"],
    )
    cooldown = [ex for ex in day.exercises if ex.section == "cooldown"]
    assert [ex.exercise_id for ex in cooldown] == [32]


def test_pull_cooldown_uses_bodyweight_back_stretch_without_gear_stretch():
    from app.services.workout_generation.assemble import ensure_cooldown_stretches
    from app.services.workout_generation.split_map import stretch_matches_region

    day = PlanDayIn(
        day_number=1,
        split_role="pull",
        exercises=[
            PlanExerciseIn(exercise_id=20, sets=3, reps="8-12", section="main"),
        ],
    )
    meta = {
        20: ShortlistItem(20, "Kéo xô", "compound", "v_pull", "back", 2, name_en="Band Pulldown"),
    }
    shoulder = ShortlistItem(
        40,
        "Giãn vai ngang",
        "mobility",
        "other",
        "stretch",
        1,
        name_en="Cross-Body Shoulder Stretch",
    )
    child = ShortlistItem(41, "Tư thế em bé (giãn lưng)", "mobility", "other", "stretch", 1, name_en="Child's Pose")
    twist = ShortlistItem(42, "Xoay cột sống ngồi", "mobility", "other", "stretch", 1, name_en="Seated Spinal Twist")
    assert not stretch_matches_region(shoulder, "back")
    assert stretch_matches_region(child, "back")
    assert stretch_matches_region(twist, "back")
    ensure_cooldown_stretches(
        day,
        shortlists={"cooldown": [shoulder, twist, child]},
        used_ids=set(),
        meta_by_id=meta,
        session_minutes=45,
        equipment_slugs=["resistance-band-2"],
    )
    cooldown = [ex.exercise_id for ex in day.exercises if ex.section == "cooldown"]
    assert 40 not in cooldown
    assert cooldown[0] == 41
