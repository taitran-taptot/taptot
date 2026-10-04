"""Apply food-catalog audit cleanup (fiber, zero-macro fish, units, dishes, prep).

Idempotent; safe to run on every startup after traditional-dish / catalog seeds.
"""

from __future__ import annotations

from app.services.food_energy import apply_energy_alignment_dict, apply_energy_alignment_food

__all__ = [
    "AUDIT_FOOD_MERGES",
    "NUTRIENT_100G_PATCHES",
    "PREP_STATE_PATCHES",
    "apply_energy_alignment_dict",
    "apply_energy_alignment_food",
    "correct_inflated_dish_serving",
    "scale_serving_from_100g",
    "serving_to_100g",
]

# Per-100g patches (VN table / label truth). Keys are food slugs.
NUTRIENT_100G_PATCHES: dict[str, dict[str, float | str | None]] = {
    # Zero-macro sea fish → Bảng TPDD Việt Nam (approx. edible portion).
    "ca-bac-ma": {
        "kcal_100g": 106,
        "protein_100g": 19.8,
        "carbs_100g": 0,
        "fat_100g": 3.0,
        "fiber_100g": 0,
        "serving_size": "100g",
        "serving_grams": 100,
        "prep_state": "raw",
        "confidence": "reference",
    },
    "ca-ho": {
        "kcal_100g": 98,
        "protein_100g": 19.5,
        "carbs_100g": 0,
        "fat_100g": 2.2,
        "fiber_100g": 0,
        "serving_size": "100g",
        "serving_grams": 100,
        "prep_state": "raw",
        "confidence": "reference",
    },
    "ca-moi": {
        "kcal_100g": 100,
        "protein_100g": 18.5,
        "carbs_100g": 0,
        "fat_100g": 2.8,
        "fiber_100g": 0,
        "serving_size": "100g",
        "serving_grams": 100,
        "prep_state": "raw",
        "confidence": "reference",
    },
    "ca-ngan": {
        "kcal_100g": 95,
        "protein_100g": 18.2,
        "carbs_100g": 0,
        "fat_100g": 2.0,
        "fiber_100g": 0,
        "serving_size": "100g",
        "serving_grams": 100,
        "prep_state": "raw",
        "confidence": "reference",
    },
    "ca-nuc-bong": {
        "kcal_100g": 115,
        "protein_100g": 20.0,
        "carbs_100g": 0,
        "fat_100g": 3.5,
        "fiber_100g": 0,
        "serving_size": "100g",
        "serving_grams": 100,
        "prep_state": "raw",
        "confidence": "reference",
    },
    # Scoop values were stored as if 100g.
    "whey-protein-isolate": {
        "kcal_100g": 380,
        "protein_100g": 88.0,
        "carbs_100g": 3.0,
        "fat_100g": 1.5,
        "fiber_100g": 0,
        "serving_size": "1 muỗng (~30g)",
        "serving_grams": 30,
        "prep_state": "processed",
        "confidence": "reference",
    },
    "whey-protein-concentrate": {
        "kcal_100g": 400,
        "protein_100g": 78.0,
        "carbs_100g": 8.0,
        "fat_100g": 5.0,
        "fiber_100g": 0,
        "serving_size": "1 muỗng (~30g)",
        "serving_grams": 30,
        "prep_state": "processed",
        "confidence": "reference",
    },
    # Whole-egg row was 1 quả (~50g) stored as 100g.
    "trung-ga-ca-qua-song": {
        "kcal_100g": 143,
        "protein_100g": 12.6,
        "carbs_100g": 0.7,
        "fat_100g": 9.5,
        "fiber_100g": 0,
        "serving_size": "1 quả (~50g)",
        "serving_grams": 50,
        "prep_state": "raw",
        "confidence": "reference",
    },
    # Yolk was 1 lòng đỏ (~17g) stored as 100g.
    "long-do-trung-ga": {
        "kcal_100g": 322,
        "protein_100g": 15.9,
        "carbs_100g": 3.6,
        "fat_100g": 26.5,
        "fiber_100g": 0,
        "serving_size": "1 lòng đỏ (~17g)",
        "serving_grams": 17,
        "prep_state": "raw",
        "confidence": "reference",
    },
    # 1 chiếc nem (~45g) realistic fried spring roll (not inverse-scaled scoop).
    "nem-ran-cha-gio-chien": {
        "kcal_100g": 244,
        "protein_100g": 11.1,
        "carbs_100g": 20.0,
        "fat_100g": 14.4,
        "fiber_100g": 1.5,
        "serving_size": "1 chiếc vừa (~45g)",
        "serving_grams": 45,
        "prep_state": "cooked",
        "confidence": "estimated",
    },
    # Macro mass slightly over 100g — soft rescale to physical limit.
    "banh-tet-nhan-thit-dau-xanh": {
        "kcal_100g": 500,
        "protein_100g": 13.1,
        "carbs_100g": 67.7,
        "fat_100g": 19.2,
        "fiber_100g": 0.6,
        "serving_size": "1 khoanh (~150g)",
        "serving_grams": 150,
        "prep_state": "cooked",
        "confidence": "estimated",
    },
}

PREP_STATE_PATCHES = {
    "dau-phong": "cooked",
    "cha-trung": "cooked",
    "banh-trang": "processed",
}

# usda short slug → excel longer canonical slug (same 100g macros).
AUDIT_FOOD_MERGES = {
    "bi-ngoi": "bi-ngoi-xanh-zucchini",
    "cam": "cam-sanh",
    "chuoi": "chuoi-tieu-chuoi-tay",
    "le": "le-mac-cop",
    "nam-bao-ngu": "nam-bao-ngu-so",
    "nhan": "nhan-long",
    "nho": "nho-do-ninh-thuan",
    "quyt": "quyt-duong-quyt-tieu",
    "rau-chan-vit-cai-bo-xoi": "cai-bo-xoi-bina",
    "roi-man": "roi-man-do-an-phuoc",
    "tao": "tao-tay-envy-fuji",
    "vai": "vai-thieu-luc-ngan",
    "bo": "bo-sap",
    # Piece-as-100g egg row → reference whole egg.
    "trung-ga": "trung-ga-ca-qua-song",
}


def scale_serving_from_100g(
    *,
    kcal_100g: float,
    protein_100g: float,
    carbs_100g: float,
    fat_100g: float,
    fiber_100g: float | None,
    serving_grams: float,
) -> dict[str, float | None]:
    scale = serving_grams / 100.0
    return {
        "calories": round(kcal_100g * scale, 2),
        "protein_g": round(protein_100g * scale, 2),
        "carbs_g": round(carbs_100g * scale, 2),
        "fat_g": round(fat_100g * scale, 2),
        "fiber_g": None if fiber_100g is None else round(float(fiber_100g) * scale, 2),
    }


def correct_inflated_dish_serving(
    *,
    calories: float,
    protein_g: float,
    carbs_g: float,
    fat_g: float,
    fiber_g: float | None,
    serving_grams: float,
) -> dict[str, float | None] | None:
    """Scale traditional bowls whose protein was ~3–4× clinical reality.

    Trigger on severe protein inflation (typical phở/bún errors), not on
    recipe-BOM meals that are merely calorie-dense (e.g. bún chả).
    Returns None when no correction needed.
    """
    # Only rewrite clearly absurd single-serving protein (phở/bún ~90–110g).
    # Leave recipe-BOM plates in the 45–70g band (e.g. cơm tấm sườn bì chả).
    if protein_g <= 70:
        return None

    # Anchor protein to a standard meat-noodle bowl (~28g from 70–100g meat).
    factor = 28.0 / protein_g
    cal = round(calories * factor, 1)
    p = round(protein_g * factor, 1)
    c = round(carbs_g * factor, 1)
    f = round(fat_g * factor, 1)
    fib = None if fiber_g is None else round(float(fiber_g) * factor, 2)

    # After protein scale, nudge calories into 450–650 if still extreme.
    if cal > 700:
        factor2 = 600.0 / cal
        cal = round(cal * factor2, 1)
        p = round(p * factor2, 1)
        c = round(c * factor2, 1)
        f = round(f * factor2, 1)
        if fib is not None:
            fib = round(fib * factor2, 2)
    elif serving_grams >= 350 and cal < 420:
        factor2 = 450.0 / cal if cal > 0 else 1.0
        cal = round(cal * factor2, 1)
        p = round(p * factor2, 1)
        c = round(c * factor2, 1)
        f = round(f * factor2, 1)
        if fib is not None:
            fib = round(fib * factor2, 2)

    if serving_grams >= 300 and f > 32:
        delta = f - 28.0
        f = 28.0
        cal = round(max(cal - 9.0 * delta, 0), 1)

    return {
        "calories": cal,
        "protein_g": p,
        "carbs_g": c,
        "fat_g": f,
        "fiber_g": fib,
    }


def serving_to_100g(
    *,
    calories: float,
    protein_g: float,
    carbs_g: float,
    fat_g: float,
    fiber_g: float | None,
    serving_grams: float,
) -> dict[str, float | None]:
    scale = 100.0 / serving_grams if serving_grams else 0.0
    return {
        "kcal_100g": round(calories * scale, 2),
        "protein_100g": round(protein_g * scale, 2),
        "carbs_100g": round(carbs_g * scale, 2),
        "fat_100g": round(fat_g * scale, 2),
        "fiber_100g": None if fiber_g is None else round(float(fiber_g) * scale, 2),
    }
