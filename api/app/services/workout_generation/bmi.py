"""BMI bands (Asia-Pacific cutoffs) and 2-month familiarization calorie cards."""

from __future__ import annotations

from typing import Any

from app.services.workout_generation.nutrition_targets import (
    estimate_targets,
    parse_kg_per_week,
    targets_for_calories,
)

WEIGHT_GOAL_WEEKS = 8
MIN_DAILY_KCAL = {"female": 1200, "male": 1500}

BMI_LABEL_VI: dict[str, str] = {
    "underweight": "Gầy (Thiếu cân)",
    "normal": "Bình thường (Lý tưởng)",
    "overweight": "Tiền béo phì (Thừa cân)",
    "obese_1": "Béo phì độ I",
    "obese_2": "Béo phì độ II+",
}

_HEAVY = frozenset({"obese_1", "obese_2"})
_OVER = frozenset({"overweight", "obese_1", "obese_2"})


def compute_bmi(weight_kg: Any, height_cm: Any) -> float | None:
    try:
        weight = float(weight_kg)
        height = float(height_cm)
    except (TypeError, ValueError):
        return None
    if weight <= 0 or height <= 0:
        return None
    meters = height / 100.0
    if meters <= 0:
        return None
    return round(weight / (meters * meters), 1)


def bmi_band(bmi: float) -> str:
    if bmi < 18.5:
        return "underweight"
    if bmi < 23:
        return "normal"
    if bmi < 25:
        return "overweight"
    if bmi < 30:
        return "obese_1"
    return "obese_2"


def bmi_band_from_payload(payload: dict[str, Any] | None) -> str:
    data = dict(payload or {})
    bmi = compute_bmi(data.get("weight_kg"), data.get("height_cm"))
    if bmi is None:
        return "normal"
    return bmi_band(bmi)


def goal_from_bmi_band(band: str) -> str:
    if band == "underweight":
        return "gain_weight"
    if band == "normal":
        return "maintain"
    return "lose_weight"


def is_heavy_bmi(band: str) -> bool:
    return band in _HEAVY


def is_overweight_bmi(band: str) -> bool:
    return band in _OVER


def _vi_int(value: float | int) -> str:
    return f"{int(round(value)):,}".replace(",", ".")


def _vi_kg(value: float) -> str:
    rounded = round(float(value), 1)
    if rounded == int(rounded):
        return str(int(rounded))
    return str(rounded).replace(".", ",")


def _normalize_gender(raw: Any) -> str:
    return "female" if str(raw or "").strip().lower() == "female" else "male"


def build_familiarization_weight_goal(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    data = dict(payload or {})
    try:
        weight = float(data.get("weight_kg") or 0)
        height = float(data.get("height_cm") or 0)
    except (TypeError, ValueError):
        return None
    bmi = compute_bmi(weight, height)
    if bmi is None or weight < 20 or height < 50:
        return None
    band = bmi_band(bmi)
    goal = goal_from_bmi_band(band)
    gender = _normalize_gender(data.get("gender"))
    meters = height / 100.0

    kg_week = 0.0
    if goal == "lose_weight":
        pct = 0.0075 if band in _HEAVY else 0.005
        kg_week = parse_kg_per_week({**data, "kg_per_week": round(weight * pct * 20) / 20}, goal=goal)
        target_kg = max(30.0, weight - kg_week * WEIGHT_GOAL_WEEKS)
        floor_kg = 18.5 * meters * meters
        target_kg = max(target_kg, min(weight, floor_kg))
    elif goal == "gain_weight":
        kg_week = parse_kg_per_week(data, goal=goal)
        target_kg = weight + kg_week * WEIGHT_GOAL_WEEKS
        cap_kg = 22.9 * meters * meters
        target_kg = min(target_kg, max(weight, cap_kg))
    else:
        target_kg = weight

    target_kg = round(target_kg, 1)
    protein_weight = target_kg if goal == "lose_weight" else weight
    nutrition_payload = {
        **data,
        "goal": goal,
        "kg_per_week": kg_week if kg_week else None,
        "weight_kg": weight,
    }
    targets = estimate_targets(nutrition_payload)
    if targets is None:
        return None
    floor = MIN_DAILY_KCAL[gender]
    daily_kcal = int(targets.target_calories)
    if goal == "lose_weight":
        daily_kcal = max(floor, daily_kcal)
    macros = targets_for_calories(
        targets, goal=goal, weight_kg=protein_weight, target_calories=daily_kcal
    )
    protein_g = int(round(macros.protein_g))
    band_vi = BMI_LABEL_VI[band]
    current_s = _vi_kg(weight)
    target_s = _vi_kg(target_kg)
    kcal_s = _vi_int(daily_kcal)
    protein_s = _vi_int(protein_g)
    target_bmi = round(target_kg / (meters * meters), 1) if meters > 0 else bmi
    bmi_s = _vi_kg(target_bmi)
    if goal == "lose_weight":
        copy_vi = (
            f"BMI {band_vi.lower()}. {current_s} kg — ăn khoảng {kcal_s} kcal/ngày "
            f"(đạm {protein_s} g) để giảm còn khoảng {target_s} kg (BMI {bmi_s}) trong 2 tháng, "
            f"hướng về BMI bình thường 18,5–22,9 với tốc độ an toàn."
        )
    elif goal == "gain_weight":
        copy_vi = (
            f"BMI {band_vi.lower()}. {current_s} kg — ăn khoảng {kcal_s} kcal/ngày "
            f"(đạm {protein_s} g) để tăng lên khoảng {target_s} kg (BMI {bmi_s}) trong 2 tháng, "
            f"hướng về BMI bình thường 18,5–22,9 với tốc độ an toàn."
        )
    else:
        copy_vi = (
            f"BMI {band_vi.lower()}. {current_s} kg — ăn khoảng {kcal_s} kcal/ngày "
            f"(đạm {protein_s} g) để duy trì BMI trong vùng bình thường 18,5–22,9 trong 2 tháng."
        )
    return {
        "bmi": bmi,
        "band": band,
        "band_vi": band_vi,
        "goal": goal,
        "current_kg": round(weight, 1),
        "target_kg": target_kg,
        "target_bmi": target_bmi,
        "weeks": WEIGHT_GOAL_WEEKS,
        "kg_per_week": kg_week,
        "daily_kcal": daily_kcal,
        "protein_g": protein_g,
        "tdee": int(targets.tdee),
        "copy_vi": copy_vi,
    }
