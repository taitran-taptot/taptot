"""720 wizard cases of the 100-day challenge -> Excel. Does not write plans.

Grid: 3 kits x 2 genders x 3 levels x 5 sessions (2-6) x 2 minutes (45, 60)
x 2 goals (lose, gain) x 2 focus (empty, chest) = 720.

Each case calls generate_workout(persist=False), then the same 14-week
expansion and generate_meals_with_blocks the persist path uses. create_plan
is never called.

Resume: docs/testing/challenge-100-ui-cases.ckpt.jsonl (one JSON object per case).
Output: docs/testing/challenge-100-ui-cases.xlsx
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import shutil
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
API = ROOT / "api"
if str(API) not in sys.path:
    sys.path.insert(0, str(API))

from openpyxl import Workbook
from openpyxl.cell import WriteOnlyCell
from openpyxl.styles import Font, PatternFill

from app.core.database import SessionLocal
from app.schemas.plans import PlanDayIn
from app.services.periodization import expand_plan_days_for_weeks
from app.services.workout_generation.meal_engine import (
    _active_complete_meals,
    _ai_safe_pool,
    generate_meals_with_blocks,
    infer_roles,
    load_meal_pool,
    pool_is_ready,
)
from app.services.workout_generation.nutrition_targets import (
    BLOCK_SIZE_WEEKS,
    parse_kg_per_week,
)
from app.services.workout_generation.service import generate_workout
from app.services.workout_generation.session_policy import (
    CHALLENGE_PHASE_RANGES,
)

OUT_XLSX = ROOT / "docs" / "testing" / "challenge-100-ui-cases.xlsx"
CKPT = ROOT / "docs" / "testing" / "challenge-100-ui-cases.ckpt.jsonl"
MIN_FREE_BYTES = 1_500_000_000

KITS = ("resistance-band", "dumbbell", "bar-and-rings")
GENDERS = ("male", "female")
LEVELS = (1, 2, 3)
SESSIONS = (2, 3, 4, 5, 6)
MINUTES = (45, 60)
GOALS = ("lose_weight", "gain_weight")
FOCUSES: tuple[tuple[str, ...], ...] = ((), ("nguc",))
DELOAD_WEEKS = {4, 8, 14}

PROFILES = {
    "male": {"age": 25, "height_cm": 170.0, "weight_kg": 70.0, "activity": "moderate"},
    "female": {"age": 25, "height_cm": 160.0, "weight_kg": 55.0, "activity": "moderate"},
}

GENDER_VI = {"male": "Nam", "female": "Nữ"}
GOAL_VI = {"lose_weight": "Giảm cân", "gain_weight": "Tăng cân"}
ACTIVITY_VI = {"moderate": "Vận động vừa"}
MEAL_VI = {
    "breakfast": "Sáng",
    "lunch": "Trưa",
    "dinner": "Tối",
    "snack": "Phụ",
}

CASE_HEADERS = [
    "case_id",
    "kit",
    "gioi",
    "tuoi",
    "chieu_cao_cm",
    "can_nang_kg",
    "van_dong",
    "level",
    "muc_tieu",
    "kg_tuan",
    "phut_xin",
    "phut_thuc",
    "focus",
    "buoi_xin",
    "buoi_thuc",
    "week_code",
    "test_day",
    "test_keo",
    "test_chan",
    "food_ids",
    "tdee",
    "kcal_muc_tieu",
    "protein_g",
    "carb_g",
    "fat_g",
    "so_bua",
    "rule_ids",
    "error",
]
EX_HEADERS = [
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
    "set_chi_tiet",
]
MEAL_HEADERS = [
    "case_id",
    "tuan",
    "loai",
    "buoi",
    "bua",
    "ten",
    "phan",
    "kcal",
    "protein_g",
    "carb_g",
    "fat_g",
]
RULE_HEADERS = ["rule_id", "nhom", "khi_input", "engine_lam", "ghi_chu_qa"]

_WEEK_RE = re.compile(r"Tuần\s+(\d+)", re.IGNORECASE)
_PHA_RE = re.compile(r"Pha\s+(\d+)", re.IGNORECASE)
_GRAM_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*g\b", re.IGNORECASE)


def _kit_export():
    path = API / "scripts" / "export_kit_load_cases_xlsx.py"
    spec = importlib.util.spec_from_file_location("kit_load_export", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Không đọc được {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _free_bytes(path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    return int(shutil.disk_usage(path.parent).free)


def pick_food_ids(db) -> list[int]:
    """At least two protein, two starch, two veg, plus one dish when the catalog has one."""
    pool = _ai_safe_pool(db)
    need = {"protein": 2, "carb": 2, "produce": 2}
    got = {role: 0 for role in need}
    chosen: list[Any] = []
    seen: set[int] = set()
    for food in pool:
        roles = infer_roles(food)
        for role, count in need.items():
            if got[role] >= count or int(food.id) in seen or role not in roles:
                continue
            chosen.append(food)
            seen.add(int(food.id))
            got[role] += 1
            break
    if any(got[role] < count for role, count in need.items()):
        raise SystemExit(f"Kho thức ăn chưa đủ nhóm wizard: {got}")
    dishes = _active_complete_meals(db)
    if dishes:
        dish = sorted(dishes, key=lambda food: int(food.id))[0]
        if int(dish.id) not in seen:
            chosen.append(dish)
            seen.add(int(dish.id))
    ids = [int(food.id) for food in chosen]
    loaded, used_ai = load_meal_pool(db, {"ai_suggest_foods": False, "food_ids": ids})
    if used_ai or not pool_is_ready(loaded):
        ids = [fid for fid in ids if fid != (int(dishes[0].id) if dishes else -1)]
        loaded, used_ai = load_meal_pool(db, {"ai_suggest_foods": False, "food_ids": ids})
        if used_ai or not pool_is_ready(loaded):
            raise SystemExit("Pool món không đủ để gửi food_ids như wizard.")
    return ids


def iter_specs(food_ids: list[int]) -> list[dict[str, Any]]:
    kit = _kit_export()
    specs: list[dict[str, Any]] = []
    for kit_name in KITS:
        for gender in GENDERS:
            profile = PROFILES[gender]
            for level in LEVELS:
                baseline = kit.baseline_for(kit_name, gender, level, "ok")
                for sessions in SESSIONS:
                    for minutes in MINUTES:
                        for goal in GOALS:
                            payload_seed = {
                                "goal": goal,
                                "gender": gender,
                                "weight_kg": profile["weight_kg"],
                            }
                            kg = parse_kg_per_week(payload_seed, goal=goal)
                            for focus in FOCUSES:
                                focus_tag = focus[0] if focus else "trong"
                                case_id = (
                                    f"ui-{kit_name}-{gender}-l{level}-s{sessions}"
                                    f"-m{minutes}-{goal}-{focus_tag}"
                                )
                                specs.append(
                                    {
                                        "case_id": case_id,
                                        "kit": kit_name,
                                        "gender": gender,
                                        "level": level,
                                        "sessions": sessions,
                                        "minutes": minutes,
                                        "goal": goal,
                                        "focus": list(focus),
                                        "baseline": baseline,
                                        "kg_per_week": kg,
                                        "food_ids": list(food_ids),
                                        **profile,
                                    }
                                )
    return specs


def _payload(spec: dict[str, Any], kit_mod) -> dict[str, Any]:
    return {
        "goal": spec["goal"],
        "gender": spec["gender"],
        "age": spec["age"],
        "height_cm": spec["height_cm"],
        "weight_kg": spec["weight_kg"],
        "activity": spec["activity"],
        "sessions_per_week": spec["sessions"],
        "session_minutes": spec["minutes"],
        "location": "home",
        "focus_areas": list(spec["focus"]),
        "equipment_list": kit_mod.equipment_for(spec["kit"]),
        "food_ids": list(spec["food_ids"]),
        "experience_level": spec["level"],
        "ai_suggest_foods": False,
        "fitness_baseline": dict(spec["baseline"]),
        "duration_weeks": 14,
        "kg_per_week": spec["kg_per_week"],
        "challenge_100_days": True,
    }


def _rule_ids(spec: dict[str, Any], sessions_actual: int) -> str:
    gender = spec["gender"]
    ids = [
        "WEEKS-14",
        "MINUTES-SNAP",
        "DELOAD",
        "KIT-ONE",
        "NUT-FORMULA",
        "NUT-FLOOR-OPEN",
        "MEAL-PORTION",
        "MEAL-SUM",
        f"SPLIT-{gender}-{sessions_actual}",
    ]
    if spec["kit"] == "resistance-band":
        ids.append("LOAD-BAND")
    elif spec["kit"] == "dumbbell":
        ids.append("LOAD-DB")
    else:
        ids.append("LOAD-BAR")
    if int(spec["sessions"]) != int(sessions_actual):
        ids.append("CLAMP-BEGINNER")
    if spec["goal"] == "gain_weight":
        ids.append("NUT-GAIN-CAP-OPEN")
    if spec["focus"]:
        ids.append("FOCUS-CHEST")
    else:
        ids.append("FOCUS-NONE")
    return ",".join(ids)


def _template_days(result: dict[str, Any]) -> list[PlanDayIn]:
    insights = result.get("insights") or {}
    raw = insights.get("week_templates") or []
    days: list[Any] = []
    if raw and isinstance(raw[0], dict):
        days = list(raw[0].get("a") or [])
    if not days:
        days = list(result.get("days") or [])
    out: list[PlanDayIn] = []
    for index, day in enumerate(days, start=1):
        if not isinstance(day, dict):
            continue
        out.append(
            PlanDayIn(
                day_number=int(day.get("day_number") or index),
                title_vi=day.get("title_vi"),
                split_role=day.get("split_role"),
                notes_vi=day.get("notes_vi"),
            )
        )
    return out


def _week_phase(day: dict[str, Any], sessions: int, kit_mod) -> tuple[int, int]:
    title = str(day.get("title_vi") or "")
    week_match = _WEEK_RE.search(title)
    if week_match:
        week = int(week_match.group(1))
    else:
        week = kit_mod._week_of(int(day.get("day_number") or 1), sessions)
    phase_match = _PHA_RE.search(title)
    phase = int(phase_match.group(1)) if phase_match else kit_mod._phase_of(week)
    return week, phase


def _set_detail(ex: dict[str, Any]) -> str:
    prescriptions = ex.get("set_prescriptions") or []
    if not isinstance(prescriptions, list) or len(prescriptions) < 2:
        return ""
    parts: list[str] = []
    for index, item in enumerate(prescriptions, start=1):
        if not isinstance(item, dict):
            continue
        reps = str(item.get("reps") or "")
        note = str(item.get("load_note_vi") or "")
        parts.append(f"{index}:{reps}|{note}")
    bodies = {part.split(":", 1)[-1] for part in parts}
    if len(bodies) <= 1:
        return ""
    return " ; ".join(parts)


def _exercise_rows(
    spec: dict[str, Any],
    days: list[dict[str, Any]],
    sessions: int,
    catalog: dict[int, dict[str, Any]],
    kit_mod,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for day in days:
        week, phase = _week_phase(day, sessions, kit_mod)
        session_in_week = ((int(day.get("day_number") or 1) - 1) % max(1, sessions)) + 1
        for ex in day.get("exercises") or []:
            if not isinstance(ex, dict):
                continue
            cooked = kit_mod.with_suggestion(
                {
                    "case_id": spec["case_id"],
                    "tuan": week,
                    "pha": phase,
                    "buoi": session_in_week,
                    "split": day.get("split_role") or "",
                    "section": ex.get("section") or "main",
                    "ten": kit_mod._exercise_name(ex, catalog),
                    "sets": ex.get("sets"),
                    "reps": ex.get("reps"),
                    "rest": ex.get("rest_seconds"),
                    "goi_y": kit_mod._load_note(ex),
                    "notes_vi": kit_mod._notes(ex),
                    "set_chi_tiet": _set_detail(ex),
                }
            )
            rows.append({header: cooked.get(header, "") for header in EX_HEADERS})
    return rows


def _parse_grams(serving_size: Any) -> float | None:
    if not serving_size:
        return None
    match = _GRAM_RE.search(str(serving_size))
    if not match:
        return None
    try:
        return float(match.group(1).replace(",", "."))
    except ValueError:
        return None


def _portion(meal: dict[str, Any], food: Any) -> str:
    kind = ""
    complete = False
    if food is not None:
        kind = str(getattr(food, "food_kind", "") or "")
        complete = bool(getattr(food, "is_complete_meal", False))
    kind = kind or str(meal.get("food_kind") or "")
    complete = complete or bool(meal.get("is_complete_meal"))
    if complete or kind.lower() == "dish":
        return "1 suất"
    grams = meal.get("serving_grams")
    if grams in (None, "") and food is not None:
        grams = getattr(food, "serving_grams", None)
    if grams in (None, ""):
        grams = _parse_grams(meal.get("serving_size") or (getattr(food, "serving_size", None) if food else None))
    try:
        grams_f = float(grams) if grams not in (None, "") else 0.0
    except (TypeError, ValueError):
        grams_f = 0.0
    servings = float(meal.get("servings") or 1)
    if grams_f > 0 and servings > 0:
        rounded = int(round((servings * grams_f) / 5.0) * 5)
        if rounded <= 0:
            rounded = 5
        return f"≈ {rounded}g"
    size = str(meal.get("serving_size") or (getattr(food, "serving_size", "") if food else "") or "").strip()
    if size:
        return size
    calories = meal.get("calories")
    if calories not in (None, ""):
        return f"~{int(round(float(calories)))} calo"
    return ""


def _meal_numbers(meal: dict[str, Any], food: Any) -> tuple[int, Any, Any, Any]:
    servings = float(meal.get("servings") or 1)
    if food is not None and meal.get("calories") in (None, ""):
        kcal = int(round(float(food.calories or 0) * servings))
        protein = float(food.protein_g or 0) * servings
        carbs = float(food.carbs_g or 0) * servings
        fat = float(food.fat_g or 0) * servings
        return kcal, round(protein, 1), round(carbs, 1), round(fat, 1)
    kcal = int(round(float(meal.get("calories") or 0)))
    def _num(key: str) -> Any:
        raw = meal.get(key)
        if raw in (None, ""):
            return ""
        return round(float(raw), 1)
    return kcal, _num("protein_g"), _num("carbs_g"), _num("fat_g")


def _meal_rows(case_id: str, blocks: list[dict[str, Any]], foods: dict[int, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    def emit(week: int, kind: str, session_no: Any, meals: list[dict[str, Any]]) -> None:
        for meal in meals:
            if not isinstance(meal, dict):
                continue
            try:
                food_id = int(meal.get("food_id"))
            except (TypeError, ValueError):
                continue
            food = foods.get(food_id)
            name = meal.get("name_vi") or (getattr(food, "name_vi", None) if food else None) or str(food_id)
            kcal, protein, carbs, fat = _meal_numbers(meal, food)
            slot = str(meal.get("meal_type") or "")
            rows.append(
                {
                    "case_id": case_id,
                    "tuan": week,
                    "loai": kind,
                    "buoi": session_no,
                    "bua": MEAL_VI.get(slot, slot),
                    "ten": name,
                    "phan": _portion(meal, food),
                    "kcal": kcal,
                    "protein_g": protein,
                    "carb_g": carbs,
                    "fat_g": fat,
                }
            )

    for block in blocks:
        weeks = [int(week) for week in (block.get("weeks") or [])]
        for week in weeks:
            use_deload = week in DELOAD_WEEKS and bool(block.get("deload_sessions"))
            sessions = (block.get("deload_sessions") if use_deload else block.get("sessions")) or []
            for index, session in enumerate(sessions, start=1):
                emit(week, "Tập", index, list(session.get("meals") or []))
            emit(week, "Nghỉ", "", list(block.get("rest_day_meals") or []))
    return rows


def _case_row(
    spec: dict[str, Any],
    *,
    sessions_actual: Any,
    week_code: str,
    minutes_actual: Any,
    insights: dict[str, Any] | None,
    meal_count: Any,
    tests: dict[str, str],
    error: str,
) -> dict[str, Any]:
    nutrition = (insights or {}).get("nutrition") or {}
    actual = sessions_actual if sessions_actual != "" else spec["sessions"]
    return {
        "case_id": spec["case_id"],
        "kit": spec["kit"],
        "gioi": GENDER_VI[spec["gender"]],
        "tuoi": spec["age"],
        "chieu_cao_cm": spec["height_cm"],
        "can_nang_kg": spec["weight_kg"],
        "van_dong": ACTIVITY_VI.get(spec["activity"], spec["activity"]),
        "level": spec["level"],
        "muc_tieu": GOAL_VI[spec["goal"]],
        "kg_tuan": spec["kg_per_week"],
        "phut_xin": spec["minutes"],
        "phut_thuc": minutes_actual,
        "focus": "+".join(spec["focus"]),
        "buoi_xin": spec["sessions"],
        "buoi_thuc": sessions_actual,
        "week_code": week_code,
        "test_day": tests.get("test_day", ""),
        "test_keo": tests.get("test_keo", ""),
        "test_chan": tests.get("test_chan", ""),
        "food_ids": ",".join(str(fid) for fid in spec["food_ids"]),
        "tdee": nutrition.get("tdee", ""),
        "kcal_muc_tieu": nutrition.get("target_calories", ""),
        "protein_g": nutrition.get("protein_g", ""),
        "carb_g": nutrition.get("carbs_g", ""),
        "fat_g": nutrition.get("fat_g", ""),
        "so_bua": meal_count,
        "rule_ids": _rule_ids(spec, int(actual)),
        "error": error,
    }


def _meal_count(rows: list[dict[str, Any]]) -> Any:
    first = [row for row in rows if row["tuan"] == 1 and row["loai"] == "Tập" and row["buoi"] == 1]
    if not first:
        return ""
    return len({row["bua"] for row in first})


def run_case(db, spec: dict[str, Any], catalog: dict[int, dict[str, Any]], kit_mod) -> dict[str, Any]:
    payload = _payload(spec, kit_mod)
    tests = kit_mod.fitness_test_inputs(spec)
    try:
        result = generate_workout(db, None, payload, persist=False, commit=False)
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        return {
            "case_id": spec["case_id"],
            "ok": False,
            "error": str(exc),
            "case": _case_row(
                spec,
                sessions_actual="",
                week_code="",
                minutes_actual="",
                insights=None,
                meal_count="",
                tests=tests,
                error=str(exc),
            ),
            "exercises": [],
            "meals": [],
        }
    insights = result.get("insights") or {}
    sessions = int(result.get("sessions_actual") or spec["sessions"])
    week_code = str(result.get("week_code") or insights.get("week_code") or "")
    seed = [day for day in (result.get("days") or []) if isinstance(day, dict)]
    try:
        expanded = expand_plan_days_for_weeks(
            seed,
            14,
            is_dict=True,
            experience_level=spec["level"],
            strength_tier=insights.get("strength_tier"),
            week_templates=insights.get("week_templates"),
            curriculum=True,
            goal=spec["goal"],
        )
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        return {
            "case_id": spec["case_id"],
            "ok": False,
            "error": f"expand: {exc}",
            "case": _case_row(
                spec,
                sessions_actual=sessions,
                week_code=week_code,
                minutes_actual=result.get("session_minutes", ""),
                insights=insights,
                meal_count="",
                tests=tests,
                error=f"expand: {exc}",
            ),
            "exercises": [],
            "meals": [],
        }
    exercises = _exercise_rows(spec, expanded, sessions, catalog, kit_mod)
    meal_error = ""
    meals: list[dict[str, Any]] = []
    try:
        template = _template_days(result)
        blocks = []
        if template:
            from app.services.workout_generation.nutrition_targets import build_nutrition_blocks

            blocks = build_nutrition_blocks(
                payload,
                goal=spec["goal"],
                duration_weeks=14,
                split_roles=[day.split_role for day in template],
                block_size=BLOCK_SIZE_WEEKS,
                week_ranges=CHALLENGE_PHASE_RANGES,
                experience_level=int(insights.get("effective_level") or spec["level"]),
            )
        if blocks and template:
            meal_result = generate_meals_with_blocks(
                db,
                payload,
                blocks,
                template,
                goal=spec["goal"],
                block_size=4,
                include_deload_meals=True,
            )
            meals = _meal_rows(
                spec["case_id"],
                list(meal_result.nutrition_blocks or []),
                dict(meal_result.foods_by_id or {}),
            )
        else:
            meal_error = "Không có khối dinh dưỡng."
    except Exception as exc:  # noqa: BLE001
        meal_error = f"meals: {exc}"
        meals = []
    finally:
        db.rollback()
    return {
        "case_id": spec["case_id"],
        "ok": meal_error == "" and bool(exercises) and bool(meals),
        "error": meal_error,
        "case": _case_row(
            spec,
            sessions_actual=sessions,
            week_code=week_code,
            minutes_actual=result.get("session_minutes", ""),
            insights=insights,
            meal_count=_meal_count(meals),
            tests=tests,
            error=meal_error,
        ),
        "exercises": exercises,
        "meals": meals,
    }


def load_done(path: Path) -> set[str]:
    done: set[str] = set()
    if not path.is_file():
        return done
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get("ok") and row.get("case_id"):
                done.add(str(row["case_id"]))
    return done


def append_ckpt(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        handle.flush()


def rules_rows() -> list[dict[str, str]]:
    """What the engine does today, including the unclamped floor and surplus."""
    rows = [
        (
            "WEEKS-14",
            "Tuần",
            "Thử thách 100 ngày",
            "Luôn giãn 14 tuần. duration_weeks gửi 14. Tuần chia 3 pha: 1–4, 5–8, 9–14.",
        ),
        (
            "MINUTES-SNAP",
            "Phút",
            "Wizard chỉ có 45 và 60",
            "snap_session_minutes kẹp 45–60 rồi chọn mốc gần nhất trong (45, 60). 45 và 60 giữ nguyên.",
        ),
        (
            "CLAMP-BEGINNER",
            "Buổi",
            "Level 1 hoặc sức yếu, xin hơn 5 buổi",
            "SessionPolicy người mới max_sessions = 5. Xin 6 buổi được lưu 5 buổi. Nam 5 buổi là PPLUL, nữ 5 buổi là LULU, Cardio-Core. Level 2–3 không bị kẹp này.",
        ),
        (
            "SPLIT-male-2",
            "Split",
            "Nam, 2 buổi thực",
            "Mã tuần UL.",
        ),
        (
            "SPLIT-male-3",
            "Split",
            "Nam, 3 buổi thực",
            "Mã tuần PPL.",
        ),
        (
            "SPLIT-male-4",
            "Split",
            "Nam, 4 buổi thực",
            "Mã tuần ULUL.",
        ),
        (
            "SPLIT-male-5",
            "Split",
            "Nam, 5 buổi thực",
            "Mã tuần PPLUL. Level 1 xin 6 buổi rơi vào mã này.",
        ),
        (
            "SPLIT-male-6",
            "Split",
            "Nam, 6 buổi thực",
            "Mã tuần PPLPPL.",
        ),
        (
            "SPLIT-female-2",
            "Split",
            "Nữ, 2 buổi thực",
            "Mã tuần Lower, Upper.",
        ),
        (
            "SPLIT-female-3",
            "Split",
            "Nữ, 3 buổi thực",
            "Mã tuần LUL.",
        ),
        (
            "SPLIT-female-4",
            "Split",
            "Nữ, 4 buổi thực",
            "Mã tuần LPPL.",
        ),
        (
            "SPLIT-female-5",
            "Split",
            "Nữ, 5 buổi thực",
            "Mã tuần LULU, Cardio-Core.",
        ),
        (
            "SPLIT-female-6",
            "Split",
            "Nữ, 6 buổi thực",
            "Mã tuần Lower, Upper lặp 6 buổi.",
        ),
        (
            "DELOAD",
            "Deload",
            "Mọi case",
            "Tuần 4, 8, 14 là deload. Bài đã có từ 2 set trở lên còn max(2, round(set × 0.6)). Bài 1 set giữ 1. Nghỉ × 1.15 với level 1–2, × 1.20 với level 3, rồi trần 180 và làm tròn thang 0, 30, 45, 60, 90, 120, 150, 180 (nghỉ cooldown 20 giây giữ 20). Tiêu đề buổi có chữ Deload. Ghi chú bài chính có câu tập nhẹ.",
        ),
        (
            "LOAD-BAND",
            "Tải",
            "Kit dây",
            "Màu làm việc theo test đẩy/kéo/squat. Rep dưới 10 lùi 1 màu, 10–20 giữ, trên 20 tiến 1, trên 30 tiến 2; sau bước đó rep hiệu chỉnh về 15. Level 1 hạ thêm một màu trước bước phụ trợ. Phụ trợ lùi thêm. Ống vàng cộng chỉ khi màu làm việc vẫn đen, test bắt đầu đen, không phải phụ trợ, và rep test trên 20. Mục tiêu, phút, focus, tuổi, cân nặng không đổi màu dây.",
        ),
        (
            "LOAD-DB",
            "Tải",
            "Kit tạ đơn",
            "Kg gợi ý lấy từ test đẩy, kéo, goblet của đúng slot, rồi progress_db_prescription. Mục tiêu, phút, focus, tuổi, cân nặng không đổi kg.",
        ),
        (
            "LOAD-BAR",
            "Tải",
            "Kit xà và vòng",
            "Bài thân trọng theo test chống đẩy, kéo xà, squat. Kéo xà chỉ vào lịch khi test kéo đủ mạnh. Không gắn bài tạ đơn và không gắn chèo ngược trên bàn.",
        ),
        (
            "KIT-ONE",
            "Dụng cụ",
            "Wizard chọn đúng một kit",
            "Mỗi case một danh sách dụng cụ: dây, hoặc tạ đơn, hoặc xà và vòng. Không trộn kit.",
        ),
        (
            "FOCUS-NONE",
            "Focus",
            "Không chọn vùng",
            "focus_areas rỗng. Lịch không ưu tiên thêm một vùng.",
        ),
        (
            "FOCUS-CHEST",
            "Focus",
            "Chọn ngực",
            "focus_areas = [nguc]. Wizard cho tối đa 3 vùng; lưới này chỉ lấy trống và ngực.",
        ),
        (
            "NUT-FORMULA",
            "Calo",
            "Mọi case",
            "BMR Mifflin. TDEE = int(BMR × hệ số vận động vừa 1.55) cộng kcal tập trung bình ngày (buổi × phút × MET 5 × cân / 60 / 7, làm tròn). Giảm cân trừ, tăng cân cộng round(kg/tuần × 7700 / 7). Đạm 1.8 g/kg khi giảm, 2.0 g/kg khi tăng, rồi kẹp 1.6–2.0 g/kg. Béo khoảng 20–30% năng lượng. Carb là phần còn lại, có sàn carb. estimate_targets đặt 4 bữa nếu target ≥ 1800, không thì 3. Thực đơn chỉ thêm bữa phụ khi pool có món trái cây; cột so_bua đếm số bữa đã ráp ở buổi 1 tuần 1. Pool của file này không có trái cây nên so_bua là 3. kg/tuần gửi lên là mặc định engine: giảm khoảng 0.75% cân, tăng khoảng 0.5% cân, làm tròn 0.05 kg và kẹp trong biên phần trăm.",
        ),
        (
            "NUT-FLOOR-OPEN",
            "Calo",
            "Mọi case, thấy rõ khi cắt sâu",
            "Cột kcal_muc_tieu là estimate_targets: target = max(1, TDEE + điều chỉnh). Hàm này không kẹp sàn max(BMR, 1200 kcal nữ / 1500 kcal nam). Sàn đó chỉ nằm trong phase_calorie_target, và phase_calorie_target mới được khối thực đơn dùng. Vì vậy cột case có thể thấp hơn sàn, trong khi khẩu phần bữa ăn của một ca cắt sâu thì bị kẹp.",
        ),
        (
            "NUT-GAIN-CAP-OPEN",
            "Calo",
            "Tăng cân",
            "estimate_targets không trần thặng dư 500 kcal. kg/tuần cao có thể đẩy kcal_muc_tieu vượt TDEE + 500. phase_calorie_target mới trần khối thực đơn ở TDEE + 500. Cột case ghi số chưa trần.",
        ),
        (
            "MEAL-PORTION",
            "Phần ăn",
            "Mọi món",
            "Món dish hoặc is_complete_meal hiển thị 1 suất. Món chưa chế biến có gram hiển thị ≈ {gram}g, làm tròn 5 g. Không ghi đơn vị nhà bếp và không ghi số suất nhân gram. Ngoài food_ids đã chọn, engine vẫn ghép mọi món dish đang active vào pool, nên một bữa chính trong ngày có thể là 1 suất.",
        ),
        (
            "MEAL-SUM",
            "Phần ăn",
            "Mỗi ngày tập và mỗi ngày nghỉ",
            "Kcal trên từng dòng là kcal của đúng phần đó. Tổng kcal một ngày là tổng các dòng, không làm tròn lên mốc 50. Ngày tập và ngày nghỉ trong cùng khối có thể khác nhau vì món khác nhau, dù target lịch đặt cùng mức.",
        ),
    ]
    return [
        {"rule_id": rule_id, "nhom": group, "khi_input": when, "engine_lam": what, "ghi_chu_qa": ""}
        for rule_id, group, when, what in rows
    ]


def _header(ws, headers: list[str]) -> None:
    fill = PatternFill(start_color="FF1F4E3D", end_color="FF1F4E3D", fill_type="solid")
    font = Font(bold=True, color="FFFFFFFF")
    cells = []
    for header in headers:
        cell = WriteOnlyCell(ws, value=header)
        cell.fill = fill
        cell.font = font
        cells.append(cell)
    ws.append(cells)


def _latest_rows(path: Path) -> list[dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            cid = str(row.get("case_id") or "")
            if not cid:
                continue
            if cid not in latest:
                order.append(cid)
            latest[cid] = row
    return [latest[cid] for cid in order]


def write_xlsx(path: Path, ckpt: Path) -> dict[str, int]:
    rows = _latest_rows(ckpt)
    wb = Workbook(write_only=True)
    cases = wb.create_sheet("Cases")
    exercises = wb.create_sheet("Exercises")
    meals = wb.create_sheet("Meals")
    rules = wb.create_sheet("Rules")
    _header(cases, CASE_HEADERS)
    _header(exercises, EX_HEADERS)
    _header(meals, MEAL_HEADERS)
    _header(rules, RULE_HEADERS)
    for rule in rules_rows():
        rules.append([rule.get(header, "") for header in RULE_HEADERS])
    counts = {"cases": 0, "exercises": 0, "meals": 0, "rules": len(rules_rows())}
    for row in rows:
        case = row.get("case") or {}
        cases.append([case.get(header, "") for header in CASE_HEADERS])
        counts["cases"] += 1
        for exercise in row.get("exercises") or []:
            exercises.append([exercise.get(header, "") for header in EX_HEADERS])
            counts["exercises"] += 1
        for meal in row.get("meals") or []:
            meals.append([meal.get(header, "") for header in MEAL_HEADERS])
            counts["meals"] += 1
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)
    return counts


def _sets(exercise: dict[str, Any]) -> int | None:
    try:
        return int(exercise.get("sets"))
    except (TypeError, ValueError):
        return None


def verify(rows: list[dict[str, Any]]) -> list[str]:
    problems: list[str] = []
    ok_rows = [row for row in rows if row.get("ok")]
    if len(ok_rows) != 720:
        problems.append(f"Cases ok = {len(ok_rows)}, cần 720")
    if not any(row.get("exercises") for row in ok_rows):
        problems.append("Exercises rỗng")
    if not any(row.get("meals") for row in ok_rows):
        problems.append("Meals rỗng")

    def find(**want: Any) -> dict[str, Any] | None:
        for row in ok_rows:
            case = row.get("case") or {}
            if all(case.get(key) == value for key, value in want.items()):
                return row
        return None

    male3 = find(gioi="Nam", level=2, buoi_xin=3, kit="dumbbell", phut_xin=45, muc_tieu="Giảm cân", focus="")
    female3 = find(gioi="Nữ", level=2, buoi_xin=3, kit="dumbbell", phut_xin=45, muc_tieu="Giảm cân", focus="")
    clamped = find(gioi="Nam", level=1, buoi_xin=6, kit="dumbbell", phut_xin=45, muc_tieu="Giảm cân", focus="")
    if male3 is None or (male3.get("case") or {}).get("week_code") != "PPL":
        problems.append(f"Nam 3 buổi không ra PPL: {(male3 or {}).get('case')}")
    if female3 is None or (female3.get("case") or {}).get("week_code") != "LUL":
        problems.append(f"Nữ 3 buổi không ra LUL: {(female3 or {}).get('case')}")
    if clamped is None:
        problems.append("Thiếu case nam level 1 xin 6 buổi")
    else:
        case = clamped.get("case") or {}
        if case.get("buoi_thuc") != 5 or case.get("week_code") != "PPLUL":
            problems.append(f"Level 1 xin 6 không còn 5 buổi PPLUL: {case.get('buoi_thuc')} {case.get('week_code')}")

    sample = male3 or (ok_rows[0] if ok_rows else None)
    if sample:
        week3: dict[tuple[Any, Any, Any], int] = {}
        week4_drop = False
        week4_note = False
        for exercise in sample.get("exercises") or []:
            if int(exercise.get("tuan") or 0) == 4 and "tập nhẹ" in str(exercise.get("notes_vi") or "").lower():
                week4_note = True
            if str(exercise.get("section") or "") != "main":
                continue
            key = (exercise.get("buoi"), exercise.get("ten"), exercise.get("section"))
            sets = _sets(exercise)
            if sets is None:
                continue
            if int(exercise.get("tuan") or 0) == 3:
                week3[key] = sets
            elif int(exercise.get("tuan") or 0) == 4 and key in week3 and sets < week3[key]:
                week4_drop = True
        if not week4_drop:
            problems.append(f"Tuần 4 không giảm set so với tuần 3 ở {(sample.get('case') or {}).get('case_id')}")
        if not week4_note:
            problems.append("Tuần 4 không có ghi chú tập nhẹ")

    gram = False
    dish = False
    for row in ok_rows:
        for meal in row.get("meals") or []:
            portion = str(meal.get("phan") or "")
            if portion.startswith("≈ ") and portion.endswith("g"):
                gram = True
            if portion == "1 suất":
                dish = True
            if gram and dish:
                break
        if gram and dish:
            break
    if not gram:
        problems.append("Không thấy phần gram dạng ≈ Ng")
    if not dish:
        problems.append("Không thấy món 1 suất")
    return problems


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="Chỉ chạy N case đầu, để thử.")
    parser.add_argument("--skip-xlsx", action="store_true")
    args = parser.parse_args()

    free = _free_bytes(OUT_XLSX)
    print(f"free_bytes={free}", flush=True)
    if free < MIN_FREE_BYTES:
        raise SystemExit(f"Đĩa còn {free} byte, dưới {MIN_FREE_BYTES}. Dừng để khỏi đầy đĩa.")

    kit_mod = _kit_export()
    kit_mod._install_name_cache()
    db = SessionLocal()
    try:
        food_ids = pick_food_ids(db)
        print(f"food_ids={food_ids}", flush=True)
        specs = iter_specs(food_ids)
        if args.limit:
            specs = specs[: args.limit]
        print(f"specs={len(specs)}", flush=True)
        catalog = kit_mod.load_catalog(db)
        done = load_done(CKPT)
        started = time.perf_counter()
        for index, spec in enumerate(specs, start=1):
            if spec["case_id"] in done:
                if index % 50 == 0 or index == len(specs):
                    print(f"[{index}/{len(specs)}] skip", flush=True)
                continue
            t0 = time.perf_counter()
            row = run_case(db, spec, catalog, kit_mod)
            append_ckpt(CKPT, row)
            print(
                f"[{index}/{len(specs)}] {spec['case_id']} ok={row.get('ok')} "
                f"ex={len(row.get('exercises') or [])} meals={len(row.get('meals') or [])} "
                f"{time.perf_counter() - t0:.1f}s",
                flush=True,
            )
        print(f"generate_s={time.perf_counter() - started:.1f}", flush=True)
    finally:
        db.close()

    if args.skip_xlsx:
        return
    if args.limit:
        print("skip xlsx because --limit", flush=True)
        return
    counts = write_xlsx(OUT_XLSX, CKPT)
    print(f"xlsx={OUT_XLSX} counts={counts}", flush=True)
    problems = verify(_latest_rows(CKPT))
    if problems:
        print("VERIFY_FAIL", flush=True)
        for problem in problems:
            print(problem, flush=True)
        raise SystemExit(1)
    print("VERIFY_OK", flush=True)


if __name__ == "__main__":
    main()
