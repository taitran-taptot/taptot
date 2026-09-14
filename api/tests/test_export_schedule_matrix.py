"""Flatten helpers for gym Challenge Excel export (no OpenAI)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from export_schedule_matrix_xlsx import (  # noqa: E402
    default_paths,
    iter_template_weeks,
    slim_week_templates,
    tuan_rows,
    _payload_for_case,
    _write_xlsx,
)
from app.services.workout_generation.schedule_case_matrix import (
    filter_schedule_cases,
    iter_schedule_cases,
)
from app.services.workout_generation.session_policy import CHALLENGE_WEEKS


def _day(eid: int, *, day_number: int = 1, sets: int = 3) -> dict:
    return {
        "day_number": day_number,
        "split_role": "push",
        "title_vi": "Push",
        "meals": [{"food_id": 1}],
        "exercises": [
            {
                "section": "warmup",
                "exercise_id": 1,
                "name_vi": "Giãn",
                "sets": 1,
                "reps": "5 phút",
                "rest_seconds": 25,
                "sort_order": 1,
            },
            {
                "section": "warmup",
                "exercise_id": eid,
                "name_vi": "Primer",
                "sets": 2,
                "reps": "4",
                "rest_seconds": 45,
                "sort_order": 2,
            },
            {
                "section": "main",
                "exercise_id": eid,
                "name_vi": "Bench",
                "sets": sets,
                "reps": "8",
                "rest_seconds": 120,
                "sort_order": 3,
            },
        ],
    }


def test_payload_sets_challenge_flags():
    case = next(c for c in iter_schedule_cases() if c.venue_key == "gym")
    plain = _payload_for_case(case, challenge=False)
    assert "challenge_100_days" not in plain
    assert plain["duration_weeks"] == 4
    chal = _payload_for_case(case, challenge=True)
    assert chal["challenge_100_days"] is True
    assert chal["duration_weeks"] == CHALLENGE_WEEKS == 14
    assert chal["ai_suggest_foods"] is True


def test_filter_and_default_paths_home_challenge():
    all_cases = iter_schedule_cases()
    home = filter_schedule_cases(all_cases, "home")
    assert len(home) == 348
    assert all(c.location == "home" for c in home)
    assert len(filter_schedule_cases(all_cases, "home_body")) == 150
    assert len(filter_schedule_cases(all_cases, "home_all")) == 150
    assert len(filter_schedule_cases(all_cases, "home_equip")) == 150
    ckpt, xlsx = default_paths(challenge=True, venue="home")
    assert ckpt.name == "schedule_matrix_challenge_home_checkpoint.jsonl"
    assert xlsx.name == "schedule_matrix_challenge_home.xlsx"


def test_slim_week_templates_drops_meals():
    raw = [
        {"a": [_day(10)], "b": [_day(20)]},
        {"a": [_day(11)], "b": [_day(21)]},
        {"a": [_day(12)], "b": [_day(22)]},
    ]
    slim = slim_week_templates(raw)
    assert len(slim) == 3
    assert "meals" not in slim[0]["a"][0]
    assert slim[0]["a"][0]["exercises"][1]["sets"] == 2


def test_iter_template_weeks_flattens_3x2():
    rec = {
        "week_templates": slim_week_templates(
            [
                {"a": [_day(10, day_number=1)], "b": [_day(20, day_number=1)]},
                {"a": [_day(11)], "b": [_day(21)]},
                {"a": [_day(12)], "b": [_day(22)]},
            ]
        )
    }
    weeks = list(iter_template_weeks(rec))
    assert [(p, ab, len(d)) for p, ab, d in weeks] == [
        (1, "A", 1),
        (1, "B", 1),
        (2, "A", 1),
        (2, "B", 1),
        (3, "A", 1),
        (3, "B", 1),
    ]


def test_tuan_rows_14_weeks_deload_uses_a():
    rows = tuan_rows("M_L1_3d_45m_gym")
    assert len(rows) == 14
    by_week = {int(r[1]): r for r in rows}
    assert by_week[1][2] == 1 and by_week[1][3] == "A" and by_week[1][4] is False
    assert by_week[2][3] == "B"
    assert by_week[4][3] == "A" and by_week[4][4] is True
    assert by_week[5][2] == 2 and by_week[5][3] == "A"
    assert by_week[8][3] == "A" and by_week[8][4] is True
    assert by_week[14][2] == 3 and by_week[14][4] is True


def test_write_xlsx_challenge_has_tuan_and_phase_columns(tmp_path):
    rec = {
        "case_id": "M_L1_2d_30m_gym",
        "status": "ok",
        "gender": "male",
        "experience_level": 1,
        "venue_key": "gym",
        "location": "gym",
        "no_equipment": False,
        "equipment_list": ["dumbbell"],
        "session_minutes": 30,
        "sessions_requested": 2,
        "sessions_expected": 2,
        "sessions_actual": 2,
        "matrix_week_code": "PPL",
        "expected_week_code": "PPL",
        "week_code_actual": "PPL",
        "overlay_expected": False,
        "split_overridden": False,
        "expected_roles": ["push", "pull"],
        "challenge": True,
        "n_phases": 3,
        "n_templates": 6,
        "error": None,
        "elapsed_s": 1,
        "week_templates": slim_week_templates(
            [
                {
                    "a": [_day(10, day_number=1), _day(11, day_number=2)],
                    "b": [_day(20, day_number=1), _day(21, day_number=2)],
                },
                {"a": [_day(12), _day(13, day_number=2)], "b": [_day(22), _day(23, day_number=2)]},
                {"a": [_day(14), _day(15, day_number=2)], "b": [_day(24), _day(25, day_number=2)]},
            ]
        ),
    }
    path = tmp_path / "out.xlsx"
    _write_xlsx([rec], path, challenge=True)
    from openpyxl import load_workbook

    wb = load_workbook(path)
    assert set(wb.sheetnames) >= {"Cases", "Buoi", "BaiTap", "Tuan"}
    buoi = list(wb["Buoi"].iter_rows(values_only=True))
    assert buoi[0][:4] == ("case_id", "phase", "week_ab", "day_number")
    body = buoi[1:]
    assert len(body) == 12  # 3 phases × 2 AB × 2 days
    phases = {(r[1], r[2]) for r in body}
    assert phases == {(1, "A"), (1, "B"), (2, "A"), (2, "B"), (3, "A"), (3, "B")}
    tuan = list(wb["Tuan"].iter_rows(values_only=True))
    assert len(tuan) == 14  # header + 13
    cases = list(wb["Cases"].iter_rows(values_only=True))
    headers = list(cases[0])
    assert "challenge" in headers
    assert "equipment_list" in headers
    assert cases[1][headers.index("n_phases")] == 3
    assert cases[1][headers.index("equipment_list")] == "dumbbell"
