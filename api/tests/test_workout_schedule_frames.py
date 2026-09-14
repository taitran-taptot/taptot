"""Tests for coach workout schedule frame seed + ensure migrator."""

from sqlalchemy import create_engine, text

from app.core.migrations import ensure_workout_schedule_frames
from app.services.workout_schedule_frame_seed import SCHEDULE_FRAME_SEED, frames_as_dicts


def test_seed_has_fifteen_frames_levels_1_to_3():
    frames = frames_as_dicts()
    assert len(frames) == 15
    assert {f["experience_level"] for f in frames} == {1, 2, 3}
    assert {f["sessions_per_week"] for f in frames} == {2, 3, 4, 5, 6}
    for f in frames:
        assert len(f["days"]) == f["sessions_per_week"]
        assert [d["day_index"] for d in f["days"]] == list(range(f["sessions_per_week"]))


def test_ensure_creates_and_seeds_sqlite(tmp_path):
    db = tmp_path / "frames.db"
    engine = create_engine(f"sqlite:///{db}")
    ensure_workout_schedule_frames(engine)
    with engine.connect() as conn:
        n_frames = conn.execute(text("SELECT COUNT(*) FROM workout_schedule_frames")).scalar()
        n_days = conn.execute(text("SELECT COUNT(*) FROM workout_schedule_frame_days")).scalar()
        assert int(n_frames) == len(SCHEDULE_FRAME_SEED)
        expected_days = sum(len(spec[-1]) for spec in SCHEDULE_FRAME_SEED)
        assert int(n_days) == expected_days

        row = conn.execute(
            text(
                "SELECT name_vi FROM workout_schedule_frames "
                "WHERE experience_level = 1 AND sessions_per_week = 2"
            )
        ).fetchone()
        assert row is not None
        assert "Push" in row[0] or "Toàn thân" in row[0]

        # Idempotent — second call does not duplicate
        ensure_workout_schedule_frames(engine)
        n2 = conn.execute(text("SELECT COUNT(*) FROM workout_schedule_frames")).scalar()
        assert int(n2) == len(SCHEDULE_FRAME_SEED)
