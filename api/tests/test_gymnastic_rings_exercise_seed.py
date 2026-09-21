"""Seed gymnastic-rings exercises for home schedule generation."""

from datetime import UTC, datetime

from sqlalchemy import create_engine, text

from app.core.migrations import ensure_gymnastic_rings_exercises, ensure_home_equipment_catalog_v2
from app.services.gymnastic_rings_exercise_seed import (
    load_ring_exercise_seed,
    seed_gymnastic_rings_exercises,
)
from app.services.muscle_group_hierarchy_seed import seed_muscle_group_hierarchy


def _build_sqlite():
    engine = create_engine("sqlite:///:memory:")
    now = datetime.now(UTC).isoformat()
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
                    image_url TEXT
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
                    secondary_muscles TEXT NOT NULL DEFAULT '[]',
                    instruction_steps_vi TEXT,
                    common_mistakes_vi TEXT,
                    tips_vi TEXT,
                    is_active INTEGER NOT NULL DEFAULT 1,
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
        seed_muscle_group_hierarchy(conn, is_sqlite=True)
        # placeholder timestamp unused but schema ready
        _ = now
    return engine


def test_ring_seed_file_has_back_chest_arm_coverage():
    items = load_ring_exercise_seed()
    assert len(items) >= 16
    slugs = {i["slug"] for i in items}
    assert "ring-push-up" in slugs
    assert "ring-row" in slugs
    assert "ring-dip" in slugs
    assert "ring-biceps-curl" in slugs
    assert "ring-triceps-extension" in slugs
    assert "ring-dead-hang" in slugs
    assert "ring-pec-stretch" in slugs
    assert "ring-lat-stretch" in slugs
    assert "ring-face-pull" in slugs
    assert "ring-rear-delt-fly" in slugs
    assert "ring-hold" in slugs
    muscles = {i["muscle_slug"] for i in items}
    assert "chest-mid" in muscles or "chest-lower" in muscles
    assert "back-middle" in muscles or "back-lats" in muscles
    assert "biceps" in muscles
    assert "triceps" in muscles
    assert "shoulders-rear" in muscles
    assert "shoulders-front" in muscles
    mobility = [i for i in items if i.get("movement_role") == "mobility"]
    assert len(mobility) >= 3
    assert all(i.get("exercise_type") == "warmup" for i in mobility)


def test_seed_upserts_and_links_gymnastic_rings():
    engine = _build_sqlite()
    ensure_home_equipment_catalog_v2(engine)
    ensure_gymnastic_rings_exercises(engine)

    with engine.begin() as conn:
        eq = conn.execute(
            text("SELECT id, is_active FROM equipment WHERE slug = 'gymnastic-rings'")
        ).fetchone()
        assert eq is not None
        assert int(eq[1]) == 1

        n = conn.execute(
            text("SELECT COUNT(*) FROM exercises WHERE notes_vi LIKE 'seed:gymnastic-rings:%'")
        ).scalar()
        assert int(n) == len(load_ring_exercise_seed())

        linked = conn.execute(
            text(
                """
                SELECT COUNT(*) FROM exercise_equipment ee
                JOIN equipment eq ON eq.id = ee.equipment_id
                JOIN exercises e ON e.id = ee.exercise_id
                WHERE eq.slug = 'gymnastic-rings'
                  AND e.notes_vi LIKE 'seed:gymnastic-rings:%'
                """
            )
        ).scalar()
        assert int(linked) == int(n)

        row = conn.execute(
            text(
                "SELECT venue, movement_pattern, difficulty, is_active "
                "FROM exercises WHERE name_en = 'Ring Row'"
            )
        ).fetchone()
        assert row is not None
        assert row[0] == "home"
        assert row[1] == "h_pull"
        assert int(row[2]) == 2
        assert int(row[3]) == 1

        chin = conn.execute(
            text(
                "SELECT is_active FROM exercises WHERE notes_vi = 'seed:gymnastic-rings:ring-chin-up'"
            )
        ).scalar()
        assert int(chin) == 0
        for marker in (
            "seed:gymnastic-rings:archer-ring-row",
            "seed:gymnastic-rings:ring-support-hold",
        ):
            flag = conn.execute(
                text("SELECT is_active FROM exercises WHERE notes_vi = :m"),
                {"m": marker},
            ).scalar()
            assert int(flag) == 0

    # idempotent
    ensure_gymnastic_rings_exercises(engine)
    with engine.begin() as conn:
        n2 = conn.execute(
            text("SELECT COUNT(*) FROM exercises WHERE notes_vi LIKE 'seed:gymnastic-rings:%'")
        ).scalar()
        assert int(n2) == len(load_ring_exercise_seed())


def test_seed_function_returns_count():
    engine = _build_sqlite()
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO equipment (slug, name_vi, name_en, is_active) "
                "VALUES ('gymnastic-rings', 'Vòng treo', 'Gymnastic Rings', 1)"
            )
        )
        n = seed_gymnastic_rings_exercises(conn, is_sqlite=True)
    assert n == len(load_ring_exercise_seed())


def test_band2_front_raise_seed_links_resistance_band_2():
    from app.core.migrations import ensure_resistance_band_2_exercises
    from app.services.gymnastic_rings_exercise_seed import (
        load_band2_exercise_seed,
        seed_resistance_band_2_exercises,
    )

    engine = _build_sqlite()
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO equipment (slug, name_vi, name_en, is_active) VALUES "
                "('resistance-band-1', 'Dây kháng lực 1', 'Resistance Band 1', 1),"
                "('resistance-band-2', 'Dây kháng lực 2', 'Resistance Band 2', 1)"
            )
        )
        n = seed_resistance_band_2_exercises(conn, is_sqlite=True)
    items = load_band2_exercise_seed()
    assert n == len(items) >= 12
    slugs = {i["slug"] for i in items}
    assert "band-front-raise" in slugs
    assert "band-chest-press" in slugs
    assert "band-clamshell" in slugs
    assert "band-pull-apart" in slugs

    ensure_resistance_band_2_exercises(engine)
    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                SELECT e.name_en, e.venue, mg.slug, eq.slug
                FROM exercises e
                JOIN muscle_groups mg ON mg.id = e.muscle_group_id
                JOIN exercise_equipment ee ON ee.exercise_id = e.id
                JOIN equipment eq ON eq.id = ee.equipment_id
                WHERE e.notes_vi = 'seed:resistance-band-2:band-front-raise'
                """
            )
        ).fetchone()
        assert row is not None
        assert row[0] == "Band Front Raise"
        assert row[1] == "home"
        assert row[2] == "shoulders-front"
        assert row[3] == "resistance-band-2"

        press = conn.execute(
            text(
                """
                SELECT eq.slug FROM exercises e
                JOIN exercise_equipment ee ON ee.exercise_id = e.id
                JOIN equipment eq ON eq.id = ee.equipment_id
                WHERE e.notes_vi = 'seed:resistance-band-2:band-chest-press'
                """
            )
        ).scalar()
        assert press == "resistance-band-2"

        clam = conn.execute(
            text(
                """
                SELECT eq.slug FROM exercises e
                JOIN exercise_equipment ee ON ee.exercise_id = e.id
                JOIN equipment eq ON eq.id = ee.equipment_id
                WHERE e.notes_vi = 'seed:resistance-band-1:band-clamshell'
                """
            )
        ).scalar()
        assert clam == "resistance-band-1"
