"""Integration-ish tests for hybrid workout generation (deterministic path)."""

from datetime import datetime, timezone
import re

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.migrations import (
    ensure_familiarization_exercises,
    ensure_exercise_prescription_defaults,
    ensure_exercise_venue_and_difficulty_v2,
    ensure_plan_day_nutrition,
    ensure_session_block_templates,
)
from app.main import create_app
from app.services.workout_generation.service import generate_workout
from app.services.workout_generation.weekly_volume import is_pushup_name

TEST_USER_ID = "00000000-0000-4000-8000-000000000001"


def _as_phase_picker(weekly_fn):
    def _phase(week_payload, profile=None, phase=None, **_k):
        days = weekly_fn(week_payload, profile=profile)
        return {"days": days, "week_b": days, "rationale_vi": "test"}

    return _phase


def _setup_engine(tmp_path):
    db = tmp_path / "gen.db"
    engine = create_engine(f"sqlite:///{db}")
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE users (
                    id TEXT PRIMARY KEY,
                    email TEXT,
                    role TEXT NOT NULL DEFAULT 'user'
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE muscle_groups (
                    id INTEGER PRIMARY KEY,
                    slug TEXT NOT NULL,
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
                    id INTEGER PRIMARY KEY,
                    slug TEXT NOT NULL UNIQUE,
                    name_vi TEXT NOT NULL,
                    name_en TEXT,
                    category TEXT,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    sort_order INTEGER NOT NULL DEFAULT 0
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE exercises (
                    id INTEGER PRIMARY KEY,
                    name_vi TEXT NOT NULL,
                    name_en TEXT,
                    muscle_group_id INTEGER NOT NULL,
                    exercise_type TEXT NOT NULL DEFAULT 'main',
                    movement_role TEXT,
                    movement_pattern TEXT,
                    difficulty INTEGER NOT NULL DEFAULT 2,
                    difficulty_label TEXT,
                    notes_vi TEXT,
                    secondary_muscles TEXT NOT NULL DEFAULT '[]',
                    instruction_vi TEXT,
                    instruction_steps_vi TEXT,
                    common_mistakes_vi TEXT,
                    tips_vi TEXT,
                    gif_url TEXT,
                    image_url TEXT,
                    video_url TEXT,
                    owner_user_id TEXT,
                    venue TEXT NOT NULL DEFAULT 'both',
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_by TEXT,
                    created_at TEXT,
                    updated_at TEXT
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
        # Minimal plan tables used by PlanService.create_plan
        conn.execute(
            text(
                """
                CREATE TABLE user_daily_plans (
                    id INTEGER PRIMARY KEY,
                    user_id TEXT,
                    title_vi TEXT NOT NULL,
                    description_vi TEXT,
                    start_date TEXT,
                    end_date TEXT,
                    target_calories INTEGER,
                    target_protein_g REAL,
                    target_carbs_g REAL,
                    target_fat_g REAL,
                    source TEXT NOT NULL DEFAULT 'manual',
                    is_template INTEGER NOT NULL DEFAULT 0,
                    share_token TEXT,
                    ai_generation_id INTEGER,
                    insights_json TEXT,
                    challenge_100_days INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT,
                    updated_at TEXT
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE user_daily_plan_days (
                    id INTEGER PRIMARY KEY,
                    plan_id INTEGER NOT NULL,
                    day_number INTEGER NOT NULL,
                    title_vi TEXT,
                    notes_vi TEXT
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE user_daily_plan_exercises (
                    id INTEGER PRIMARY KEY,
                    plan_day_id INTEGER NOT NULL,
                    exercise_id INTEGER NOT NULL,
                    sets INTEGER NOT NULL DEFAULT 3,
                    reps TEXT,
                    rest_seconds INTEGER NOT NULL DEFAULT 120,
                    section TEXT NOT NULL DEFAULT 'main',
                    notes_vi TEXT,
                    sort_order INTEGER NOT NULL DEFAULT 0,
                    rir INTEGER,
                    rpe REAL,
                    tempo TEXT,
                    technique TEXT,
                    superset_group INTEGER,
                    set_prescriptions TEXT
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE user_daily_plan_meals (
                    id INTEGER PRIMARY KEY,
                    plan_day_id INTEGER NOT NULL,
                    food_id INTEGER NOT NULL,
                    meal_type TEXT NOT NULL DEFAULT 'lunch',
                    servings REAL NOT NULL DEFAULT 1,
                    notes_vi TEXT,
                    sort_order INTEGER NOT NULL DEFAULT 0
                )
                """
            )
        )

        conn.execute(
            text(
                "INSERT INTO muscle_groups (id, slug, name_vi, sort_order) VALUES "
                "(1,'chest','Ngực',1),(2,'back','Lưng',2),(3,'core','Core',3),"
                "(4,'co-dui-truoc','Đùi trước',4),(5,'biceps','Tay trước',5),"
                "(6,'triceps','Tay sau',6),(7,'shoulders','Vai',7),(8,'glutes','Mông',8)"
            )
        )
        now = datetime.now(timezone.utc).isoformat()
        exercises = [
            (1, "Bench", 1, "compound", "h_push", 1),
            (2, "OHP", 1, "compound", "v_push", 2),
            (3, "Fly", 1, "isolation", "h_push", 2),
            (4, "Lateral raise", 7, "isolation", "v_push", 2),
            (5, "Row", 2, "compound", "h_pull", 2),
            (6, "Pulldown", 2, "compound", "v_pull", 2),
            (7, "Curl", 5, "isolation", "h_pull", 2),
            (8, "Face pull", 7, "isolation", "h_pull", 2),
            (9, "Squat", 4, "compound", "squat", 2),
            (10, "RDL", 8, "compound", "hinge", 2),
            (11, "Leg ext", 4, "isolation", "squat", 2),
            (12, "Leg curl", 4, "isolation", "hinge", 2),
            (13, "Plank", 3, "isolation", "core", 1),
            (14, "Crunch", 3, "isolation", "core", 1),
            (15, "Arm circle", 1, "mobility", "other", 1),
            (16, "Hip open", 4, "mobility", "other", 1),
            (17, "Jog", 3, "cardio", "other", 1),
            (18, "Stretch chest", 1, "mobility", "other", 1),
        ]
        extra = [
            (19, "Chống đẩy", None, 1, "compound", "h_push", 1),
            (20, "Chống đẩy kim cương", None, 1, "isolation", "h_push", 1),
            (21, "Chống đẩy chống gối", None, 1, "compound", "h_push", 1),
            (22, "Chống đẩy tay trên ghế", None, 1, "compound", "h_push", 1),
            (23, "Kéo xe trượt", "Sled pull", 2, "cardio", "other", 1),
            (24, "Đẩy xe trượt", "Sled push", 2, "cardio", "other", 1),
            (25, "Hip thrust", None, 8, "compound", "hinge", 2),
            (26, "Kickback mông", None, 8, "isolation", "hinge", 2),
            (27, "Pull-through", None, 8, "isolation", "hinge", 2),
            (28, "Pushdown", None, 6, "isolation", "h_push", 2),
            (29, "Đi bộ", None, 3, "cardio", "other", 1),
            (30, "Xe đạp", None, 3, "cardio", "other", 1),
            (31, "Nhảy dang chân", "Jumping Jack", 3, "cardio", "other", 1),
            (32, "Đấm bóng tưởng tượng", "Shadow Boxing", 3, "cardio", "other", 1),
            (33, "Nhảy dây", "Jump Rope", 3, "cardio", "other", 1),
            (34, "Chạy ngắt quãng", "Running Intervals", 3, "cardio", "other", 1),
            (35, "Đi bộ đường dài", "Hiking", 3, "cardio", "other", 1),
            (36, "Chạy bền", "Trail Run", 3, "cardio", "other", 1),
        ]
        for eid, name, name_en, mg, role, pattern, diff in [
            (*row[:2], None, *row[2:]) for row in exercises
        ] + extra:
            conn.execute(
                text(
                    "INSERT INTO exercises "
                    "(id,name_vi,name_en,muscle_group_id,exercise_type,movement_role,movement_pattern,"
                    "difficulty,is_active,created_at,updated_at) "
                    "VALUES (:id,:n,:ne,:mg,'main',:r,:p,:d,1,:c,:u)"
                ),
                {
                    "id": eid,
                    "n": name,
                    "ne": name_en,
                    "mg": mg,
                    "r": role,
                    "p": pattern,
                    "d": diff,
                    "c": now,
                    "u": now,
                },
            )
        conn.execute(
            text(
                """
                CREATE TABLE ai_generations (
                    id INTEGER PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    generation_type TEXT NOT NULL,
                    input_params TEXT NOT NULL DEFAULT '{}',
                    output_data TEXT NOT NULL DEFAULT '{}',
                    tokens_used INTEGER,
                    cost_usd REAL,
                    is_paid INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT,
                    prompt_version TEXT,
                    system_prompt_hash TEXT
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE product_redeem_batches (
                    id INTEGER PRIMARY KEY,
                    qty INTEGER,
                    created_by TEXT,
                    created_at TEXT
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE product_redeem_codes (
                    id INTEGER PRIMARY KEY,
                    batch_id INTEGER NOT NULL,
                    code TEXT NOT NULL UNIQUE,
                    status TEXT NOT NULL DEFAULT 'unused',
                    reservation_token TEXT,
                    reserved_at TEXT,
                    redeemed_at TEXT,
                    plan_id INTEGER,
                    redeemed_user_id TEXT,
                    order_id INTEGER,
                    order_item_id INTEGER
                )
                """
            )
        )

        conn.execute(
            text("INSERT INTO users (id, email, role) VALUES (:id,'a@b.c','user')"),
            {"id": TEST_USER_ID},
        )

    ensure_session_block_templates(engine)
    ensure_exercise_prescription_defaults(engine)
    ensure_exercise_venue_and_difficulty_v2(engine)
    ensure_plan_day_nutrition(engine)
    return engine


def test_generate_workout_openai_pick(tmp_path, monkeypatch):
    engine = _setup_engine(tmp_path)
    Session = sessionmaker(bind=engine)
    db = Session()
    monkeypatch.setattr(
        "app.services.workout_generation.service.generate_coach_advice",
        lambda _payload, _summary, **kwargs: {
            "advice_vi": ["Test advice"],
            "summary_vi": "Test summary",
            "week_notes_vi": "",
            "used_openai": False,
        },
    )

    try:
        result = generate_workout(
            db,
            TEST_USER_ID,
            {
                "challenge_100_days": True,
                "goal": "lose_weight",
                "gender": "male",
                "age": 25,
                "height_cm": 170,
                "weight_kg": 70,
                "activity": "moderate",
                "sessions_per_week": 3,
                "session_minutes": 45,
                "experience_level": 1,
                "no_equipment": False,
                "ai_suggest_equipment": False,
                "equipment_list": ["dumbbell"],
                "duration_weeks": 2,
            },
        )
        assert result["plan_id"]
        assert result["share_token"]
        plan = result["plan"]
        assert plan["source"] == "ai"
        assert len(plan["days"]) >= 3
        desc = plan.get("description_vi") or ""
        assert "Master `" not in desc
        assert "set/tuần" not in desc
        assert "LISS" not in desc
        insights = plan.get("insights") or {}
        assert insights.get("used_openai_pick") is True
        assert insights.get("generator") == "master_v1_14_challenge100"
        inputs = insights.get("inputs") or {}
        assert inputs.get("location_vi")
        assert "buổi/tuần" in (inputs.get("recap_vi") or desc)
        main_compounds = []
        for day in plan["days"]:
            for ex in day.get("exercises") or []:
                main_compounds.append(ex)
        assert any(ex.get("sets") == 3 for ex in main_compounds)
    finally:
        db.close()


def test_generate_familiarization_retired_alias_maps_to_first_push_pull(
    tmp_path, monkeypatch
):
    engine = _setup_engine(tmp_path)
    ensure_familiarization_exercises(engine)
    with engine.begin() as conn:
        now = datetime.now(timezone.utc).isoformat()
        for eid, name_vi, name_en, mg, role, pattern, diff in (
            (101, "Treo người thả lỏng", "Dead Hang", 2, "compound", "v_pull", 1),
            (103, "Chống đẩy tường", "Wall Push-up", 1, "compound", "h_push", 1),
            (104, "Chống đẩy quỳ gối", "Knee Push-up", 1, "compound", "h_push", 2),
            (106, "Superman", "Superman", 2, "compound", "v_pull", 1),
            (107, "Chèo ba lô hai tay", "Bent-Over Backpack Row", 2, "compound", "h_pull", 1),
            (109, "Squat thể trọng", "Bodyweight Squat", 4, "compound", "squat", 1),
            (110, "Plank", "Plank", 3, "compound", "core", 1),
            (111, "Đi bộ tại chỗ", "March in Place", 4, "compound", "other", 1),
            (112, "Kéo người dưới bàn", "Table Inverted Row", 2, "compound", "h_pull", 1),
            (114, "Chống đẩy kê tay ghế", "Incline Push-up", 1, "compound", "h_push", 1),
            (115, "Nhảy dang chân", "Jumping Jack", 4, "compound", "other", 1),
            (116, "Cầu mông", "Glute Bridge", 4, "compound", "hinge", 1),
        ):
            conn.execute(
                text(
                    "INSERT INTO exercises "
                    "(id,name_vi,name_en,muscle_group_id,exercise_type,movement_role,"
                    "movement_pattern,difficulty,venue,is_active,created_at,updated_at) "
                    "VALUES (:id,:n,:ne,:mg,'main',:r,:p,:d,'both',1,:c,:u)"
                ),
                {
                    "id": eid,
                    "n": name_vi,
                    "ne": name_en,
                    "mg": mg,
                    "r": role,
                    "p": pattern,
                    "d": diff,
                    "c": now,
                    "u": now,
                },
            )
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        result = generate_workout(
            db,
            TEST_USER_ID,
            {
                "generation_mode": "familiarization",
                "familiarization_path": "basic_foundation",
                "gender": "male",
                "age": 25,
                "height_cm": 170,
                "weight_kg": 70,
                "activity": "light",
                "goal": "maintain",
                "sessions_per_week": 3,
                "session_minutes": 45,
                "experience_level": 1,
                "location": "home",
                "equipment_list": ["pull-up-bar"],
                "food_ids": [],
                "fitness_baseline": {
                    "pushup_variant": "standard",
                    "pushups_max": 0,
                    "pull_test_variant": "strict",
                    "pullups_max": 0,
                    "squats_max": 10,
                    "plank_seconds": 20,
                    "run_10min_meters": 900,
                },
            },
            persist=False,
        )
        days = result["days"]
        insights = result["insights"]
        assert len(days) == 28
        assert insights["duration_days"] == 28
        assert sum(bool(day.get("exercises")) for day in days) == 12
        assert insights["generator"] == "familiarization_rules_v1"
        assert insights["used_openai_pick"] is False
        assert insights["familiarization_path"] == "first_push_pull"
        assert "nhập môn" in insights["overview"]["mission_vi"].lower()
        assert "Chống đẩy sàn 3–8" in insights["overview"]["outcome_vi"]
        assert "nền tảng" in insights["overview"]["outcome_vi"]
        assert all(not day.get("meals") for day in days)
        last_train = next(day for day in reversed(days) if day.get("exercises"))
        last_blob = " ".join(
            (ex.get("name_en") or "") + " " + (ex.get("name_vi") or "") + " " + (ex.get("reps") or "")
            for ex in (last_train.get("exercises") or [])
        ).lower()
        assert "8–10/tay" in last_blob or "backpack" in last_blob or "chèo" in last_blob
    finally:
        db.close()


def test_generate_first_push_pull_is_upper_focused_with_schedule_titles(
    tmp_path, monkeypatch
):
    engine = _setup_engine(tmp_path)
    ensure_familiarization_exercises(engine)
    with engine.begin() as conn:
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            text(
                "INSERT OR IGNORE INTO equipment "
                "(id, slug, name_vi, name_en, category, is_active, sort_order) "
                "VALUES (1, 'pull-up-bar', 'Xà đơn', 'Pull-up bar', 'home', 1, 40)"
            )
        )
        for eid, name_vi, name_en, mg, role, pattern, diff in (
            (101, "Treo người thả lỏng", "Dead Hang", 2, "compound", "v_pull", 1),
            (102, "Kéo xà", "Pull-up", 2, "compound", "v_pull", 2),
            (103, "Chống đẩy tường", "Wall Push-up", 1, "compound", "h_push", 1),
            (104, "Chống đẩy quỳ gối", "Knee Push-up", 1, "compound", "h_push", 2),
            (105, "Chống đẩy", "Push-up", 1, "compound", "h_push", 2),
            (106, "Superman", "Superman", 2, "compound", "v_pull", 1),
            (107, "Chèo ba lô hai tay", "Bent-Over Backpack Row", 2, "compound", "h_pull", 1),
            (108, "Chèo ba lô một tay", "One-Arm Backpack Row", 2, "compound", "h_pull", 1),
            (109, "Squat thể trọng", "Bodyweight Squat", 4, "compound", "squat", 1),
            (110, "Plank", "Plank", 3, "compound", "core", 1),
            (111, "Đi bộ tại chỗ", "March in Place", 4, "compound", "other", 1),
            (112, "Kéo người dưới bàn", "Table Inverted Row", 2, "compound", "h_pull", 1),
            (113, "Kéo xà 1/3", "1/3 Pull-up", 2, "compound", "v_pull", 1),
            (114, "Chống đẩy kê tay ghế", "Incline Push-up", 1, "compound", "h_push", 1),
            (115, "Nhảy dang chân", "Jumping Jack", 4, "compound", "other", 1),
            (116, "Cầu mông", "Glute Bridge", 4, "compound", "hinge", 1),
        ):
            conn.execute(
                text(
                    "INSERT INTO exercises "
                    "(id,name_vi,name_en,muscle_group_id,exercise_type,movement_role,"
                    "movement_pattern,difficulty,venue,is_active,created_at,updated_at) "
                    "VALUES (:id,:n,:ne,:mg,'main',:r,:p,:d,'both',1,:c,:u)"
                ),
                {
                    "id": eid,
                    "n": name_vi,
                    "ne": name_en,
                    "mg": mg,
                    "r": role,
                    "p": pattern,
                    "d": diff,
                    "c": now,
                    "u": now,
                },
            )
        conn.execute(
            text(
                "INSERT INTO exercise_equipment (exercise_id, equipment_id) "
                "VALUES (101, 1), (102, 1), (113, 1)"
            )
        )
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        female = generate_workout(
            db,
            TEST_USER_ID,
            {
                "generation_mode": "familiarization",
                "familiarization_path": "first_push_pull",
                "gender": "female",
                "age": 25,
                "height_cm": 160,
                "weight_kg": 55,
                "activity": "light",
                "goal": "maintain",
                "sessions_per_week": 3,
                "session_minutes": 45,
                "experience_level": 1,
                "location": "home",
                "equipment_list": ["pull-up-bar"],
                "food_ids": [],
                "fitness_baseline": {
                    "pushup_variant": "knee",
                    "pushups_max": 0,
                    "pull_test_variant": "hang",
                    "pull_hold_seconds": 0,
                    "pullups_max": 0,
                    "squats_max": 0,
                    "plank_seconds": 0,
                    "run_10min_meters": 0,
                },
            },
        )
        plan = female["plan"]
        plan_days = plan["days"]
        insights = plan["insights"]
        assert insights["generator"] == "familiarization_rules_v1"
        assert insights["duration_days"] == 28
        assert insights["overview"]["mission_vi"]
        assert insights["overview"]["outcome_vi"]
        assert "nhập môn" in insights["overview"]["mission_vi"].lower()
        assert "Chống đẩy quỳ 4–10" in insights["overview"]["outcome_vi"]
        assert "nền tảng" in insights["overview"]["outcome_vi"]
        assert len(plan_days) == 28
        assert sum(bool(day.get("exercises")) for day in plan_days) == 12
        assert sum(not day.get("exercises") for day in plan_days) == 16
        assert plan_days[-1]["day_number"] == 28
        assert plan_days[-1]["split_role"] == "recovery"
        assert (plan["end_date"] - plan["start_date"]).days == 27
        bar_exercise_ids = {
            int(row[0])
            for row in db.execute(
                text(
                    "SELECT ee.exercise_id FROM exercise_equipment ee "
                    "JOIN equipment e ON e.id = ee.equipment_id "
                    "WHERE e.slug = 'pull-up-bar'"
                )
            )
        }
        def _day_blob(days):
            return " ".join(
                ((ex.get("name_vi") or "") + " " + (ex.get("name_en") or "") + " " + (ex.get("reps") or ""))
                for day in days
                for ex in (day.get("exercises") or [])
            ).lower()

        # Tuần 1 (ngày 1–7): chưa xà treo / inverted row
        pre_week2 = plan_days[:7]
        pre_week2_ids = {
            int(ex["exercise_id"])
            for day in pre_week2
            for ex in (day.get("exercises") or [])
        }
        assert pre_week2_ids.isdisjoint(bar_exercise_ids)
        pre_week2_names = _day_blob(pre_week2)
        assert "inverted" not in pre_week2_names
        assert "dead hang" not in pre_week2_names
        assert "treo người" not in pre_week2_names
        assert "pull-up" not in pre_week2_names
        assert "cằm" not in pre_week2_names
        assert "negative" not in pre_week2_names
        assert (
            "backpack" in pre_week2_names
            or "ba lô" in pre_week2_names
            or "balo" in pre_week2_names
            or "wall" in pre_week2_names
            or "tường" in pre_week2_names
            or "ghế" in pre_week2_names
        )
        backpack_ids = {
            int(ex["exercise_id"])
            for day in plan_days[:14]
            for ex in (day.get("exercises") or [])
            if "backpack"
            in ((ex.get("name_en") or "") + " " + (ex.get("name_vi") or "")).lower()
            or "ba lô" in ((ex.get("name_vi") or "")).lower()
            or "balo" in ((ex.get("name_vi") or "")).lower()
        }
        assert backpack_ids & {107, 108} or any(
            "row" in ((ex.get("name_en") or "") + " " + (ex.get("name_vi") or "")).lower()
            and (
                "backpack" in ((ex.get("name_en") or "")).lower()
                or "ba lô" in ((ex.get("name_vi") or "")).lower()
                or "balo" in ((ex.get("name_vi") or "")).lower()
            )
            for day in plan_days[:14]
            for ex in (day.get("exercises") or [])
        )

        week2_names = _day_blob(plan_days[7:14])
        assert "hang" not in week2_names
        assert "treo" not in week2_names
        assert "backpack" in week2_names or "ba lô" in week2_names or "balo" in week2_names

        day_17_names = _day_blob([plan_days[16]])
        assert "inverted" not in day_17_names
        assert "one-arm" in day_17_names or "một tay" in day_17_names or "row" in day_17_names
        assert "cằm" not in day_17_names
        assert "negative" not in day_17_names

        assert "Buổi 1" in (plan_days[0].get("title_vi") or "")
        assert "Toàn thân" in (plan_days[0].get("title_vi") or "")
        # Zero baseline: tuần 1–3 tường/ghế; quỳ xuất hiện từ tuần 4 (probe) hoặc 5
        week1_push = _day_blob(plan_days[:7])
        assert (
            "tường" in week1_push
            or "wall" in week1_push
            or "ghế" in week1_push
            or "incline" in week1_push
        )
        knee_names = {
            (ex.get("name_vi") or "") + " " + (ex.get("name_en") or "")
            for day in plan_days[21:]  # từ tuần 4
            for ex in day.get("exercises") or []
        }
        assert any(
            "quỳ gối" in n.lower()
            or "chống gối" in n.lower()
            or "knee" in n.lower()
            for n in knee_names
        )

        whole = _day_blob(plan_days)
        assert "giữ cằm" not in whole
        assert "chin-over-bar" not in whole
        assert "negative" not in whole
        assert "dead hang" not in whole
        assert "inverted" not in whole

        last_train = next(day for day in reversed(plan_days) if day.get("exercises"))
        assert last_train["day_number"] == 26

        male = generate_workout(
            db,
            TEST_USER_ID,
            {
                "generation_mode": "familiarization",
                "familiarization_path": "first_push_pull",
                "gender": "male",
                "sessions_per_week": 5,
                "session_minutes": 90,
                "experience_level": 1,
                "fitness_baseline": {},
            },
            persist=False,
        )
        assert len(male["days"]) == 28
        assert male["sessions_actual"] == 3
        male_blob = " ".join(
            str(ex.get("name_en") or "")
            for day in male["days"]
            for ex in (day.get("exercises") or [])
        ).lower()
        assert "pull-up" not in male_blob
        assert "inverted" not in male_blob
        assert male["insights"]["overview"]["mission_vi"]
        assert male["insights"]["overview"]["outcome_vi"]

        alias = generate_workout(
            db,
            TEST_USER_ID,
            {
                "generation_mode": "familiarization",
                "familiarization_path": "basic_foundation",
                "gender": "female",
                "age": 25,
                "height_cm": 160,
                "weight_kg": 55,
                "activity": "light",
                "goal": "maintain",
                "sessions_per_week": 3,
                "session_minutes": 45,
                "experience_level": 1,
                "location": "home",
                "equipment_list": ["pull-up-bar"],
                "food_ids": [],
                "fitness_baseline": {
                    "pushup_variant": "knee",
                    "pushups_max": 8,
                    "pull_test_variant": "inverted_row",
                    "inverted_rows_max": 6,
                    "squats_max": 20,
                    "plank_seconds": 40,
                    "run_10min_meters": 1100,
                },
            },
            persist=False,
        )
        assert alias["insights"]["familiarization_path"] == "first_push_pull"
        assert "nhập môn" in alias["insights"]["overview"]["mission_vi"].lower()

    finally:
        db.close()


def test_generate_workout_persist_false_fills_empty_picks(tmp_path, monkeypatch):
    engine = _setup_engine(tmp_path)
    Session = sessionmaker(bind=engine)
    db = Session()
    monkeypatch.setattr(
        "app.services.workout_generation.service.generate_coach_advice",
        lambda *_a, **_k: {
            "advice_vi": [],
            "summary_vi": "",
            "week_notes_vi": "",
            "used_openai": False,
        },
    )

    try:
        result = generate_workout(
            db,
            None,
            {
                "challenge_100_days": True,
                "goal": "maintain",
                "gender": "male",
                "age": 25,
                "height_cm": 170,
                "weight_kg": 70,
                "activity": "moderate",
                "sessions_per_week": 3,
                "session_minutes": 45,
                "experience_level": 1,
                "location": "home",
                "no_equipment": False,
                "ai_suggest_equipment": False,
                "equipment_list": ["dumbbell"],
                "duration_weeks": 2,
            },
            persist=False,
        )
        assert result["plan_id"] is None
        days = result.get("days") or []
        assert len(days) >= 3
        roles = [d.get("split_role") for d in days]
        for day in days:
            exercises = day.get("exercises") or []
            wu = sum(1 for ex in exercises if ex.get("section") == "warmup")
            assert wu == 2
            mains = [ex for ex in exercises if (ex.get("section") or "main") == "main"]
            assert mains
            for ex in exercises:
                name = ex.get("name_vi")
                assert name and str(name).strip().lower() not in {"none", ""}
        if "pull" in roles:
            pull = next(d for d in days if d.get("split_role") == "pull")
            names = " ".join(
                str(ex.get("name_vi") or "")
                for ex in pull.get("exercises") or []
                if (ex.get("section") or "main") == "main"
            ).lower()
            assert "curl" in names
        if "push" in roles or "upper" in roles:
            pass
    finally:
        db.close()


def _stub_coach(monkeypatch):
    monkeypatch.setattr(
        "app.services.workout_generation.service.generate_coach_advice",
        lambda *_a, **_k: {
            "advice_vi": [],
            "summary_vi": "",
            "week_notes_vi": "",
            "used_openai": False,
        },
    )


def _name(item: dict) -> str:
    return str(item.get("name_vi") or "").lower()


def _muscle(item: dict) -> str:
    return str(item.get("muscle") or item.get("muscle_slug") or "").lower()


def _pattern(item: dict) -> str:
    return str(item.get("movement_pattern") or "").lower()


def _bad_openai_picks(week_payload, profile=None, *, empty_resistance: bool = False):
    """Simulate the audit bugs: no biceps, no press, hinge-only legs, push-up spam."""
    days = []
    for d in week_payload:
        role = str(d.get("split_role") or "").lower()
        blocks_out = []
        for b in d.get("blocks") or []:
            if not b.get("pick"):
                continue
            key = str(b.get("block_key") or "")
            short = [x for x in (b.get("shortlist") or []) if isinstance(x, dict) and x.get("id")]
            n = int(b.get("count_max") or 0)
            if empty_resistance and key == "resistance":
                blocks_out.append({"block_key": key, "exercise_ids": []})
                continue

            def take(ranked: list) -> list[int]:
                seen: set[int] = set()
                out: list[int] = []
                for x in ranked:
                    eid = int(x["id"])
                    if eid in seen:
                        continue
                    seen.add(eid)
                    out.append(eid)
                    if len(out) >= n:
                        break
                return out

            ids: list[int]
            if key in {"cardio", "conditioning"}:
                ids = take(short)
            elif role == "pull" and key in {"compound", "accessory", "resistance"}:
                skip_bi = [
                    x
                    for x in short
                    if "curl" not in _name(x) and _muscle(x) != "biceps"
                ]
                skip_bi.sort(
                    key=lambda x: (
                        0 if "face" in _name(x) else 1,
                        0 if _muscle(x) in {"back", "shoulders"} else 2,
                    )
                )
                ids = take(skip_bi or short)
            elif role == "upper" and key in {"compound", "accessory", "resistance"}:
                pulls = [x for x in short if _pattern(x) in {"h_pull", "v_pull"}]
                ids = take(pulls + short)
            elif role in {"legs", "lower"} and key in {"compound", "accessory", "resistance"}:
                hinges = [x for x in short if _pattern(x) == "hinge"]
                ids = take(hinges + short)
            elif key == "resistance":
                pu = [x for x in short if is_pushup_name(_name(x))]
                sled = [
                    x
                    for x in short
                    if "sled" in _name(x) or "trượt" in _name(x) or "truot" in _name(x)
                ]
                ids = take(pu + sled + short)
            else:
                ids = take(short)
            blocks_out.append({"block_key": key, "exercise_ids": ids})
        days.append({"day_index": d["day_index"], "blocks": blocks_out})
    return days


def _assert_preview_sane(days: list) -> None:
    assert days
    for day in days:
        exercises = day.get("exercises") or []
        wu = sum(1 for ex in exercises if ex.get("section") == "warmup")
        assert wu >= 1, day.get("split_role")
        mains = [ex for ex in exercises if (ex.get("section") or "main") == "main"]
        assert mains, day.get("split_role")
        for ex in exercises:
            name = ex.get("name_vi")
            assert name and str(name).strip().lower() not in {"none", ""}


def _main_names(day: dict) -> str:
    return " ".join(
        str(ex.get("name_vi") or "")
        for ex in day.get("exercises") or []
        if (ex.get("section") or "main") == "main"
    ).lower()


def test_stub_picker_gym_l1_3d_45_ppl(tmp_path, monkeypatch):
    engine = _setup_engine(tmp_path)
    db = sessionmaker(bind=engine)()
    _stub_coach(monkeypatch)
    try:
        result = generate_workout(
            db,
            None,
            {
                "goal": "maintain",
                "gender": "male",
                "age": 25,
                "height_cm": 170,
                "weight_kg": 70,
                "activity": "moderate",
                "sessions_per_week": 3,
                "session_minutes": 45,
                "experience_level": 1,
                "location": "home",
                "no_equipment": False,
                "ai_suggest_equipment": False,
                "equipment_list": ["dumbbell"],
                "duration_weeks": 4,
                "challenge_100_days": True,
            },
            persist=False,
        )
        days = result.get("days") or []
        _assert_preview_sane(days)
        roles = [d.get("split_role") for d in days]
        assert "pull" in roles
        pull = next(d for d in days if d.get("split_role") == "pull")
        assert "curl" in _main_names(pull)
    finally:
        db.close()


def test_stub_picker_gym_l1_4d_45_ul(tmp_path, monkeypatch):
    engine = _setup_engine(tmp_path)
    db = sessionmaker(bind=engine)()
    _stub_coach(monkeypatch)
    try:
        result = generate_workout(
            db,
            None,
            {
                "goal": "maintain",
                "gender": "male",
                "age": 25,
                "height_cm": 170,
                "weight_kg": 70,
                "activity": "moderate",
                "sessions_per_week": 4,
                "session_minutes": 45,
                "experience_level": 1,
                "location": "home",
                "no_equipment": False,
                "ai_suggest_equipment": False,
                "equipment_list": ["dumbbell"],
                "duration_weeks": 4,
                "challenge_100_days": True,
            },
            persist=False,
        )
        days = result.get("days") or []
        _assert_preview_sane(days)
        uppers = [d for d in days if d.get("split_role") == "upper"]
        assert uppers
        press_hint = ("bench", "ohp", "fly", "chống đẩy", "chong day", "press")
        for upper in uppers:
            blob = _main_names(upper)
            assert any(h in blob for h in press_hint), blob
            assert "pushdown" not in blob or any(h in blob for h in press_hint)
    finally:
        db.close()


def test_stub_picker_home_body_90_upper(tmp_path, monkeypatch):
    engine = _setup_engine(tmp_path)
    db = sessionmaker(bind=engine)()
    _stub_coach(monkeypatch)
    try:
        result = generate_workout(
            db,
            None,
            {
                "goal": "maintain",
                "gender": "male",
                "age": 25,
                "height_cm": 170,
                "weight_kg": 70,
                "activity": "moderate",
                "sessions_per_week": 4,
                "session_minutes": 90,
                "experience_level": 1,
                "location": "home",
                "no_equipment": False,
                "ai_suggest_equipment": False,
                "equipment_list": ["dumbbell"],
                "duration_weeks": 4,
                "challenge_100_days": True,
            },
            persist=False,
        )
        days = result.get("days") or []
        _assert_preview_sane(days)
        for day in days:
            blob = " ".join(
                str(ex.get("name_vi") or "") for ex in day.get("exercises") or []
            ).lower()
            assert "sled" not in blob
            assert "xe trượt" not in blob
            assert "xe truot" not in blob
            role = str(day.get("split_role") or "")
            if role in {"core", "cardio"}:
                continue
            mains = [
                ex
                for ex in day.get("exercises") or []
                if (ex.get("section") or "main") == "main"
            ]
            pu = sum(1 for ex in mains if is_pushup_name(ex.get("name_vi")))
            assert pu <= 2
            cardioish = [
                ex
                for ex in day.get("exercises") or []
                if (ex.get("section") or "") in {"cardio", "conditioning"}
            ]
            assert len(cardioish) <= 2
    finally:
        db.close()


def test_stub_picker_home_body_l2_6d_45_fallback(tmp_path, monkeypatch):
    engine = _setup_engine(tmp_path)
    db = sessionmaker(bind=engine)()
    _stub_coach(monkeypatch)
    try:
        result = generate_workout(
            db,
            None,
            {
                "goal": "maintain",
                "gender": "female",
                "age": 28,
                "height_cm": 160,
                "weight_kg": 55,
                "activity": "moderate",
                "sessions_per_week": 6,
                "session_minutes": 45,
                "experience_level": 2,
                "location": "home",
                "no_equipment": False,
                "ai_suggest_equipment": False,
                "equipment_list": ["dumbbell"],
                "duration_weeks": 4,
                "challenge_100_days": True,
            },
            persist=False,
        )
        days = result.get("days") or []
        _assert_preview_sane(days)
        assert len(days) >= 5
        for day in days:
            blob = " ".join(
                str(ex.get("name_vi") or "") for ex in day.get("exercises") or []
            ).lower()
            assert "sled" not in blob
            assert "none" not in blob
            role = str(day.get("split_role") or "")
            if role in {"core", "cardio"}:
                continue
            mains = [
                ex
                for ex in day.get("exercises") or []
                if (ex.get("section") or "main") == "main"
            ]
            assert len(mains) >= 2
    finally:
        db.close()


def test_generate_workout_does_not_call_meal_openai():
    import inspect

    src = inspect.getsource(generate_workout)
    assert "pick_challenge_meals_with_openai" not in src


def test_generate_rejects_level_4(tmp_path):
    engine = _setup_engine(tmp_path)
    Session = sessionmaker(bind=engine)
    db = Session()
    from app.core.exceptions import BadRequestError
    import pytest

    try:
        with pytest.raises(BadRequestError):
            generate_workout(
                db,
                TEST_USER_ID,
                {
                    "goal": "maintain",
                    "gender": "male",
                    "age": 25,
                    "height_cm": 170,
                    "weight_kg": 70,
                    "activity": "light",
                    "sessions_per_week": 3,
                    "session_minutes": 45,
                    "experience_level": 4,
                    "no_equipment": False,
                    "equipment_list": ["dumbbell"],
                    "duration_weeks": 2,
                },
            )
    finally:
        db.close()

def test_ai_usage_public():
    app = create_app()
    client = TestClient(app)
    res = client.get("/api/v1/ai/usage")
    assert res.status_code == 200
    assert res.json().get("unlimited") is True


def _fake_pick(week_payload, profile=None):
    days = []
    for d in week_payload:
        blocks_out = []
        for b in d.get("blocks") or []:
            if not b.get("pick"):
                continue
            n = int(b.get("count_max") or 0)
            ids = [int(x["id"]) for x in (b.get("shortlist") or [])[:n]]
            blocks_out.append({"block_key": b["block_key"], "exercise_ids": ids})
        days.append({"day_index": d["day_index"], "blocks": blocks_out})
    return days


_PHASE_PICK_CALLS: list[dict] = []


def _fake_phase_pick(
    week_payload,
    profile=None,
    phase=None,
    avoid_ids=None,
    avoid_stems=None,
):
    _PHASE_PICK_CALLS.append(
        {
            "avoid_ids": list(avoid_ids or []),
            "month": (phase or {}).get("month"),
        }
    )
    days = _fake_pick(week_payload, profile=profile)
    week_b = []
    for d in week_payload:
        blocks_out = []
        for b in d.get("blocks") or []:
            if not b.get("pick"):
                continue
            key = str(b.get("block_key") or "")
            n = int(b.get("count_max") or 0)
            sl = [int(x["id"]) for x in (b.get("shortlist") or [])]
            ids = sl[:n]
            if key in {"accessory", "resistance", "conditioning", "core", "cardio"} and len(sl) > n:
                alt = sl[-n:]
                if alt != ids:
                    ids = alt
            blocks_out.append({"block_key": key, "exercise_ids": ids})
        week_b.append({"day_index": d["day_index"], "blocks": blocks_out})
    month = int((phase or {}).get("month") or 1)
    return {
        "days": days,
        "week_b": week_b,
        "rationale_vi": f"Pha {month}: lịch tập theo mục tiêu tháng này.",
    }


def _must_not_coach(*_a, **_k):
    raise AssertionError("challenge must not call generate_coach_advice")


def _fake_meals_with_blocks(db, payload, blocks, template_days, **kwargs):
    from app.services.workout_generation.meal_engine import MealPlanResult

    insights = []
    for block in blocks:
        sessions = []
        for d in template_days:
            slot = next(
                (s for s in block.schedule.training if s.split_role == d.split_role),
                block.schedule.training[0] if block.schedule.training else None,
            )
            t = slot.targets if slot else block.targets
            sessions.append(
                {
                    "split_role": d.split_role,
                    "target_calories": t.target_calories,
                    "target_protein_g": t.protein_g,
                    "target_carbs_g": t.carbs_g,
                    "target_fat_g": t.fat_g,
                    "meals": [],
                    "meal_notes": {},
                }
            )
        insights.append(
            {
                "block_index": block.block_index,
                "weeks": list(range(block.week_from, block.week_to + 1)),
                "projected_weight_kg": block.projected_weight_kg,
                "avg_target_calories": block.schedule.avg_target,
                "tdee": block.targets.tdee,
                "protein_g": block.targets.protein_g,
                "carbs_g": block.targets.carbs_g,
                "fat_g": block.targets.fat_g,
                "sessions": sessions,
            }
        )
    return MealPlanResult(nutrition_blocks=insights, warning_vi=None)


def test_generate_workout_challenge_100_days(tmp_path, monkeypatch):
    engine = _setup_engine(tmp_path)
    Session = sessionmaker(bind=engine)
    db = Session()
    monkeypatch.setattr(
        "app.services.workout_generation.service.generate_coach_advice",
        _must_not_coach,
    )
    monkeypatch.setattr(
        "app.services.workout_generation.service.generate_meals_with_blocks",
        _fake_meals_with_blocks,
    )
    try:
        result = generate_workout(
            db,
            TEST_USER_ID,
            {
                "goal": "lose_weight",
                "gender": "male",
                "age": 25,
                "height_cm": 170,
                "weight_kg": 70,
                "activity": "moderate",
                "sessions_per_week": 3,
                "session_minutes": 45,
                "experience_level": 1,
                "location": "home",
                "no_equipment": False,
                "ai_suggest_equipment": False,
                "equipment_list": ["dumbbell"],
                "ai_suggest_foods": True,
                "duration_weeks": 4,
                "challenge_100_days": True,
                "kg_per_week": 0.5,
            },
        )
        plan = result["plan"]
        insights = plan.get("insights") or {}
        assert insights.get("challenge_100_days") is True
        assert insights.get("generator") == "master_v1_14_challenge100"
        assert insights.get("nutrition_checkin_interval_days") == 28
        cur = insights.get("curriculum") or {}
        assert cur.get("deload_weeks") == [4, 8, 14]
        assert cur.get("duration_weeks") == 14
        assert len(cur.get("mesocycles") or []) == 3
        r1 = cur["mesocycles"][0].get("rationale_vi") or ""
        assert "pool" not in r1.lower()
        assert "không bịa" not in r1
        assert "buổi" in r1
        assert "\n" not in r1
        n_refs = len(cur["mesocycles"][0].get("knowledge_refs") or [])
        assert 3 <= n_refs <= 4
        assert cur["mesocycles"][0].get("label_vi") == "Nền tảng"
        wt = insights.get("week_templates") or []
        assert len(wt) == 3
        assert isinstance(wt[0], dict) and "a" in wt[0] and "b" in wt[0]
        blocks = insights.get("nutrition_blocks") or []
        assert len(blocks) == 3
        assert blocks[0]["weeks"] == [1, 2, 3, 4]
        assert blocks[2]["weeks"] == [9, 10, 11, 12, 13, 14]
        # 14 weeks × 3 sessions
        assert len(plan["days"]) == 42
        titles = [d.get("title_vi") or "" for d in plan["days"]]
        deload_titles = [t for t in titles if "Deload" in t]
        assert len(deload_titles) == 9  # 3 deload weeks × 3 sessions
        assert any("Pha 3" in t and "Tuần 14" in t for t in titles)
        assert plan.get("challenge_100_days") is True
    finally:
        db.close()


def test_generate_workout_rejects_regular_four_week(tmp_path):
    from app.core.exceptions import BadRequestError

    engine = _setup_engine(tmp_path)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        with pytest.raises(BadRequestError) as ei:
            generate_workout(
                db,
                TEST_USER_ID,
                {
                    "goal": "lose_weight",
                    "gender": "male",
                    "age": 25,
                    "height_cm": 170,
                    "weight_kg": 70,
                    "activity": "moderate",
                    "sessions_per_week": 3,
                    "session_minutes": 45,
                    "experience_level": 1,
                    "no_equipment": False,
                    "equipment_list": ["dumbbell"],
                    "duration_weeks": 4,
                    "challenge_100_days": False,
                },
            )
        assert "Nhập môn" in str(ei.value.message) or "100 ngày" in str(ei.value.message)
    finally:
        db.close()


def test_generate_workout_rejects_empty_home_equipment(tmp_path):
    from app.core.exceptions import BadRequestError
    engine = _setup_engine(tmp_path)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        with pytest.raises(BadRequestError):
            generate_workout(
                db,
                TEST_USER_ID,
                {
                    "goal": "maintain",
                    "gender": "male",
                    "age": 25,
                    "height_cm": 170,
                    "weight_kg": 70,
                    "activity": "moderate",
                    "sessions_per_week": 3,
                    "session_minutes": 45,
                    "experience_level": 1,
                    "location": "home",
                    "no_equipment": False,
                    "equipment_list": [],
                },
            )
    finally:
        db.close()

