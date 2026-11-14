"""100-day challenge cases -> Excel. persist=False.

138240 cases = 3 kits x 2 genders x 3 levels x 5 sessions x 2 minutes
x 64 focus combinations x 4 goals x 3 strength tiers.
Exercise rows are the 1440-case core (maintain, tier ok, focus empty or one area), all 14 weeks.
"""

from __future__ import annotations

import json
import os
import sys
import time
from functools import lru_cache
from itertools import combinations
from multiprocessing import Process
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
API = ROOT / "api"
if str(API) not in sys.path:
    sys.path.insert(0, str(API))

from openpyxl import Workbook
from openpyxl.cell import WriteOnlyCell
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from sqlalchemy import text

from app.core.database import SessionLocal
from app.services.periodization import expand_plan_days_for_weeks
from app.services.workout_generation.focus import FOCUS_CANONICAL, normalize_focus_areas
from app.services.workout_generation.load_estimate import (
    BAND_LEVEL_LBS,
    BAND_LEVEL_NAME_VI,
    default_band_level,
)
from app.services.workout_generation.service import generate_workout

OUT_XLSX = ROOT / "docs" / "testing" / "kit-load-cases.xlsx"
CKPT = ROOT / "docs" / "testing" / "kit-load-cases.ckpt.jsonl"
BAND_OUT_XLSX = ROOT / "docs" / "testing" / "kit-load-cases-band.xlsx"
BAND_CKPT = ROOT / "docs" / "testing" / "kit-load-cases-band.ckpt.jsonl"
CHALLENGE_OUT_XLSX = ROOT / "docs" / "testing" / "challenge-100-cases.xlsx"
CHALLENGE_CKPT = ROOT / "docs" / "testing" / "challenge-100-cases.ckpt.jsonl"
SAMPLE_WEEKS = (1, 7, 14)

KITS: tuple[str, ...] = ("resistance-band", "dumbbell", "bar-and-rings")
GENDERS: tuple[str, ...] = ("male", "female")
LEVELS: tuple[int, ...] = (1, 2, 3)
SESSIONS: tuple[int, ...] = (2, 3, 4, 5, 6)
MINUTES: tuple[int, ...] = (45, 60)
GOALS: tuple[str, ...] = ("lose_weight", "maintain", "gain_weight", "gain_muscle")
TIERS: tuple[str, ...] = ("weak", "ok", "strong")
FOCUS_VALUES: tuple[tuple[str, ...], ...] = ((),) + tuple((key,) for key in FOCUS_CANONICAL)
FOCUS_COMBOS: tuple[tuple[str, ...], ...] = tuple(
    combo
    for size in range(0, 4)
    for combo in combinations(FOCUS_CANONICAL, size)
)
BAR_EQUIPMENT: tuple[str, ...] = ("pull-up-bar", "gymnastic-rings")
FULL_CASE_COUNT = 138_240
CORE_CASE_COUNT = 1_440

CASE_HEADERS = [
    "case_id",
    "kit",
    "gioi",
    "trinh_do",
    "focus",
    "buoi_xin",
    "buoi_thuc",
    "test_day",
    "test_keo",
    "test_chan",
    "week_code",
    "error",
]
EX_HEADERS = [
    "case_id",
    "test_day",
    "test_keo",
    "test_chan",
    "tuan",
    "pha",
    "buoi",
    "split",
    "section",
    "ten",
    "goi_y",
    "sets",
    "reps",
    "rest",
    "notes_vi",
]

GENDER_VI = {"male": "Nam", "female": "Nữ"}
LEVEL_VI = {
    1: "người mới",
    2: "đã có thói quen",
    3: "tập đều",
    4: "trên 12 tháng",
    5: "trên 12 tháng",
}
GOAL_VI = {
    "lose_weight": "Giảm cân",
    "maintain": "Giữ cân",
    "gain_weight": "Tăng cân",
    "gain_muscle": "Tăng cơ",
}
GOAL_CODE = {
    "lose_weight": "lose",
    "maintain": "keep",
    "gain_weight": "gain",
    "gain_muscle": "muscle",
}
TIER_VI = {"weak": "Yếu", "ok": "Vừa", "strong": "Mạnh"}
ACTIVITY_VI = {
    "sedentary": "Ngồi nhiều",
    "light": "Vận động nhẹ",
    "moderate": "Vận động vừa",
    "active": "Vận động nhiều",
    "very_active": "Lao động nặng",
}
KIT_CODE = {"resistance-band": "band", "dumbbell": "db", "bar-and-rings": "bar"}

CHALLENGE_CASE_HEADERS = [
    "case_id",
    "kit",
    "gioi",
    "tuoi",
    "chieu_cao_cm",
    "can_nang_kg",
    "van_dong",
    "level",
    "trinh_do",
    "tier",
    "muc_tieu",
    "phut_xin",
    "phut_thuc",
    "focus",
    "buoi_xin",
    "buoi_thuc",
    "week_code",
    "test_day",
    "test_keo",
    "test_chan",
    "tdee",
    "kcal_muc_tieu",
    "protein_g",
    "carb_g",
    "fat_g",
    "error",
]
CHALLENGE_EX_HEADERS = [
    "case_id",
    "tuan",
    "pha",
    "buoi",
    "split",
    "section",
    "ten",
    "goi_y",
    "sets",
    "reps",
    "rest",
    "notes_vi",
]
BIEN_HEADERS = [
    "case_id",
    "mo_ta",
    "kit",
    "level",
    "muc_tieu",
    "buoi_xin",
    "buoi_thuc",
    "phut_xin",
    "phut_thuc",
    "focus_gui",
    "focus_con",
    "tuoi",
    "van_dong",
    "kg_per_week",
    "health_note",
    "week_code",
    "tdee",
    "kcal_muc_tieu",
    "error",
]

BAND_CASE_HEADERS = [
    "case_id",
    "gioi",
    "tuoi",
    "chieu_cao_cm",
    "can_nang_kg",
    "van_dong",
    "trinh_do",
    "muc_tieu",
    "phut_buoi",
    "focus",
    "buoi_xin",
    "buoi_thuc",
    "week_code",
    "test_day",
    "test_keo",
    "test_chan",
    "tdee",
    "kcal_muc_tieu",
    "protein_g",
    "carb_g",
    "fat_g",
    "error",
]
BAND_EX_HEADERS = [
    "case_id",
    "tuan",
    "pha",
    "buoi",
    "split",
    "section",
    "ten",
    "goi_y",
    "sets",
    "reps",
    "rest",
    "notes_vi",
]


def _profile(gender: str) -> dict[str, Any]:
    female = gender == "female"
    return {
        "age": 28,
        "height_cm": 160.0 if female else 175.0,
        "weight_kg": 68.0 if female else 75.0,
        "activity": "moderate",
    }


def baseline_for(kit: str, gender: str, level: int, tier: str = "ok") -> dict[str, Any]:
    """Representative test that classifies as weak, ok, or strong for this kit and gender."""
    female = gender == "female"
    if tier not in TIERS:
        tier = "ok"
    if kit == "resistance-band":
        color = default_band_level(gender=gender, experience_level=level)
        if tier == "weak":
            push, pull, squat = (2, 7, 8) if female else (4, 7, 8)
        elif tier == "strong":
            push, pull, squat = (20, 29, 30)
        else:
            push, pull, squat = (15, 15, 15)
        return {
            "test_kit": "band",
            "band_level": color,
            "band_level_push": color,
            "band_level_pull": color,
            "band_level_squat": color,
            "pushups_max": push,
            "pullups_max": pull,
            "squats_max": squat,
        }
    if kit == "bar-and-rings":
        if tier == "weak":
            push, pull, squat = (2, 0, 8) if female else (4, 0, 8)
        elif tier == "strong":
            push, pull, squat = (12, 6, 30) if female else (20, 10, 30)
        else:
            push, pull, squat = (6, 3, 15) if female else (10, 4, 15)
        return {
            "test_kit": "bar_rings",
            "pushups_max": push,
            "pullups_max": pull,
            "squats_max": squat,
        }
    if tier == "weak":
        press, row, goblet, reps = 2.5, 2.5, 4.0, 8
    elif tier == "strong":
        press, row, goblet, reps = 15.0, 15.0, 22.0, 16
    else:
        press, row, goblet, reps = 8.0, 8.0, 12.0, 15
    return {
        "test_kit": "dumbbell",
        "db_press_kg": press,
        "db_row_kg": row,
        "goblet_kg": goblet,
        "db_press_reps": reps,
        "db_row_reps": reps,
        "goblet_reps": reps,
        "pushups_max": 15,
        "pullups_max": 15,
        "squats_max": 15,
    }


def fitness_test_inputs(spec: dict[str, Any]) -> dict[str, str]:
    """The fitness-test entry for this case: color or kg, plus the rep count."""
    base = spec.get("baseline") or {}
    if spec["kit"] == "resistance-band":
        def band(color_key: str, reps_key: str) -> str:
            color = str(base.get(color_key) or base.get("band_level") or "")
            name = BAND_LEVEL_NAME_VI.get(color, color)
            lbs = BAND_LEVEL_LBS.get(color, "")
            return f"Dây {name} · {lbs} lbs · {base.get(reps_key)} cái"

        return {
            "test_day": band("band_level_push", "pushups_max"),
            "test_keo": band("band_level_pull", "pullups_max"),
            "test_chan": band("band_level_squat", "squats_max"),
        }
    if spec["kit"] == "bar-and-rings":
        return {
            "test_day": f"Chống đẩy · {base.get('pushups_max')} cái",
            "test_keo": f"Kéo xà · {base.get('pullups_max')} cái",
            "test_chan": f"Squat · {base.get('squats_max')} cái",
        }

    def bell(kg_key: str, reps_key: str) -> str:
        kg = base.get(kg_key)
        kg_txt = f"{kg:g}" if isinstance(kg, float) else kg
        return f"{kg_txt} kg · {base.get(reps_key)} cái"

    return {
        "test_day": bell("db_press_kg", "db_press_reps"),
        "test_keo": bell("db_row_kg", "db_row_reps"),
        "test_chan": bell("goblet_kg", "goblet_reps"),
    }


def is_core(spec: dict[str, Any]) -> bool:
    """Maintain, mid tier, and at most one focus area. This is the exercise sheet."""
    return spec.get("goal") == "maintain" and spec.get("tier") == "ok" and len(spec.get("focus") or []) <= 1


def _spec(
    *,
    case_id: str,
    kit: str,
    gender: str,
    level: int,
    focus: tuple[str, ...] | list[str],
    sessions: int,
    minutes: int,
    goal: str,
    tier: str,
    age: int | None = None,
    activity: str | None = None,
    kg_per_week: float | None = None,
    health_note: str | None = None,
    mo_ta: str = "",
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "case_id": case_id,
        "kit": kit,
        "gender": gender,
        "level": level,
        "focus": list(focus),
        "sessions": sessions,
        "minutes": minutes,
        "goal": goal,
        "tier": tier,
        "baseline": baseline_for(kit, gender, level if level in LEVELS else 2, tier),
        "mo_ta": mo_ta,
    }
    if age is not None:
        row["age"] = age
    if activity:
        row["activity"] = activity
    if kg_per_week is not None:
        row["kg_per_week"] = kg_per_week
    if health_note:
        row["health_note"] = health_note
    return row


@lru_cache(maxsize=1)
def iter_specs() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for kit in KITS:
        code = KIT_CODE[kit]
        for gender in GENDERS:
            g = "F" if gender == "female" else "M"
            for level in LEVELS:
                for focus in FOCUS_COMBOS:
                    focus_id = "+".join(focus) if focus else "none"
                    for sessions in SESSIONS:
                        for minutes in MINUTES:
                            for goal in GOALS:
                                for tier in TIERS:
                                    out.append(
                                        _spec(
                                            case_id=(
                                                f"{code}_{g}_L{level}_{focus_id}"
                                                f"_s{sessions}_m{minutes}_{GOAL_CODE[goal]}_{tier}"
                                            ),
                                            kit=kit,
                                            gender=gender,
                                            level=level,
                                            focus=focus,
                                            sessions=sessions,
                                            minutes=minutes,
                                            goal=goal,
                                            tier=tier,
                                        )
                                    )
    return out


def iter_core_specs() -> list[dict[str, Any]]:
    return [spec for spec in iter_specs() if is_core(spec)]


def iter_band_specs() -> list[dict[str, Any]]:
    return [spec for spec in iter_specs() if spec["kit"] == "resistance-band"]


def iter_boundary_specs() -> list[dict[str, Any]]:
    """Rejected or clamped inputs. One axis each, not crossed into the main grid."""
    common = {
        "kit": "resistance-band",
        "gender": "male",
        "level": 2,
        "focus": (),
        "sessions": 3,
        "minutes": 60,
        "goal": "maintain",
        "tier": "ok",
    }

    def one(case_id: str, mo_ta: str, **overrides: Any) -> dict[str, Any]:
        fields = {**common, **overrides}
        return _spec(case_id=case_id, mo_ta=mo_ta, **fields)

    return [
        one("bien_level_4", "Level 4 bị từ chối", level=4),
        one("bien_level_5", "Level 5 bị từ chối", level=5),
        one("bien_sessions_7", "Buổi 7 bị cắt về tối đa 6", sessions=7),
        one("bien_minutes_30", "30 phút gom về 45", minutes=30),
        one("bien_minutes_53", "53 phút gom về 60", minutes=53),
        one(
            "bien_focus_4",
            "Focus thứ tư bị cắt, còn 3 vùng",
            focus=("nguc", "lung", "mong", "chan"),
        ),
        one("bien_age_45", "Tuổi 45 tránh bài nhảy", age=45),
        one("bien_activity_sedentary", "Vận động ngồi nhiều", activity="sedentary"),
        one("bien_activity_very_active", "Vận động lao động nặng", activity="very_active"),
        one(
            "bien_kg_0_1",
            "Giảm 0,1 kg/tuần",
            goal="lose_weight",
            kg_per_week=0.1,
        ),
        one(
            "bien_kg_1_5",
            "Tăng 1,5 kg/tuần",
            goal="gain_weight",
            kg_per_week=1.5,
        ),
        one("bien_note_goi", "Ghi chú gối", health_note="đau gối"),
        one("bien_note_vai", "Ghi chú vai", health_note="đau vai"),
        one("bien_note_lung", "Ghi chú lưng", health_note="đau lưng"),
    ]


def equipment_for(kit: str) -> list[str]:
    if kit == "bar-and-rings":
        return list(BAR_EQUIPMENT)
    return [kit]


def payload_for(spec: dict[str, Any]) -> dict[str, Any]:
    profile = _profile(spec["gender"])
    if spec.get("age") is not None:
        profile["age"] = spec["age"]
    if spec.get("activity"):
        profile["activity"] = spec["activity"]
    payload: dict[str, Any] = {
        "goal": spec["goal"],
        "gender": spec["gender"],
        "sessions_per_week": spec["sessions"],
        "session_minutes": spec["minutes"],
        "location": "home",
        "focus_areas": list(spec["focus"] or []),
        "extra_goals": [],
        "equipment_list": equipment_for(spec["kit"]),
        "food_ids": [],
        "experience_level": spec["level"],
        "ai_suggest_equipment": False,
        "no_equipment": False,
        "ai_suggest_foods": False,
        "fitness_baseline": dict(spec["baseline"]),
        "duration_weeks": 14,
        "challenge_100_days": True,
        "curriculum_12_weeks": False,
        **profile,
    }
    if spec.get("kg_per_week") is not None:
        payload["kg_per_week"] = spec["kg_per_week"]
    if spec.get("health_note"):
        payload["health_note"] = spec["health_note"]
    return payload


def load_catalog(db) -> dict[int, dict[str, Any]]:
    rows = db.execute(text("SELECT id, name_en, name_vi FROM exercises")).mappings().all()
    return {int(r["id"]): dict(r) for r in rows}


def _exercise_name(ex: dict[str, Any], catalog: dict[int, dict[str, Any]]) -> str:
    try:
        eid = int(ex.get("exercise_id"))
    except (TypeError, ValueError):
        eid = None
    cat = catalog.get(eid) if eid is not None else None
    return str(
        (cat or {}).get("name_vi")
        or ex.get("name_vi")
        or (cat or {}).get("name_en")
        or ex.get("name_en")
        or ""
    )


def _load_note(ex: dict[str, Any]) -> str:
    rx = ex.get("set_prescriptions") or []
    if rx and isinstance(rx[0], dict):
        return str(rx[0].get("load_note_vi") or "")
    return ""


def _notes(ex: dict[str, Any]) -> str:
    return str(ex.get("notes_vi") or "")


def with_suggestion(row: dict[str, Any]) -> dict[str, Any]:
    """Put the implement suggestion beside the exercise name and inside the note."""
    out = dict(row)
    goi = str(out.get("goi_y") or out.get("load_note_vi") or "").strip()
    notes = str(out.get("notes_vi") or "").strip()
    if goi and goi not in notes:
        notes = f"{goi}. {notes}".strip() if notes else goi
    out["goi_y"] = goi
    out["notes_vi"] = notes
    return out


def _week_of(day_number: int, sessions: int) -> int:
    return (max(1, int(day_number)) - 1) // max(1, int(sessions)) + 1


def _phase_of(week: int) -> int:
    if week <= 4:
        return 1
    if week <= 8:
        return 2
    return 3


def load_ckpt(path: Path) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    if not path.is_file():
        return latest
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            cid = row.get("case_id")
            if cid:
                latest[str(cid)] = row
    return latest


def append_ckpt(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def _profile_fields(spec: dict[str, Any]) -> dict[str, Any]:
    profile = _profile(spec["gender"])
    if spec.get("age") is not None:
        profile["age"] = spec["age"]
    activity = str(spec.get("activity") or profile["activity"])
    goal = str(spec["goal"])
    tier = str(spec.get("tier") or "ok")
    return {
        "tuoi": profile["age"],
        "chieu_cao_cm": profile["height_cm"],
        "can_nang_kg": profile["weight_kg"],
        "van_dong": ACTIVITY_VI.get(activity, activity),
        "level": spec["level"],
        "tier": TIER_VI.get(tier, tier),
        "muc_tieu": GOAL_VI.get(goal, goal),
        "phut_buoi": spec["minutes"],
        "phut_xin": spec["minutes"],
    }


def _nutrition_fields(insights: dict[str, Any] | None) -> dict[str, Any]:
    nutrition = (insights or {}).get("nutrition") or {}
    return {
        "tdee": nutrition.get("tdee", ""),
        "kcal_muc_tieu": nutrition.get("target_calories", ""),
        "protein_g": nutrition.get("protein_g", ""),
        "carb_g": nutrition.get("carbs_g", ""),
        "fat_g": nutrition.get("fat_g", ""),
    }


def _case_row(
    spec: dict[str, Any],
    *,
    sessions_actual: Any = "",
    week_code: str = "",
    error: str = "",
    insights: dict[str, Any] | None = None,
    phut_thuc: Any = "",
) -> dict[str, Any]:
    level = spec["level"]
    return {
        "case_id": spec["case_id"],
        "kit": spec["kit"],
        "gioi": GENDER_VI[spec["gender"]],
        "trinh_do": LEVEL_VI.get(level, str(level)),
        "focus": "+".join(spec.get("focus") or []),
        "buoi_xin": spec["sessions"],
        "buoi_thuc": sessions_actual,
        "week_code": week_code,
        "error": error,
        "phut_thuc": phut_thuc,
        **_profile_fields(spec),
        **fitness_test_inputs(spec),
        **_nutrition_fields(insights),
    }


def run_case(
    db,
    spec: dict[str, Any],
    catalog: dict[int, dict[str, Any]],
    *,
    weeks: tuple[int, ...] | None = SAMPLE_WEEKS,
    with_exercises: bool = True,
) -> dict[str, Any]:
    payload = payload_for(spec)
    t0 = time.perf_counter()
    try:
        result = generate_workout(db, None, payload, persist=False, commit=False)
    except Exception as exc:  # noqa: BLE001
        return {
            "spec": spec,
            "error": str(exc),
            "elapsed_s": round(time.perf_counter() - t0, 2),
            "case": _case_row(spec, error=str(exc)),
            "exercises": [],
        }
    insights = result.get("insights") or {}
    week_code = str(result.get("week_code") or insights.get("week_code") or "")
    sessions = int(result.get("sessions_actual") or spec["sessions"])
    phut_thuc = result.get("session_minutes", "")
    seed = result.get("days") or []
    expanded: list[dict[str, Any]] = []
    if with_exercises:
        templates = insights.get("week_templates")
        expanded = expand_plan_days_for_weeks(
            seed,
            14,
            is_dict=True,
            experience_level=spec["level"],
            week_templates=templates,
            curriculum=True,
            goal=spec["goal"],
        )
    ex_rows: list[dict[str, Any]] = []
    for day in expanded:
        week = _week_of(int(day.get("day_number") or 1), sessions)
        if weeks is not None and week not in weeks:
            continue
        session_in_week = ((int(day.get("day_number") or 1) - 1) % sessions) + 1
        for ex in day.get("exercises") or []:
            ex_rows.append(
                {
                    "case_id": spec["case_id"],
                    **fitness_test_inputs(spec),
                    "tuan": week,
                    "pha": _phase_of(week),
                    "buoi": session_in_week,
                    "split": day.get("split_role") or "",
                    "section": ex.get("section") or "main",
                    "ten": _exercise_name(ex, catalog),
                    "sets": ex.get("sets"),
                    "reps": ex.get("reps"),
                    "rest": ex.get("rest_seconds"),
                    "goi_y": _load_note(ex),
                    "notes_vi": _notes(ex),
                }
            )
    return {
        "spec": spec,
        "error": None,
        "elapsed_s": round(time.perf_counter() - t0, 2),
        "case": _case_row(
            spec,
            sessions_actual=sessions,
            week_code=week_code,
            insights=insights,
            phut_thuc=phut_thuc,
        ),
        "exercises": ex_rows,
    }


def write_xlsx(
    cases: list[dict[str, Any]],
    exercises: list[dict[str, Any]],
    path: Path,
    *,
    case_headers: list[str] | None = None,
    ex_headers: list[str] | None = None,
) -> None:
    wb = Workbook()
    fill = PatternFill(start_color="FF1F4E3D", end_color="FF1F4E3D", fill_type="solid")
    font = Font(bold=True, color="FFFFFFFF")
    wide = {"goi_y", "notes_vi", "week_code", "error", "test_day", "test_keo", "test_chan"}

    def sheet(title: str, headers: list[str], rows: list[dict[str, Any]]) -> None:
        ws = wb.create_sheet(title)
        ws.append(headers)
        for cell in ws[1]:
            cell.fill = fill
            cell.font = font
        for row in rows:
            ws.append([row.get(h, "") for h in headers])
        for i, h in enumerate(headers, start=1):
            ws.column_dimensions[get_column_letter(i)].width = 42 if h in wide else 16
        for header in ("goi_y", "notes_vi", "error"):
            if header not in headers:
                continue
            idx = headers.index(header) + 1
            for cells in ws.iter_rows(min_row=2, min_col=idx, max_col=idx):
                cells[0].alignment = Alignment(wrap_text=True, vertical="top")

    if "Sheet" in wb.sheetnames:
        del wb["Sheet"]
    sheet("Cases", case_headers or CASE_HEADERS, cases)
    sheet("Exercises", ex_headers or EX_HEADERS, exercises)
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)


def _export(
    specs: list[dict[str, Any]],
    *,
    ckpt: Path,
    out: Path,
    weeks: tuple[int, ...] | None,
    case_headers: list[str],
    ex_headers: list[str],
) -> None:
    print(f"specs {len(specs)}")
    done = load_ckpt(ckpt)
    cases: list[dict[str, Any]] = []
    exercises: list[dict[str, Any]] = []
    db = SessionLocal()
    try:
        catalog = load_catalog(db)
        for i, spec in enumerate(specs, start=1):
            cid = spec["case_id"]
            cached = done.get(cid)
            if cached and cached.get("case") and not cached.get("error"):
                cases.append({**cached["case"], **fitness_test_inputs(spec)})
                exercises.extend(
                    {**with_suggestion(ex), **fitness_test_inputs(spec)}
                    for ex in (cached.get("exercises") or [])
                )
                print(f"[{i}/{len(specs)}] skip {cid}")
                continue
            rec = run_case(db, spec, catalog, weeks=weeks)
            slim = {
                "case_id": cid,
                "error": rec.get("error"),
                "elapsed_s": rec.get("elapsed_s"),
                "case": rec.get("case"),
                "exercises": rec.get("exercises") or [],
            }
            append_ckpt(ckpt, slim)
            done[cid] = slim
            cases.append({**rec["case"], **fitness_test_inputs(spec)})
            exercises.extend(
                {**with_suggestion(ex), **fitness_test_inputs(spec)}
                for ex in (rec.get("exercises") or [])
            )
            print(f"[{i}/{len(specs)}] {cid} {rec.get('elapsed_s')}s err={rec.get('error')}")
    finally:
        db.close()
    write_xlsx(cases, exercises, out, case_headers=case_headers, ex_headers=ex_headers)
    print(f"wrote {out} cases={len(cases)} exercises={len(exercises)}")


def load_ckpt_index(path: Path) -> tuple[dict[str, dict[str, Any]], int]:
    """Latest small case row per id. Exercise lists stay on disk."""
    latest: dict[str, dict[str, Any]] = {}
    next_line = 1
    if not path.is_file():
        return latest, next_line
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            raw = line.strip()
            if not raw:
                continue
            try:
                row = json.loads(raw)
            except json.JSONDecodeError:
                next_line += 1
                continue
            cid = row.get("case_id")
            if cid:
                latest[str(cid)] = {
                    "error": row.get("error"),
                    "case": row.get("case"),
                    "saved_exercises": bool(row.get("saved_exercises")),
                    "line": next_line,
                }
            next_line += 1
    return latest, next_line


class _CkptWriter:
    def __init__(self, path: Path, next_line: int) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = path.open("a", encoding="utf-8")
        self.next_line = next_line

    def write(self, row: dict[str, Any]) -> int:
        self._fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        self._fh.flush()
        line = self.next_line
        self.next_line += 1
        return line

    def close(self) -> None:
        try:
            self._fh.close()
        except OSError:
            pass


def _boundary_row(spec: dict[str, Any], rec: dict[str, Any]) -> dict[str, Any]:
    case = rec.get("case") or {}
    sent = list(spec.get("focus") or [])
    kept = normalize_focus_areas(sent)
    kg = spec.get("kg_per_week")
    return {
        "case_id": spec["case_id"],
        "mo_ta": spec.get("mo_ta") or "",
        "kit": spec["kit"],
        "level": spec["level"],
        "muc_tieu": case.get("muc_tieu", ""),
        "buoi_xin": spec["sessions"],
        "buoi_thuc": case.get("buoi_thuc", ""),
        "phut_xin": spec["minutes"],
        "phut_thuc": case.get("phut_thuc", ""),
        "focus_gui": "+".join(sent),
        "focus_con": "+".join(kept),
        "tuoi": case.get("tuoi", ""),
        "van_dong": case.get("van_dong", ""),
        "kg_per_week": "" if kg is None else kg,
        "health_note": spec.get("health_note") or "",
        "week_code": case.get("week_code", ""),
        "tdee": case.get("tdee", ""),
        "kcal_muc_tieu": case.get("kcal_muc_tieu", ""),
        "error": rec.get("error") or "",
    }


def _styled_header(ws: Any, headers: list[str]) -> None:
    fill = PatternFill(start_color="FF1F4E3D", end_color="FF1F4E3D", fill_type="solid")
    font = Font(bold=True, color="FFFFFFFF")
    cells = []
    for header in headers:
        cell = WriteOnlyCell(ws, value=header)
        cell.fill = fill
        cell.font = font
        cells.append(cell)
    ws.append(cells)


def _exercise_ckpt(ex: dict[str, Any]) -> dict[str, Any]:
    cooked = with_suggestion(ex)
    return {header: cooked.get(header, "") for header in CHALLENGE_EX_HEADERS}


def _shard_path(shard: int) -> Path:
    return CHALLENGE_CKPT.with_name(f"challenge-100-cases.ckpt.{shard}.jsonl")


def _install_name_cache() -> None:
    """Reuse exercise-name lookups inside one export process. The catalog is read-only."""
    from app.services.workout_generation import kit_schedule

    original = kit_schedule._lookup_named
    found: dict[tuple[str, str], Any] = {}

    def cached(db, candidates, used_ids=None):
        taken = used_ids or set()
        for name_en, name_vi in candidates:
            key = (str(name_en or "").strip().lower(), str(name_vi or "").strip().lower())
            if key not in found:
                found[key] = original(db, [(name_en, name_vi)], None)
            row = found[key]
            if row is not None and int(row.id) not in taken:
                return row
        return None

    kit_schedule._lookup_named = cached


def _run_into_ckpt(
    db,
    catalog: dict[int, dict[str, Any]],
    specs: list[dict[str, Any]],
    core_ids: set[str],
    index: dict[str, dict[str, Any]],
    writer: _CkptWriter,
    *,
    label: str,
) -> Any:
    total = len(specs)
    _ = core_ids
    for i, spec in enumerate(specs, start=1):
        cid = spec["case_id"]
        cached = index.get(cid)
        if cached and cached.get("case") and not cached.get("error"):
            if i % 500 == 0 or i == total:
                print(f"[{label} {i}/{total}] skip {cid}", flush=True)
            continue
        rec = run_case(
            db,
            spec,
            catalog,
            weeks=SAMPLE_WEEKS,
            with_exercises=False,
        )
        if rec.get("error"):
            try:
                db.rollback()
            except Exception:  # noqa: BLE001
                pass
        slim = {
            "case_id": cid,
            "error": rec.get("error"),
            "elapsed_s": rec.get("elapsed_s"),
            "case": rec.get("case"),
            "saved_exercises": False,
            "exercises": [],
            "boundary": _boundary_row(spec, rec) if cid.startswith("bien_") else None,
        }
        line = writer.write(slim)
        index[cid] = {
            "error": slim["error"],
            "case": slim["case"],
            "saved_exercises": False,
            "line": line,
            "boundary": slim["boundary"],
        }
        if rec.get("error") or i % 50 == 0 or i == total:
            print(
                f"[{label} {i}/{total}] {cid} {rec.get('elapsed_s')}s err={rec.get('error')}",
                flush=True,
            )
    return db, catalog


def write_challenge_xlsx(
    specs: list[dict[str, Any]],
    boundaries: list[dict[str, Any]],
    core_ids: set[str],
    index: dict[str, dict[str, Any]],
    shards: list[tuple[Path, dict[str, int | None]]],
    path: Path,
) -> None:
    wb = Workbook(write_only=True)
    cases = wb.create_sheet("Cases")
    _styled_header(cases, CHALLENGE_CASE_HEADERS)
    for spec in specs:
        row = (index.get(spec["case_id"]) or {}).get("case") or {}
        cases.append([row.get(header, "") for header in CHALLENGE_CASE_HEADERS])

    exercises = wb.create_sheet("Exercises")
    _styled_header(exercises, CHALLENGE_EX_HEADERS)
    exercise_rows = 0
    _install_name_cache()
    db = SessionLocal()
    try:
        catalog = load_catalog(db)
        core_specs = [
            spec
            for spec in specs
            if spec["case_id"] in core_ids and not (index.get(spec["case_id"]) or {}).get("error")
        ]
        print(f"exercise plans {len(core_specs)}", flush=True)
        for i, spec in enumerate(core_specs, start=1):
            rec = run_case(db, spec, catalog, weeks=None, with_exercises=True)
            if rec.get("error"):
                try:
                    db.rollback()
                except Exception:  # noqa: BLE001
                    pass
            for ex in rec.get("exercises") or []:
                cooked = with_suggestion(ex)
                exercises.append([cooked.get(header, "") for header in CHALLENGE_EX_HEADERS])
                exercise_rows += 1
            if rec.get("error") or i % 25 == 0 or i == len(core_specs):
                print(
                    f"[ex {i}/{len(core_specs)}] {spec['case_id']} rows={exercise_rows} err={rec.get('error')}",
                    flush=True,
                )
    finally:
        db.close()

    bien = wb.create_sheet("Bien")
    _styled_header(bien, BIEN_HEADERS)
    for spec in boundaries:
        meta = index.get(spec["case_id"]) or {}
        row = meta.get("boundary")
        if not row:
            case = meta.get("case") or {}
            row = _boundary_row(
                spec,
                {"case": case, "error": meta.get("error")},
            )
        bien.append([row.get(header, "") for header in BIEN_HEADERS])

    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)
    print(
        f"wrote {path} cases={len(specs)} exercises={exercise_rows} bien={len(boundaries)}",
        flush=True,
    )


def _challenge_limit() -> int:
    raw = os.environ.get("CHALLENGE_LIMIT", "").strip()
    if not raw:
        return 0
    return max(0, int(raw))


def _worker_count() -> int:
    for arg in sys.argv:
        if arg.startswith("--workers="):
            return max(1, int(arg.split("=", 1)[1]))
    return 4


def _challenge_worker(shard: int, shards: int) -> None:
    _install_name_cache()
    limit = _challenge_limit()
    specs = [
        spec
        for i, spec in enumerate(iter_specs())
        if (limit <= 0 or i < limit) and i % shards == shard
    ]
    core_ids = {spec["case_id"] for spec in specs if is_core(spec)}
    extra = iter_boundary_specs() if shard == 0 and limit <= 0 else []
    path = _shard_path(shard)
    index, next_line = load_ckpt_index(path)
    writer = _CkptWriter(path, next_line)
    db = SessionLocal()
    try:
        catalog = load_catalog(db)
        print(f"[w{shard}] specs {len(specs)} core {len(core_ids)} bien {len(extra)}", flush=True)
        db, catalog = _run_into_ckpt(
            db, catalog, specs, core_ids, index, writer, label=f"w{shard}"
        )
        if extra:
            db, catalog = _run_into_ckpt(
                db, catalog, extra, set(), index, writer, label=f"w{shard}-bien"
            )
    finally:
        writer.close()
        db.close()


def _load_shards(workers: int) -> tuple[dict[str, dict[str, Any]], list[tuple[Path, dict[str, int | None]]]]:
    merged: dict[str, dict[str, Any]] = {}
    shards: list[tuple[Path, dict[str, int | None]]] = []
    for shard in range(workers):
        path = _shard_path(shard)
        index, _next = load_ckpt_index(path)
        merged.update(index)
        shards.append((path, {cid: meta.get("line") for cid, meta in index.items()}))
    return merged, shards


def export_challenge() -> None:
    workers = _worker_count()
    limit = _challenge_limit()
    if len(iter_specs()) != FULL_CASE_COUNT:
        raise SystemExit(f"expected {FULL_CASE_COUNT} cases, got {len(iter_specs())}")
    print(f"workers {workers} limit {limit or 'all'}", flush=True)
    if workers == 1:
        _challenge_worker(0, 1)
    else:
        procs = [Process(target=_challenge_worker, args=(shard, workers)) for shard in range(workers)]
        for proc in procs:
            proc.start()
        codes = []
        for proc in procs:
            proc.join()
            codes.append(proc.exitcode)
        if any(code != 0 for code in codes):
            raise SystemExit(f"worker exit codes {codes}")
    if limit > 0:
        print("limited run, checkpoint only", flush=True)
        return
    specs = iter_specs()
    core_ids = {spec["case_id"] for spec in specs if is_core(spec)}
    if len(core_ids) != CORE_CASE_COUNT:
        raise SystemExit(f"expected {CORE_CASE_COUNT} core cases, got {len(core_ids)}")
    index, shards = _load_shards(workers)
    missing = [
        spec["case_id"]
        for spec in specs
        if not (index.get(spec["case_id"]) or {}).get("case")
    ]
    if missing:
        raise SystemExit(f"missing {len(missing)} cases, first {missing[:3]}")
    boundaries = iter_boundary_specs()
    bien_missing = [
        spec["case_id"]
        for spec in boundaries
        if not (index.get(spec["case_id"]) or {}).get("case")
    ]
    if bien_missing:
        raise SystemExit(f"missing boundary cases {bien_missing}")
    write_challenge_xlsx(
        specs, boundaries, core_ids, index, shards, CHALLENGE_OUT_XLSX
    )


def main() -> None:
    export_challenge()


def main_band() -> None:
    _export(
        iter_band_specs(),
        ckpt=BAND_CKPT,
        out=BAND_OUT_XLSX,
        weeks=None,
        case_headers=BAND_CASE_HEADERS,
        ex_headers=BAND_EX_HEADERS,
    )


if __name__ == "__main__":
    if "--band" in sys.argv:
        main_band()
    else:
        main()
