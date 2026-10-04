"""Beginner-friendly Vietnamese exercise copy overlay."""

from datetime import UTC, datetime

from sqlalchemy import create_engine, text

from app.core.migrations import ensure_exercise_copy_vi
from app.services.exercise_copy_seed import (
    load_exercise_copy_seed,
    seed_exercise_copy,
    validate_copy_seed,
)


def _build_sqlite():
    engine = create_engine("sqlite:///:memory:")
    now = datetime.now(UTC).isoformat()
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE exercises (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name_vi TEXT NOT NULL,
                    name_en TEXT,
                    muscle_group_id INTEGER NOT NULL DEFAULT 1,
                    exercise_type TEXT NOT NULL DEFAULT 'main',
                    instruction_vi TEXT,
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
                INSERT INTO exercises
                    (id, name_vi, name_en, instruction_vi, instruction_steps_vi,
                     common_mistakes_vi, tips_vi, created_at, updated_at)
                VALUES
                    (25, 'Ngồi xổm không tạ', 'Bodyweight Squat',
                     'old', '["old"]',
                     '[''Cong lưng.'']',
                     'Placeholder tạm — sẽ bổ sung video sau.',
                     :now, :now),
                    (554, 'Nhấc tạ đòn từ đất', 'Barbell Deadlift',
                     'old', '["old"]',
                     '[''Cong lưng khi nâng, làm yếu cột sống dưới tải trọng nặng.'']',
                     NULL,
                     :now, :now),
                    (63, 'Ép ngực tạ đơn', 'Dumbbell Bench Press',
                     'old', '["old"]',
                     '[''Nảy tạ.'']',
                     NULL,
                     :now, :now)
                """
            ),
            {"now": now},
        )
    return engine


def test_copy_seed_file_covers_active_catalog_and_passes_hygiene():
    items = load_exercise_copy_seed()
    assert len(items) == 353
    names = {str(item["name_en"]) for item in items}
    for required in (
        "Bodyweight Squat",
        "Barbell Bench Press",
        "Barbell Deadlift",
        "Wall Push-up",
        "Ring Push-Up",
        "Pull Ups",
    ):
        assert required in names
    problems = validate_copy_seed(items)
    assert problems == []


def test_validate_copy_entry_flags_short_mistakes_and_spotter_on_machine():
    from app.services.exercise_copy_seed import validate_copy_entry

    bad = {
        "name_en": "Incline Machine Chest Press",
        "instruction_vi": "Đẩy ngực máy.",
        "instruction_steps_vi": ["a", "b", "c", "d"],
        "common_mistakes_vi": ["Nảy.", "Cong lưng."],
        "tips_vi": "Cần người hỗ trợ khi tạ đòn nặng.",
    }
    problems = validate_copy_entry(bad)
    assert any("too short" in p for p in problems)
    assert any("spotter" in p for p in problems)


def test_seed_updates_instruction_fields_and_is_idempotent():
    engine = _build_sqlite()
    with engine.begin() as conn:
        first = seed_exercise_copy(conn, is_sqlite=True)
        second = seed_exercise_copy(conn, is_sqlite=True)
    assert first == 3
    assert second == 3

    with engine.begin() as conn:
        squat = conn.execute(
            text(
                "SELECT instruction_vi, instruction_steps_vi, common_mistakes_vi, tips_vi "
                "FROM exercises WHERE name_en = 'Bodyweight Squat'"
            )
        ).fetchone()
        deadlift = conn.execute(
            text(
                "SELECT common_mistakes_vi, tips_vi FROM exercises "
                "WHERE name_en = 'Barbell Deadlift'"
            )
        ).fetchone()

    assert squat is not None
    assert squat[0] and "ngồi xổm" in squat[0].lower()
    assert squat[1].startswith("[")
    assert "gối sụp" in squat[2].lower()
    assert not squat[2].lstrip().startswith("[")
    assert squat[3]
    assert "placeholder" not in squat[3].lower()

    assert deadlift is not None
    assert not deadlift[0].lstrip().startswith("[")
    assert "cong lưng" in deadlift[0].lower()
    assert deadlift[1]


def test_ensure_exercise_copy_vi_wrapper():
    engine = _build_sqlite()
    ensure_exercise_copy_vi(engine)
    with engine.begin() as conn:
        tips = conn.execute(
            text("SELECT tips_vi FROM exercises WHERE name_en = 'Bodyweight Squat'")
        ).scalar()
        press_name = conn.execute(
            text("SELECT name_vi FROM exercises WHERE name_en = 'Dumbbell Bench Press'")
        ).scalar()
    assert tips
    assert "placeholder" not in str(tips).lower()
    assert press_name == "Đẩy ngực tạ đơn"


def _blob(item: dict) -> str:
    steps = item.get("instruction_steps_vi") or []
    mistakes = item.get("common_mistakes_vi") or []
    return " ".join(
        [
            str(item.get("instruction_vi") or ""),
            " ".join(str(x) for x in steps),
            " ".join(str(x) for x in mistakes),
            str(item.get("tips_vi") or ""),
        ]
    )


def test_worst_copy_clusters_are_not_mismatched():
    by_en = {str(item["name_en"]): item for item in load_exercise_copy_seed()}

    bench = _blob(by_en["Bench Dips"])
    assert "hai tay chống xà" not in bench
    assert "Nắm song song" not in bench
    assert "mép ghế" in bench
    parallel = _blob(by_en["Parallel Bar Dips"])
    assert "Nắm song song" in parallel

    reverse = _blob(by_en["Reverse Pec Deck"])
    assert "tạ treo" not in reverse
    assert "ngực áp đệm" in reverse.lower() or "Ngồi máy" in reverse

    high = _blob(by_en["Hammer Strength High Row"])
    assert "Kéo tạ về phía hông" not in high
    assert "cúi hông" not in high.lower()
    assert "ngực trên" in high
    iso = _blob(by_en["Hammer Strength Iso-Lateral Row"])
    assert "cúi hông" not in iso.lower()
    assert "Kéo tạ về hông" not in iso

    for name, item in by_en.items():
        blob = _blob(item)
        if "curl" in name.lower() and "preacher" not in name.lower() and "leg" not in name.lower():
            assert "Khuỷu rời đệm tựa" not in blob, name
        if "preacher" in name.lower() and "curl" in name.lower():
            assert "Khuỷu rời đệm tựa" in blob, name

    for name in (
        "Band External Rotation",
        "Single-Leg Step-Down",
        "Sled Pull",
        "Sled Push/Pull",
    ):
        blob = _blob(by_en[name])
        assert "Vào tư thế ổn định cho bài" not in blob, name
        assert "biến thể máy" not in blob, name

    for name, item in by_en.items():
        low = name.lower()
        if ("machine" in low or "smith" in low) and ("row" in low or "pulldown" in low):
            blob = _blob(item)
            assert "Treo người" not in blob, name
            assert "cằm qua xà" not in blob, name

    pullups = _blob(by_en["Pull Ups"])
    assert "xà" in pullups
    chins = _blob(by_en["Chin Ups"])
    assert "xà" in chins

    wall = _blob(by_en["Wall Ball"])
    assert "Vào tư thế ổn định cho bài" not in wall
    assert "biến thể máy" not in wall
    assert "ném" in wall.lower()

    landmine = _blob(by_en["Landmine T Bar Rows"])
    assert "cắm đất" in landmine
    assert "tạ treo" not in landmine

    belt = _blob(by_en["Belt Squat"])
    assert "đai" in belt.lower()
    assert "lưng/hông dán đệm" not in belt
    assert "bàn đạp" not in belt

    band_curl = _blob(by_en["Band Leg Curl"])
    assert "máy cuốn đùi" not in band_curl
    db_leg = _blob(by_en["Dumbbell Leg Curl"])
    assert "máy cuốn đùi" not in db_leg

    calf_press = _blob(by_en["Calf Press"])
    assert "bàn đạp" in calf_press
    assert "cổ chân" in calf_press

    pullover = _blob(by_en["Machine Lat Pullover"])
    assert "Ngồi máy" in pullover or "ngồi máy" in pullover
    assert "Nằm ghế hoặc đứng cúi" not in pullover

    ffe = _blob(by_en["Front-Foot-Elevated Split Squat"])
    assert "bục" in ffe
    assert "Bước chân trước, hạ gối sau" not in ffe

    jerk = _blob(by_en["Push Jerk"])
    assert "tách chân" in jerk
    assert "Vào tư thế, thân ổn định" not in jerk

    sa_tri = _blob(by_en["Single-Arm Tricep Extension"])
    assert "sau đầu" in sa_tri or "trên đầu" in sa_tri

    cross = _blob(by_en["Cross-Body Hammer Curl"])
    assert "chéo" in cross

    gm = _blob(by_en["Good Mornings"])
    assert "Vào tư thế, thân ổn định" not in gm
    assert "sau vai" in gm

    hinge = _blob(by_en["Hip Hinge Speed Romanian Deadlift"])
    assert "Vào tư thế, thân ổn định" not in hinge

    lat_raise = _blob(by_en["Machine Lateral Raise"])
    assert "Tạ dọc người" not in lat_raise

    smith_row = _blob(by_en["Smith Machine Bent-Over Row"])
    assert "tạ treo" not in smith_row

    lat = _blob(by_en["Bodyweight Alternating Lateral Lunge"])
    assert "sang ngang" in lat
    assert "Bước chân trước, hạ gối sau" not in lat

    curtsy = _blob(by_en["Dumbbell Goblet Alternating Curtsy Lunge"])
    assert "chéo" in curtsy.lower()

    abduct = _blob(by_en["Bodyweight Hip Abduction"])
    assert "ngồi máy" not in abduct.lower()

    cab_bench = _blob(by_en["Cable Bench Press"])
    assert "Ngồi/nằm máy" not in cab_bench
    assert "Nằm ghế" in cab_bench or "nằm ghế" in cab_bench

    cab_chest = _blob(by_en["Cable Chest Press"])
    assert "Đứng giữa hai cột" in cab_chest

    tbar = _blob(by_en["Chest-Supported T-Bar Row"])
    assert "ngực" in tbar.lower()
    assert "Cúi hông, lưng thẳng" not in tbar

    skull = _blob(by_en["Dumbbell Skullcrusher"])
    assert "Nằm ghế" in skull
    assert "trán" in skull or "sau đầu" in skull

    situp = _blob(by_en["Dumbbell Situp"])
    assert "tạ" in situp.lower()

    band_pd = _blob(by_en["Band Seated Pulldown"])
    assert "nắm thanh" not in band_pd.lower()
    assert "dây" in band_pd.lower()
