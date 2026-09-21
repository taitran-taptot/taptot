"""Tests for curriculum mesocycle RPE tweaks (production challenge path)."""

from app.schemas.plans import PlanDayIn, PlanExerciseIn, PlanInsightsOut
from app.services.workout_generation.phase_templates import (
    apply_phase_rpe,
    curriculum_insight_payload,
)


def test_three_phase_rpe_templates_differ():
    day = PlanDayIn(
        day_number=1,
        title_vi="Push",
        split_role="push",
        exercises=[
            PlanExerciseIn(exercise_id=10, sets=3, reps="8-12", rest_seconds=90, section="main"),
            PlanExerciseIn(exercise_id=11, sets=3, reps="10-12", rest_seconds=60, section="main"),
        ],
    )
    p1 = apply_phase_rpe([day], 0)
    p2 = apply_phase_rpe([day], 1)
    p3 = apply_phase_rpe(
        [day],
        2,
        meta_by_id={
            10: {"muscle_slug": "nguc", "movement_role": "compound"},
            11: {"muscle_slug": "vai", "movement_role": "isolation"},
        },
        focus_slugs={"nguc"},
    )
    assert "còn làm thêm" not in (p1[0].exercises[0].notes_vi or "")
    assert "còn làm thêm" not in (p2[0].exercises[0].notes_vi or "")
    assert "Làm số cái trên lịch rồi dừng" in (p1[0].exercises[0].notes_vi or "")
    nguc = next(e for e in p3[0].exercises if e.exercise_id == 10)
    assert "Ưu tiên nhóm mục tiêu" in (nguc.notes_vi or "")
    others = [e for e in p3[0].exercises if e.exercise_id != 10]
    if others:
        assert all("Ưu tiên nhóm mục tiêu" not in (e.notes_vi or "") for e in others)
    assert "RPE" not in (p1[0].exercises[0].notes_vi or "")
    assert (p2[0].exercises[0].rest_seconds or 90) <= 90
    assert p2[0].exercises[0].rest_seconds in {0, 30, 45, 60, 90, 120, 150, 180}
    assert p3[0].exercises[0].sets >= p1[0].exercises[0].sets


def test_curriculum_insight_shape():
    payload = curriculum_insight_payload()
    assert payload["deload_weeks"] == [4, 8, 14]
    assert payload["duration_weeks"] == 14
    assert len(payload["mesocycles"]) == 3
    assert payload["mesocycles"][0]["label_vi"] == "Nền tảng"
    assert payload["mesocycles"][2]["weeks"] == [9, 10, 11, 12, 13, 14]
    assert payload["mesocycles"][2]["deload_week"] == 14


def test_curriculum_insight_includes_rationale():
    payload = curriculum_insight_payload(
        rationale_vi=["Tháng 1 tập form.", "", "Tháng 3 nhấn ngực."]
    )
    assert payload["mesocycles"][0]["rationale_vi"] == "Tháng 1 tập form."
    assert "rationale_vi" not in payload["mesocycles"][1]
    assert payload["mesocycles"][2]["rationale_vi"] == "Tháng 3 nhấn ngực."


def test_plan_insights_out_keeps_curriculum_and_nutrition():
    payload = curriculum_insight_payload()
    out = PlanInsightsOut.model_validate(
        {
            "overview": {"summary_vi": "x"},
            "challenge_100_days": True,
            "curriculum": payload,
            "nutrition_blocks": [{"block_index": 0, "weeks": [1, 2, 3, 4]}],
            "week_templates": [[{"dropped": True}]],
        }
    )
    assert out.challenge_100_days is True
    assert out.curriculum is not None
    assert len(out.curriculum.mesocycles) == 3
    assert out.nutrition_blocks and out.nutrition_blocks[0]["weeks"] == [1, 2, 3, 4]
    assert "week_templates" not in out.model_dump()
