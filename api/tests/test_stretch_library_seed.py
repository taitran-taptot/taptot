"""Restore stretch exercises from unassigned complete-library videos."""

from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.core.migrations import ensure_stretch_library_from_videos
from app.services.muscle_group_hierarchy_seed import seed_muscle_group_hierarchy
from app.services.stretch_library_seed import STRETCH_CLIPS, seed_stretch_library_from_videos


def _build_sqlite(tmp_path: Path):
    engine = create_engine("sqlite:///:memory:")
    now = datetime.now(UTC).isoformat()
    video_dir = tmp_path / "media" / "complete-exercise-library"
    video_dir.mkdir(parents=True)
    for item in STRETCH_CLIPS:
        (video_dir / f"{item['slug']}.mp4").write_bytes(b"mp4")
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE muscle_groups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    slug TEXT NOT NULL UNIQUE,
                    name_vi TEXT NOT NULL,
                    name_en TEXT,
                    sort_order INTEGER NOT NULL DEFAULT 0,
                    parent_id INTEGER,
                    is_filter_only INTEGER NOT NULL DEFAULT 0
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE equipment (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    slug TEXT NOT NULL UNIQUE,
                    name_vi TEXT NOT NULL,
                    name_en TEXT,
                    category TEXT,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    sort_order INTEGER NOT NULL DEFAULT 0,
                    image_url TEXT,
                    specs_vi TEXT
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE exercises (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name_vi TEXT NOT NULL,
                    name_en TEXT,
                    muscle_group_id INTEGER NOT NULL,
                    exercise_type TEXT NOT NULL DEFAULT 'main',
                    movement_role TEXT,
                    movement_pattern TEXT,
                    venue TEXT,
                    difficulty INTEGER NOT NULL DEFAULT 2,
                    difficulty_label TEXT,
                    notes_vi TEXT,
                    video_url TEXT,
                    gif_url TEXT,
                    image_url TEXT,
                    secondary_muscles TEXT NOT NULL DEFAULT '[]',
                    instruction_vi TEXT,
                    instruction_steps_vi TEXT,
                    common_mistakes_vi TEXT,
                    tips_vi TEXT,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    owner_user_id TEXT,
                    created_by TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE exercise_equipment (
                    exercise_id INTEGER NOT NULL,
                    equipment_id INTEGER NOT NULL,
                    PRIMARY KEY (exercise_id, equipment_id)
                )
                """
            )
        )
        conn.execute(
            text(
                "INSERT INTO equipment (slug, name_vi, name_en, is_active) "
                "VALUES ('gymnastic-rings', 'Vòng treo', 'Gymnastic Rings', 1)"
            )
        )
        seed_muscle_group_hierarchy(conn, is_sqlite=True)
        _ = now
    return engine


def test_stretch_seed_upserts_cooldown_rows(tmp_path, monkeypatch):
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    from app.core.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setattr(
        "app.services.stretch_library_seed.get_settings",
        lambda: type("S", (), {"upload_dir": str(tmp_path)})(),
    )
    engine = _build_sqlite(tmp_path)
    with Session(engine) as db:
        n = seed_stretch_library_from_videos(db, media_root=tmp_path / "media")
        db.commit()
    assert n == len(STRETCH_CLIPS)

    with engine.begin() as conn:
        rows = conn.execute(
            text(
                "SELECT name_en, exercise_type, movement_role, muscle_group_id, video_url, is_active "
                "FROM exercises WHERE notes_vi LIKE 'seed:stretch-video:%' ORDER BY name_en"
            )
        ).fetchall()
        assert len(rows) == len(STRETCH_CLIPS)
        stretch_id = conn.execute(
            text("SELECT id FROM muscle_groups WHERE slug = 'stretch'")
        ).scalar()
        for row in rows:
            assert row[1] == "cooldown"
            assert row[2] == "mobility"
            assert int(row[3]) == int(stretch_id)
            assert str(row[4]).startswith("complete-exercise-library/")
            assert int(row[5]) == 1

        linked = conn.execute(
            text(
                """
                SELECT e.name_en FROM exercise_equipment ee
                JOIN equipment eq ON eq.id = ee.equipment_id
                JOIN exercises e ON e.id = ee.exercise_id
                WHERE eq.slug = 'gymnastic-rings'
                ORDER BY e.name_en
                """
            )
        ).fetchall()
        assert [r[0] for r in linked] == ["Ring Lat Stretch", "Ring Pec Stretch"]

        child = conn.execute(
            text("SELECT name_vi FROM exercises WHERE name_en = 'Child''s Pose'")
        ).scalar()
        assert child


def test_ensure_stretch_library_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.services.stretch_library_seed.get_settings",
        lambda: type("S", (), {"upload_dir": str(tmp_path)})(),
    )
    engine = _build_sqlite(tmp_path)
    ensure_stretch_library_from_videos(engine)
    ensure_stretch_library_from_videos(engine)
    with engine.begin() as conn:
        n = conn.execute(
            text("SELECT COUNT(*) FROM exercises WHERE notes_vi LIKE 'seed:stretch-video:%'")
        ).scalar()
        assert int(n) == len(STRETCH_CLIPS)
