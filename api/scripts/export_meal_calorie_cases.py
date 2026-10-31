"""Grid of meal-calorie cases and an Excel export. Does not write the app database."""

from __future__ import annotations

import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

API_DIR = Path(__file__).resolve().parents[1]
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from app.services.workout_generation.meal_engine import build_day_templates
from app.services.workout_generation.nutrition_targets import (
    KCAL_PER_KG,
    MAX_SURPLUS_KCAL,
    _kcal_floor,
    estimate_targets,
    phase_calorie_target,
    targets_for_calories,
)

WEEKLY_KG = 0.35
COMPARE_KCAL = 1800
# Heavy work pushes a small person above 1.8 g/kg. That surplus is fine up to this ceiling.
PROTEIN_CEILING_G_PER_KG = 2.3

PEOPLE: tuple[dict[str, Any], ...] = (
    {
        "id": "nu_moc",
        "label": "Nữ mốc 24 tuổi",
        "gender": "female",
        "weight_kg": 60,
        "height_cm": 152,
        "age": 24,
    },
    {
        "id": "nam_cung_so_do",
        "label": "Nam cùng số đo",
        "gender": "male",
        "weight_kg": 60,
        "height_cm": 152,
        "age": 24,
    },
    {
        "id": "nu_60_tuoi",
        "label": "Nữ 60 tuổi",
        "gender": "female",
        "weight_kg": 60,
        "height_cm": 152,
        "age": 60,
    },
    {
        "id": "nu_nhe",
        "label": "Nữ nhẹ",
        "gender": "female",
        "weight_kg": 45,
        "height_cm": 150,
        "age": 22,
    },
    {
        "id": "nam_nhe",
        "label": "Nam nhẹ",
        "gender": "male",
        "weight_kg": 55,
        "height_cm": 165,
        "age": 22,
    },
    {
        "id": "nam_nang",
        "label": "Nam nặng",
        "gender": "male",
        "weight_kg": 100,
        "height_cm": 180,
        "age": 40,
    },
)

LEVELS: tuple[tuple[int, str], ...] = (
    (1, "Người mới bắt đầu"),
    (2, "Đã có thói quen vận động"),
    (3, "Tập hoặc chơi thể thao đều"),
)

ACTIVITIES: tuple[tuple[str, str], ...] = (
    ("sedentary", "Ngồi nhiều — văn phòng, học, lái xe"),
    ("light", "Đứng / đi nhẹ — giáo viên, bán hàng, nội trợ"),
    ("moderate", "Đi lại nhiều — phục vụ, y tá, shipper"),
    ("active", "Lao động chân tay — công trình, kho, nông"),
    ("very_active", "Lao động nặng cả ngày — khuân vác, thợ hồ"),
)

GOALS: tuple[tuple[str, str], ...] = (
    ("lose_weight", "Giảm 5 kg / 100 ngày"),
    ("maintain", "Giữ cân"),
    ("gain_weight", "Tăng 5 kg / 100 ngày"),
)

CASE_HEADERS = [
    "Người",
    "Giới",
    "Tuổi",
    "Cao (cm)",
    "Nặng (kg)",
    "Trình độ",
    "Trình độ (tên)",
    "Số buổi",
    "Phút",
    "Việc ngày",
    "Việc ngày (tên)",
    "Mục tiêu",
    "Mục tiêu (tên)",
    "kg/tuần sau kẹp",
    "BMR",
    "TDEE",
    "Mục tiêu thô",
    "Mục tiêu đã kẹp",
    "Sàn",
    "Trần",
    "kg / 100 ngày nếu ăn đúng",
    "Đối chiếu 1800",
    "Nhận xét",
]

PLATE_HEADERS = [
    "Người",
    "Giới",
    "Tuổi",
    "Cao (cm)",
    "Nặng (kg)",
    "Số buổi",
    "Phút",
    "Việc ngày",
    "Mục tiêu",
    "Mục tiêu đã kẹp",
    "Đạm mục tiêu (g)",
    "Calo đĩa",
    "Lệch calo %",
    "Đạm đĩa (g)",
    "Đạm (g/kg)",
    "Lệch đạm %",
    "Kết quả",
]


def _kg_text(value: float) -> str:
    return f"{value:.2f}".replace(".", ",")


def build_case_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for person in PEOPLE:
        for level, level_vi in LEVELS:
            for minutes in (45, 60):
                for sessions in (2, 4, 6):
                    for activity, activity_vi in ACTIVITIES:
                        for goal, goal_vi in GOALS:
                            rows.append(
                                _case_row(
                                    person,
                                    level=level,
                                    level_vi=level_vi,
                                    minutes=minutes,
                                    sessions=sessions,
                                    activity=activity,
                                    activity_vi=activity_vi,
                                    goal=goal,
                                    goal_vi=goal_vi,
                                )
                            )
    return rows


def _case_row(
    person: dict[str, Any],
    *,
    level: int,
    level_vi: str,
    minutes: int,
    sessions: int,
    activity: str,
    activity_vi: str,
    goal: str,
    goal_vi: str,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "gender": person["gender"],
        "weight_kg": person["weight_kg"],
        "height_cm": person["height_cm"],
        "age": person["age"],
        "activity": activity,
        "goal": goal,
        "experience_level": level,
        "sessions_per_week": sessions,
        "session_minutes": minutes,
    }
    if goal != "maintain":
        payload["kg_per_week"] = WEEKLY_KG
    targets = estimate_targets(payload)
    if targets is None:
        raise RuntimeError(f"Không tính được calo cho {person['id']}")
    gender = person["gender"]
    floor = _kcal_floor(gender, float(targets.bmr))
    ceiling = int(targets.tdee) + MAX_SURPLUS_KCAL
    clamped = phase_calorie_target(
        tdee=targets.tdee,
        full_target=targets.target_calories,
        block_index=0,
        goal=goal,
        bmr=float(targets.bmr),
        gender=gender,
    )
    raw = int(targets.target_calories)
    hit_floor = goal == "lose_weight" and raw < floor and clamped == floor
    hit_ceiling = goal == "gain_weight" and raw > ceiling and clamped == ceiling
    kg_week = float(targets.kg_per_week or 0)
    kg_100 = (clamped - int(targets.tdee)) * 100 / KCAL_PER_KG
    anchor = (
        person["id"] == "nu_moc" and activity == "moderate" and goal == "lose_weight"
    )
    compare = ""
    if anchor:
        kg_at_1800 = (COMPARE_KCAL - int(targets.tdee)) * 100 / KCAL_PER_KG
        compare = (
            f"1800 kcal nằm giữa sàn và TDEE nên an toàn, nhưng chỉ khoảng "
            f"{_kg_text(abs(kg_at_1800))} kg / 100 ngày. Engine đề xuất {clamped} kcal."
        )
    notes: list[str] = []
    rate_changed = goal != "maintain" and abs(kg_week - WEEKLY_KG) > 0.001
    rate_raised = rate_changed and kg_week > WEEKLY_KG
    realized = (int(targets.tdee) - clamped) * 7 / KCAL_PER_KG
    if goal == "gain_weight":
        realized = (clamped - int(targets.tdee)) * 7 / KCAL_PER_KG
    if rate_raised and hit_floor:
        notes.append(
            f"Tốc độ {_kg_text(WEEKLY_KG)} kg/tuần được nâng lên {_kg_text(kg_week)} kg/tuần "
            f"để ra mục tiêu thô. Sàn kéo calo ăn lên. "
            f"Tốc độ thực tế sau sàn khoảng {_kg_text(realized)} kg/tuần."
        )
    elif rate_raised:
        notes.append(
            f"Tốc độ {_kg_text(WEEKLY_KG)} kg/tuần được nâng lên {_kg_text(kg_week)} kg/tuần "
            f"vì dưới mức tối thiểu theo % cân."
        )
    elif hit_floor:
        notes.append(
            f"Mục tiêu thô dưới sàn, đã nâng calo lên sàn. "
            f"Tốc độ thực tế khoảng {_kg_text(realized)} kg/tuần."
        )
    elif rate_changed:
        notes.append(
            f"Tốc độ {_kg_text(WEEKLY_KG)} kg/tuần được hạ xuống {_kg_text(kg_week)} kg/tuần "
            f"vì vượt mức tối đa theo % cân."
        )
    if hit_ceiling:
        notes.append("Mục tiêu thô vượt trần TDEE+500, đã hạ xuống trần.")
    if compare:
        notes.append(compare)
    if not notes:
        if goal == "maintain":
            notes.append("Ăn đúng TDEE.")
        elif goal == "lose_weight":
            notes.append("Thâm hụt nằm trong sàn và TDEE.")
        else:
            notes.append("Thặng dư nằm trong TDEE và trần +500.")
    return {
        "person_id": person["id"],
        "person": person["label"],
        "gender": "Nữ" if gender == "female" else "Nam",
        "gender_key": gender,
        "age": person["age"],
        "height_cm": person["height_cm"],
        "weight_kg": person["weight_kg"],
        "level": level,
        "level_vi": level_vi,
        "sessions": sessions,
        "minutes": minutes,
        "activity": activity,
        "activity_vi": activity_vi,
        "goal": goal,
        "goal_vi": goal_vi,
        "kg_week": round(kg_week, 2),
        "bmr": int(targets.bmr),
        "tdee": int(targets.tdee),
        "raw_target": raw,
        "clamped": int(clamped),
        "floor": floor,
        "ceiling": ceiling,
        "kg_100": round(kg_100, 2),
        "compare_1800": compare,
        "note": " ".join(notes),
        "hit_floor": hit_floor,
        "hit_ceiling": hit_ceiling,
    }


def plate_sources(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One plate per person × activity × goal × sessions × minutes. Level stays at 2."""
    chosen: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for row in rows:
        if row["level"] != 2:
            continue
        key = (row["person_id"], row["activity"], row["goal"], row["sessions"], row["minutes"])
        if key in seen:
            continue
        seen.add(key)
        chosen.append(row)
    return chosen


def build_plate_row(case: dict[str, Any], pool: list[Any]) -> dict[str, Any]:
    payload = {
        "gender": case["gender_key"],
        "weight_kg": case["weight_kg"],
        "height_cm": case["height_cm"],
        "age": case["age"],
        "activity": case["activity"],
        "goal": case["goal"],
    }
    if case["goal"] != "maintain":
        payload["kg_per_week"] = case["kg_week"] or WEEKLY_KG
    base = estimate_targets(payload)
    if base is None:
        raise RuntimeError(f"Không tính được đĩa cho {case['person_id']}")
    served = targets_for_calories(
        base,
        goal=case["goal"],
        weight_kg=float(case["weight_kg"]),
        target_calories=int(case["clamped"]),
    )
    template = build_day_templates(
        pool, served, count=1, weight_kg=float(case["weight_kg"])
    )[0]
    plate_kcal = float(template.totals["calories"])
    plate_protein = float(template.totals["protein_g"])
    kcal_pct = abs(plate_kcal - served.target_calories) / served.target_calories * 100
    prot_den = served.protein_g or 1
    prot_pct = abs(plate_protein - served.protein_g) / prot_den * 100
    weight = float(case["weight_kg"])
    short_limit = 0.05 if weight < 50 or weight > 90 else 0.12
    short = plate_protein < served.protein_g * (1 - short_limit)
    over_ceiling = plate_protein > PROTEIN_CEILING_G_PER_KG * weight
    ok = kcal_pct <= 10 and not short and not over_ceiling
    return {
        **case,
        "protein_target": served.protein_g,
        "plate_kcal": round(plate_kcal, 1),
        "kcal_pct": round(kcal_pct, 1),
        "plate_protein": round(plate_protein, 1),
        "protein_g_per_kg": round(plate_protein / weight, 2),
        "prot_pct": round(prot_pct, 1),
        "plate_ok": ok,
        "plate_result": "khớp" if ok else "lệch",
    }


def schedule_tdee_groups(rows: list[dict[str, Any]]) -> tuple[int, int]:
    """Groups where sessions or minutes change TDEE, and groups where only level does."""
    by_person: dict[tuple[str, str, str], set[int]] = {}
    by_level: dict[tuple[Any, ...], set[int]] = {}
    for row in rows:
        by_person.setdefault((row["person_id"], row["activity"], row["goal"]), set()).add(row["tdee"])
        by_level.setdefault(
            (row["person_id"], row["activity"], row["goal"], row["sessions"], row["minutes"]),
            set(),
        ).add(row["tdee"])
    schedule_breaks = sum(1 for values in by_person.values() if len(values) > 1)
    level_breaks = sum(1 for values in by_level.values() if len(values) > 1)
    return schedule_breaks, level_breaks


def _case_values(row: dict[str, Any]) -> list[Any]:
    return [
        row["person"],
        row["gender"],
        row["age"],
        row["height_cm"],
        row["weight_kg"],
        row["level"],
        row["level_vi"],
        row["sessions"],
        row["minutes"],
        row["activity"],
        row["activity_vi"],
        row["goal"],
        row["goal_vi"],
        row["kg_week"],
        row["bmr"],
        row["tdee"],
        row["raw_target"],
        row["clamped"],
        row["floor"],
        row["ceiling"],
        row["kg_100"],
        row["compare_1800"],
        row["note"],
    ]


def _plate_values(row: dict[str, Any]) -> list[Any]:
    return [
        row["person"],
        row["gender"],
        row["age"],
        row["height_cm"],
        row["weight_kg"],
        row["sessions"],
        row["minutes"],
        row["activity_vi"],
        row["goal_vi"],
        row["clamped"],
        row["protein_target"],
        row["plate_kcal"],
        row["kcal_pct"],
        row["plate_protein"],
        row["protein_g_per_kg"],
        row["prot_pct"],
        row["plate_result"],
    ]


def _write_sheet(ws, headers: list[str], data: list[list[Any]]) -> None:
    header_fill = PatternFill("solid", fgColor="1F4E79")
    header_font = Font(bold=True, color="FFFFFF")
    for col, title in enumerate(headers, start=1):
        cell = ws.cell(1, col, title)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(wrap_text=True, vertical="center")
    for r, values in enumerate(data, start=2):
        for c, value in enumerate(values, start=1):
            ws.cell(r, c, value)
    ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{len(data) + 1}"
    ws.freeze_panes = "A2"
    ws.row_dimensions[1].height = 30
    for col in range(1, len(headers) + 1):
        letter = get_column_letter(col)
        width = 18
        if headers[col - 1] in {"Nhận xét", "Đối chiếu 1800", "Việc ngày (tên)", "Trình độ (tên)"}:
            width = 42
        ws.column_dimensions[letter].width = width


def write_workbook(rows: list[dict[str, Any]], plates: list[dict[str, Any]], path: Path) -> None:
    anchor = next(
        row
        for row in rows
        if row["person_id"] == "nu_moc"
        and row["activity"] == "moderate"
        and row["goal"] == "lose_weight"
        and row["sessions"] == 4
        and row["minutes"] == 45
        and row["level"] == 2
    )
    floor_n = sum(1 for row in rows if row["hit_floor"])
    ceiling_n = sum(1 for row in rows if row["hit_ceiling"])
    schedule_breaks, level_breaks = schedule_tdee_groups(rows)
    summary = [
        ("Số dòng ca", len(rows)),
        ("Số đĩa", len(plates)),
        ("Dòng chạm sàn", floor_n),
        ("Dòng chạm trần TDEE+500", ceiling_n),
        ("Nhóm người/việc/mục tiêu mà buổi hoặc phút đổi TDEE", schedule_breaks),
        ("Nhóm mà chỉ trình độ đổi TDEE", level_breaks),
        ("Ca mốc — TDEE", anchor["tdee"]),
        ("Ca mốc — mục tiêu đã kẹp", anchor["clamped"]),
        ("Ca mốc — đối chiếu 1800", anchor["compare_1800"]),
    ]
    wb = Workbook()
    cases = wb.active
    cases.title = "Ca"
    _write_sheet(cases, CASE_HEADERS, [_case_values(row) for row in rows])
    plate_ws = wb.create_sheet("Đĩa ăn")
    _write_sheet(plate_ws, PLATE_HEADERS, [_plate_values(row) for row in plates])
    summary_ws = wb.create_sheet("Tóm tắt")
    _write_sheet(summary_ws, ["Mục", "Giá trị"], summary)
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)


def export_workbook(path: Path | None = None) -> Path:
    from tests.test_meal_engine import _realistic_pool

    rows = build_case_rows()
    plates = [build_plate_row(row, _realistic_pool()) for row in plate_sources(rows)]
    if path is None:
        stamp = datetime.now().strftime("%Y%m%d_%H%M")
        path = API_DIR / "exports" / f"meal_calorie_cases_{stamp}.xlsx"
    write_workbook(rows, plates, path)
    desktop = Path.home() / "Desktop"
    desktop.mkdir(parents=True, exist_ok=True)
    copy_path = desktop / path.name
    shutil.copy2(path, copy_path)
    print(f"{len(rows)} cases, {len(plates)} plates")
    print(path)
    print(copy_path)
    return path


def main() -> None:
    export_workbook()


if __name__ == "__main__":
    main()
