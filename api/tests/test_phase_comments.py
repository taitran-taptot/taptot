from app.services.workout_generation.phase_comments import challenge_phase_copy
from app.services.workout_generation.phase_knowledge import (
    refs_for_challenge_phases_ui,
    refs_for_phase,
    refs_for_phase_ui,
)


def test_ui_reading_three_to_four_no_overlap_across_phases():
    sedentary = refs_for_challenge_phases_ui(1, goal="lose_weight", activity="sedentary")
    labor = refs_for_challenge_phases_ui(1, goal="gain_weight", activity="very_active")
    assert [r["slug"] for r in sedentary[0][:3]] == [
        "cach-doc-lich-tap-quy-uoc-buoi-tap",
        "xac-dinh-muc-tieu-tap-luyen",
        "khoi-dong-warm-up-van-dong-khop-mobility",
    ]
    assert [r["slug"] for r in labor[0][:3]] == [
        "cach-doc-lich-tap-quy-uoc-buoi-tap",
        "xac-dinh-muc-tieu-tap-luyen",
        "dau-moi-co-doms-va-chan-thuong-cach-phan-biet-va-xu-ly",
    ]
    for rows in (sedentary, labor):
        slugs = [r["slug"] for month in rows for r in month]
        assert len(slugs) == len(set(slugs))
        for month in rows:
            assert 3 <= len(month) <= 4
    l3 = refs_for_challenge_phases_ui(3, goal="lose_weight", activity="moderate")
    assert "refeed-va-diet-break" in [r["slug"] for r in l3[2]]
    assert refs_for_phase_ui(1, 0) == []


def test_engine_refs_for_phase_still_full_matrix():
    assert len(refs_for_phase(1, 1)) == 8


def test_challenge_phase_copy_one_paragraph():
    wizard = {
        "goal": "lose_weight",
        "gender_vi": "Nam",
        "age": 28,
        "location": "home",
        "equipment_vi": "Tạ đơn",
        "sessions_per_week": 4,
        "session_minutes": 60,
        "experience_level": 1,
        "activity": "sedentary",
        "focus_vi": ["Ngực"],
        "kg_per_week": 0.5,
    }
    rows = challenge_phase_copy(wizard)
    assert [r["label_vi"] for r in rows] == ["Nền tảng", "Ổn định", "Bám tiến bộ"]
    r1 = rows[0]["rationale_vi"]
    assert "tạ đơn ở nhà" in r1.lower()
    assert "4 buổi" in r1
    assert "làm quen động tác" in r1.lower()
    assert "pool" not in r1.lower()
    assert "\n" not in r1
    assert "tăng sức vừa phải" in rows[1]["rationale_vi"].lower()
    assert "ngực" in rows[2]["rationale_vi"].lower()
    slugs = [r["slug"] for row in rows for r in row["knowledge_refs"]]
    assert len(slugs) == len(set(slugs))
    labor = challenge_phase_copy({**wizard, "activity": "very_active", "goal": "gain_weight"})
    assert rows[0]["knowledge_refs"][2]["slug"] != labor[0]["knowledge_refs"][2]["slug"]
