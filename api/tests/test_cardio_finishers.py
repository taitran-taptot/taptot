"""100-day challenge cardio allowlist + leftover-minute vs interval dose."""

from app.schemas.plans import PlanDayIn, PlanExerciseIn
from app.services.workout_generation.cardio_finishers import (
    filter_challenge_cardio_items,
    is_challenge_cardio_name,
    is_continuous_finisher_name,
    is_interval_finisher_name,
)
from app.services.workout_generation.session_duration import _rescale_interval_cardios_on_day
from app.services.workout_generation.shortlist import ShortlistItem
from app.services.workout_rest import timed_block_prescription


def _item(eid: int, name_vi: str, name_en: str) -> ShortlistItem:
    return ShortlistItem(
        id=eid,
        name_vi=name_vi,
        movement_role="conditioning",
        movement_pattern="other",
        muscle_slug="conditioning",
        difficulty=1,
        name_en=name_en,
    )


def test_challenge_cardio_allowlist_keeps_six_drops_burpee():
    assert is_challenge_cardio_name("Nhảy dang chân", "Jumping Jack")
    assert is_challenge_cardio_name("Đấm bóng tưởng tượng", "Shadow Boxing")
    assert is_challenge_cardio_name("Nhảy dây", "Jump Rope")
    assert is_challenge_cardio_name("Chạy ngắt quãng", "Running Intervals")
    assert is_challenge_cardio_name("Đi bộ đường dài", "Hiking")
    assert is_challenge_cardio_name("Chạy bền", "Trail Run")
    assert not is_challenge_cardio_name("Burpee", "Burpee")
    assert not is_challenge_cardio_name("Leo núi tại chỗ", "Mountain Climber")
    assert not is_challenge_cardio_name("Đi bộ", "Walk")
    kept = filter_challenge_cardio_items(
        [
            _item(1, "Nhảy dang chân", "Jumping Jack"),
            _item(2, "Burpee", "Burpee"),
            _item(3, "Đi bộ đường dài", "Hiking"),
        ]
    )
    assert {it.id for it in kept} == {1, 3}


def test_interval_vs_continuous_finisher_names():
    assert is_interval_finisher_name("Nhảy dang chân", "Jumping Jack")
    assert is_interval_finisher_name("Nhảy dây", "Jump Rope")
    assert is_continuous_finisher_name("Đi bộ đường dài", "Hiking")
    assert is_continuous_finisher_name("Chạy bền", "Trail Run")
    assert not is_continuous_finisher_name("Nhảy dang chân", "Jumping Jack")
    assert not is_interval_finisher_name("Đi bộ đường dài", "Hiking")


def test_timed_block_hiking_is_one_set_minutes():
    sets, reps, rest, notes = timed_block_prescription(
        block_key="conditioning",
        plan_section="cardio",
        movement_role="conditioning",
        duration_min=10,
        interval_cardio=True,
        experience_level=1,
        name_vi="Đi bộ đường dài",
        name_en="Hiking",
    )
    assert sets == 1
    assert reps == "10 phút"
    assert rest == 0
    assert notes


def test_timed_block_jumping_jack_is_interval_seconds():
    sets, reps, rest, notes = timed_block_prescription(
        block_key="conditioning",
        plan_section="cardio",
        movement_role="conditioning",
        duration_min=10,
        interval_cardio=True,
        experience_level=1,
        name_vi="Nhảy dang chân",
        name_en="Jumping Jack",
    )
    assert sets > 1
    assert "giây" in reps
    assert "phút" not in reps
    assert rest > 0
    assert notes


def test_rescale_keeps_hiking_as_leftover_minutes():
    day = PlanDayIn(
        day_number=1,
        split_role="upper",
        exercises=[
            PlanExerciseIn(
                exercise_id=1, sets=3, reps="10", rest_seconds=90, section="main"
            ),
            PlanExerciseIn(
                exercise_id=2, sets=5, reps="45 giây", rest_seconds=60, section="cardio"
            ),
        ],
    )
    meta = {
        2: _item(2, "Đi bộ đường dài", "Hiking"),
    }
    _rescale_interval_cardios_on_day(day, 20, convert_continuous=True, meta_by_id=meta)
    cardios = [e for e in day.exercises if e.section == "cardio"]
    assert len(cardios) == 1
    assert cardios[0].sets == 1
    assert "phút" in str(cardios[0].reps).lower()
    assert "giây" not in str(cardios[0].reps).lower()
