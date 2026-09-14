from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.entities import CalculatorLog, UserProfile


ACTIVITY_MULTIPLIERS = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "active": 1.725,
    "very_active": 1.9,
}

GOAL_ADJUSTMENTS = {
    "lose_weight": -500,
    "maintain": 0,
    "gain_muscle": 300,
}


class CalculatorService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def bmi(self, weight_kg: float, height_cm: float) -> dict[str, Any]:
        if height_cm <= 0 or weight_kg <= 0:
            raise ValueError("Invalid height or weight")
        height_m = height_cm / 100
        bmi = round(weight_kg / (height_m * height_m), 1)
        category = self._bmi_category(bmi)
        return {"bmi": bmi, "category_vi": category}

    def tdee(
        self,
        *,
        gender: str,
        weight_kg: float,
        height_cm: float,
        age: int,
        activity_level: str,
        goal: str = "maintain",
    ) -> dict[str, Any]:
        bmr = self._bmr(gender, weight_kg, height_cm, age)
        multiplier = ACTIVITY_MULTIPLIERS.get(activity_level, 1.375)
        tdee = int(bmr * multiplier)
        target = tdee + GOAL_ADJUSTMENTS.get(goal, 0)
        return {
            "bmr": int(bmr),
            "tdee": tdee,
            "target_calories": max(target, 1),
            "activity_level": activity_level,
            "goal": goal,
        }

    def macros(self, target_calories: int, weight_kg: float, goal: str = "maintain") -> dict[str, int]:
        if goal == "lose_weight":
            protein_g = int(weight_kg * 2.0)
            fat_g = int(weight_kg * 0.8)
        elif goal == "gain_muscle" or goal == "gain_weight":
            protein_g = int(weight_kg * 2.2)
            fat_g = int(weight_kg * 1.0)
        else:
            protein_g = int(weight_kg * 1.8)
            fat_g = int(weight_kg * 0.9)

        protein_cal = protein_g * 4
        fat_cal = fat_g * 9
        carbs_cal = max(target_calories - protein_cal - fat_cal, 0)
        carbs_g = int(carbs_cal / 4)
        return {
            "target_calories": target_calories,
            "protein_g": protein_g,
            "carbs_g": carbs_g,
            "fat_g": fat_g,
        }

    def calculate_and_log(
        self,
        calculator_type: str,
        input_data: dict[str, Any],
        user_id: str | None = None,
    ) -> dict[str, Any]:
        if calculator_type == "bmi":
            result = self.bmi(input_data["weight_kg"], input_data["height_cm"])
        elif calculator_type == "tdee":
            result = self.tdee(**input_data)
        elif calculator_type == "macros":
            result = self.macros(
                input_data["target_calories"],
                input_data["weight_kg"],
                input_data.get("goal", "maintain"),
            )
        elif calculator_type == "full":
            tdee = self.tdee(**input_data)
            macros = self.macros(tdee["target_calories"], input_data["weight_kg"], input_data.get("goal", "maintain"))
            bmi = self.bmi(input_data["weight_kg"], input_data["height_cm"])
            result = {**tdee, **macros, **bmi}
        else:
            raise ValueError(f"Unknown calculator: {calculator_type}")

        log = CalculatorLog(
            user_id=user_id,
            calculator_type=calculator_type,
            input_data=input_data,
            result_data=result,
            created_at=datetime.now(UTC),
        )
        self.db.add(log)

        if user_id:
            profile = self.db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
            if profile and calculator_type in ("tdee", "full"):
                profile.tdee = result.get("tdee")
                profile.target_calories = result.get("target_calories")
                profile.target_protein_g = result.get("protein_g")
                profile.target_carbs_g = result.get("carbs_g")
                profile.target_fat_g = result.get("fat_g")
                profile.updated_at = datetime.now(UTC)

        self.db.commit()
        return result

    def _bmr(self, gender: str, weight_kg: float, height_cm: float, age: int) -> float:
        if gender == "female":
            return 10 * weight_kg + 6.25 * height_cm - 5 * age - 161
        return 10 * weight_kg + 6.25 * height_cm - 5 * age + 5

    def _bmi_category(self, bmi: float) -> str:
        if bmi < 18.5:
            return "Thiếu cân"
        if bmi < 23:
            return "Bình thường"
        if bmi < 25:
            return "Thừa cân"
        return "Béo phì"
