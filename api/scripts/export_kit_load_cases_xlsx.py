"""Band and dumbbell challenge cases -> Excel. persist=False.

480 cases = 2 kits x 2 genders x 3 levels x 8 focus values x 5 session counts.
Weeks 1, 7, and 14 only (phase 1, phase 2, phase-3 deload).
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
API = ROOT / "api"
if str(API) not in sys.path:
    sys.path.insert(0, str(API))

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from sqlalchemy import text

from app.core.database import SessionLocal
from app.services.periodization import expand_plan_days_for_weeks
from app.services.workout_generation.focus import FOCUS_CANONICAL
from app.services.workout_generation.load_estimate import (
    BAND_LEVEL_LBS,
    BAND_LEVEL_NAME_VI,
    default_band_level,
    default_db_kg,
)
from app.services.workout_generation.service import generate_workout

OUT_XLSX = ROOT / "docs" / "testing" / "kit-load-cases.xlsx"
CKPT = ROOT / "docs" / "testing" / "kit-load-cases.ckpt.jsonl"
SAMPLE_WEEKS = (1, 7, 14)

KITS: tuple[str, ...] = ("resistance-band", "dumbbell")
GENDERS: tuple[str, ...] = ("male", "female")
LEVELS: tuple[int, ...] = (1, 2, 3)
SESSIONS: tuple[int, ...] = (2, 3, 4, 5, 6)
FOCUS_VALUES: tuple[tuple[str, ...], ...] = ((),) + tuple((key,) for key in FOCUS_CANONICAL)

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
LEVEL_VI = {1: "người mới", 2: "đã có thói quen", 3: "tập đều"}
KIT_CODE = {"resistance-band": "band", "dumbbell": "db"}


def _profile(gender: str) -> dict[str, Any]:
    female = gender == "female"
    return {
        "age": 28,
        "height_cm": 160.0 if female else 175.0,
        "weight_kg": 68.0 if female else 75.0,
        "activity": "moderate",
    }


def baseline_for(kit: str, gender: str, level: int) -> dict[str, Any]:
    """Mid test: AMRAP 15 on the default color or kilograms for this person."""
    if kit == "resistance-band":
        color = default_band_level(gender=gender, experience_level=level)
        return {
            "test_kit": "band",
            "band_level": color,
            "band_level_push": color,
            "band_level_pull": color,
            "band_level_squat": color,
            "pushups_max": 15,
            "pullups_max": 15,
            "squats_max": 15,
        }
    press = default_db_kg(gender=gender, experience_level=level, slot="press")
    row = default_db_kg(gender=gender, experience_level=level, slot="row")
    squat = default_db_kg(gender=gender, experience_level=level, slot="squat")
    return {
        "test_kit": "dumbbell",
        "db_press_kg": press,
        "db_row_kg": row,
        "goblet_kg": squat,
        "db_press_reps": 15,
        "db_row_reps": 15,
        "goblet_reps": 15,
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

    def bell(kg_key: str, reps_key: str) -> str:
        kg = base.get(kg_key)
        kg_txt = f"{kg:g}" if isinstance(kg, float) else kg
        return f"{kg_txt} kg · {base.get(reps_key)} cái"

    return {
        "test_day": bell("db_press_kg", "db_press_reps"),
        "test_keo": bell("db_row_kg", "db_row_reps"),
        "test_chan": bell("goblet_kg", "goblet_reps"),
    }


def iter_specs() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for kit in KITS:
        code = KIT_CODE[kit]
        for gender in GENDERS:
            g = "F" if gender == "female" else "M"
            for level in LEVELS:
                for focus in FOCUS_VALUES:
                    focus_id = focus[0] if focus else "none"
                    for sessions in SESSIONS:
                        out.append(
                            {
                                "case_id": f"{code}_{g}_L{level}_{focus_id}_s{sessions}",
                                "kit": kit,
                                "gender": gender,
                                "level": level,
                                "focus": list(focus),
                                "sessions": sessions,
                                "minutes": 60,
                                "goal": "maintain",
                                "baseline": baseline_for(kit, gender, level),
                            }
                        )
    return out


def payload_for(spec: dict[str, Any]) -> dict[str, Any]:
    return {
        "goal": spec["goal"],
        "gender": spec["gender"],
        "sessions_per_week": spec["sessions"],
        "session_minutes": spec["minutes"],
        "location": "home",
        "focus_areas": list(spec["focus"] or []),
        "extra_goals": [],
        "equipment_list": [spec["kit"]],
        "food_ids": [],
        "experience_level": spec["level"],
        "ai_suggest_equipment": False,
        "no_equipment": False,
        "ai_suggest_foods": False,
        "fitness_baseline": dict(spec["baseline"]),
        "duration_weeks": 14,
        "challenge_100_days": True,
        "curriculum_12_weeks": False,
        **_profile(spec["gender"]),
    }


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


def _case_row(
    spec: dict[str, Any],
    *,
    sessions_actual: Any = "",
    week_code: str = "",
    error: str = "",
) -> dict[str, Any]:
    return {
        "case_id": spec["case_id"],
        "kit": spec["kit"],
        "gioi": GENDER_VI[spec["gender"]],
        "trinh_do": LEVEL_VI[spec["level"]],
        "focus": "+".join(spec.get("focus") or []),
        "buoi_xin": spec["sessions"],
        "buoi_thuc": sessions_actual,
        "week_code": week_code,
        "error": error,
        **fitness_test_inputs(spec),
    }


def run_case(db, spec: dict[str, Any], catalog: dict[int, dict[str, Any]]) -> dict[str, Any]:
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
    seed = result.get("days") or []
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
        if week not in SAMPLE_WEEKS:
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
        "case": _case_row(spec, sessions_actual=sessions, week_code=week_code),
        "exercises": ex_rows,
    }


def write_xlsx(cases: list[dict[str, Any]], exercises: list[dict[str, Any]], path: Path) -> None:
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
    sheet("Cases", CASE_HEADERS, cases)
    sheet("Exercises", EX_HEADERS, exercises)
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)


def main() -> None:
    specs = iter_specs()
    print(f"specs {len(specs)}")
    done = load_ckpt(CKPT)
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
            rec = run_case(db, spec, catalog)
            slim = {
                "case_id": cid,
                "error": rec.get("error"),
                "elapsed_s": rec.get("elapsed_s"),
                "case": rec.get("case"),
                "exercises": rec.get("exercises") or [],
            }
            append_ckpt(CKPT, slim)
            done[cid] = slim
            cases.append({**rec["case"], **fitness_test_inputs(spec)})
            exercises.extend(
                {**with_suggestion(ex), **fitness_test_inputs(spec)}
                for ex in (rec.get("exercises") or [])
            )
            print(f"[{i}/{len(specs)}] {cid} {rec.get('elapsed_s')}s err={rec.get('error')}")
    finally:
        db.close()
    write_xlsx(cases, exercises, OUT_XLSX)
    print(f"wrote {OUT_XLSX} cases={len(cases)} exercises={len(exercises)}")


if __name__ == "__main__":
    main()
