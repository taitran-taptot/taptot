"""Keyword injury / age denylist for workout shortlists."""

from app.services.workout_generation.injury_filters import parse_injury_constraints


def test_knee_note_denies_squat_and_jump():
    c = parse_injury_constraints("Đau gối phải khi ngồi xổm")
    assert "squat" in c.denied_patterns
    assert "squat" in c.denied_families
    assert c.blocks_exercise(pattern="squat", muscle_slug="quads", name_vi="Squat cốc")
    assert c.blocks_exercise(pattern="hinge", muscle_slug="hamstrings", name_vi="Box jump")
    assert not c.blocks_exercise(pattern="h_push", muscle_slug="chest", name_vi="Bench press")


def test_ngoi_does_not_match_goi():
    c = parse_injury_constraints("Hay ngồi lâu, muốn tăng cơ")
    assert "squat" not in c.denied_patterns
    assert not c.notes_vi


def test_shoulder_denies_vertical_press():
    c = parse_injury_constraints("Đau vai trái")
    assert "v_push" in c.denied_patterns
    assert c.blocks_exercise(pattern="v_push", muscle_slug="shoulders", name_vi="Military press")
    assert not c.blocks_exercise(pattern="h_push", muscle_slug="chest", name_vi="Push up")


def test_back_denies_hinge_keeps_squat_pattern_unless_listed():
    c = parse_injury_constraints("Đau lưng dưới, thoát vị")
    assert "hinge" in c.denied_patterns
    assert c.blocks_exercise(pattern="hinge", muscle_slug="hamstrings", name_vi="Deadlift")
    assert not c.blocks_exercise(pattern="squat", muscle_slug="quads", name_vi="Goblet squat")


def test_age_45_denies_plyo_without_note():
    c = parse_injury_constraints("", age=45)
    assert c.blocks_exercise(pattern="conditioning", muscle_slug="quads", name_vi="Box jump")
    assert c.blocks_exercise(pattern="pull", muscle_slug="lats", name_vi="Kipping pull-up")
    assert not c.blocks_exercise(pattern="squat", muscle_slug="quads", name_vi="Goblet squat")
