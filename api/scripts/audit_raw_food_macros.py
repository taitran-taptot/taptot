"""Strip fiber keys from seeds; audit raw macros vs USDA FoodData Central (±5%)."""

from __future__ import annotations

import csv
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

API = Path(__file__).resolve().parents[1]
ROOT = API.parent
sys.path.insert(0, str(API))

from app.services.food_energy import (  # noqa: E402
    SKIP_ENERGY_SLUGS,
    apply_energy_alignment_dict,
    classic_atwater_kcal,
    relative_error,
)

SEEDS = ROOT / "seeds"
TOL = 0.05

# USDA SR Legacy / FoodData Central per 100 g (total carbohydrate, not net).
USDA_BY_SLUG: dict[str, tuple[float, float, float, float, str]] = {
    "uc-ga-khong-da-song": (120, 22.5, 0.0, 2.62, "usda:171077"),
    "dui-ga-khong-da-song": (119, 19.66, 0.0, 3.92, "usda:171079"),
    "ca-hoi-atlantic-song": (208, 20.42, 0.0, 13.42, "usda:173686"),
    "trung-ga-ca-qua-song": (143, 12.56, 0.72, 9.51, "usda:171287"),
    "thit-bo-xay-90-nac-song": (176, 20.0, 0.0, 10.0, "usda:174030"),
    "thit-lon-nac-vai-song": (143, 19.87, 0.0, 6.81, "usda:168255"),
    "ca-chua": (18, 0.88, 3.89, 0.2, "usda:170457"),
    "tao": (52, 0.26, 13.81, 0.17, "usda:171688"),
    "chuoi": (89, 1.09, 22.84, 0.33, "usda:173944"),
    "dua-leo": (15, 0.65, 3.63, 0.11, "usda:169225"),
    "cai-thao": (16, 1.2, 3.23, 0.2, "usda:169995"),
    "bi-ngoi": (17, 1.21, 3.11, 0.32, "usda:169291"),
    "bo": (160, 2.0, 8.53, 14.66, "usda:171705"),
    "rau-muong": (19, 2.6, 3.14, 0.2, "usda:170073"),
    "bap-ngot": (86, 3.27, 18.7, 1.35, "usda:169998"),
    "toi": (149, 6.36, 33.06, 0.5, "usda:169230"),
    "gung": (80, 1.82, 17.77, 0.75, "usda:169231"),
    "sa": (99, 1.82, 25.31, 0.49, "usda:169147"),
    "can-tay": (16, 0.69, 2.97, 0.17, "usda:169988"),
    "toi-tay": (61, 1.5, 14.15, 0.3, "usda:169246"),
    "thi-la": (43, 3.46, 7.02, 1.12, "usda:170419"),
    "tieu-den": (251, 10.39, 63.95, 3.27, "usda:170931"),
    "ot-hiem": (40, 1.87, 8.81, 0.44, "usda:170106"),
    "dau-phong": (587, 23.68, 21.51, 49.66, "usda:174036"),
    "dau-xanh": (347, 23.86, 62.62, 1.15, "usda:174256"),
    "chanh-ta": (30, 0.7, 10.54, 0.2, "usda:168155"),
    "hanh-tim": (72, 2.5, 16.8, 0.1, "usda:170499"),
}
FDC_NUTRIENTS = {
    1008: "kcal",
    2048: "kcal_atwater",
    1003: "protein",
    1004: "fat",
    1005: "carbs",
}

JSON_TARGETS = [
    SEEDS / "foods_catalog_v2.json",
    SEEDS / "grain_nut_foods.json",
    SEEDS / "foods_cooking_pantry.json",
    SEEDS / "foods_traditional_dishes.json",
    SEEDS / "foods_recipe_macros.json",
]


def _drop_fiber(obj):
    if isinstance(obj, dict):
        obj.pop("fiber_g", None)
        obj.pop("fiber_100g", None)
        for value in obj.values():
            _drop_fiber(value)
    elif isinstance(obj, list):
        for item in obj:
            _drop_fiber(item)


def _iter_foods(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        foods = payload.get("foods")
        if isinstance(foods, list):
            return foods
    return []


def _is_raw_ingredient(row: dict) -> bool:
    if not isinstance(row, dict):
        return False
    if str(row.get("food_kind") or "ingredient").lower() == "dish":
        return False
    return str(row.get("prep_state") or "raw").lower() == "raw"


def _f(value, default=0.0) -> float:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _parse_fdc(source_ref: str) -> str | None:
    text = (source_ref or "").strip()
    match = re.fullmatch(r"usda:(\d+)", text)
    return match.group(1) if match else None


def _nutrients_from_fdc(payload: dict) -> dict[str, float] | None:
    found: dict[str, float] = {}
    for item in payload.get("foodNutrients") or []:
        nutrient = item.get("nutrient") or {}
        nid = nutrient.get("id") or item.get("nutrientId")
        amount = item.get("amount")
        if amount is None:
            amount = item.get("value")
        key = FDC_NUTRIENTS.get(int(nid)) if nid is not None else None
        if key and amount is not None:
            found[key] = float(amount)
    kcal = found.get("kcal")
    if kcal is None:
        kcal = found.get("kcal_atwater")
    if kcal is None or "protein" not in found or "carbs" not in found or "fat" not in found:
        return None
    return {
        "kcal": round(kcal, 2),
        "protein": round(found["protein"], 2),
        "carbs": round(found["carbs"], 2),
        "fat": round(found["fat"], 2),
    }


def _get_json(url: str, body: bytes | None = None) -> dict | None:
    req = urllib.request.Request(
        url,
        data=body,
        headers={"User-Agent": "vietfit-db-audit", "Content-Type": "application/json"},
        method="POST" if body else "GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None


def fetch_fdc(fdc_id: str) -> dict[str, float] | None:
    url = f"https://api.nal.usda.gov/fdc/v1/food/{fdc_id}?api_key=DEMO_KEY"
    payload = _get_json(url)
    if not payload:
        return None
    return _nutrients_from_fdc(payload)


def search_fdc(query: str) -> tuple[str, dict[str, float]] | None:
    q = (query or "").strip()
    if not q:
        return None
    url = "https://api.nal.usda.gov/fdc/v1/foods/search?api_key=DEMO_KEY"
    body = json.dumps(
        {
            "query": q,
            "dataType": ["SR Legacy", "Foundation"],
            "pageSize": 5,
            "requireAllWords": False,
        }
    ).encode("utf-8")
    payload = _get_json(url, body)
    if not payload:
        return None
    for food in payload.get("foods") or []:
        desc = str(food.get("description") or "").lower()
        if "raw" not in desc and "fresh" not in desc:
            continue
        parsed = _nutrients_from_fdc(food)
        fdc_id = str(food.get("fdcId") or "")
        if parsed and fdc_id:
            return f"usda:{fdc_id}", parsed
    for food in payload.get("foods") or []:
        parsed = _nutrients_from_fdc(food)
        fdc_id = str(food.get("fdcId") or "")
        if parsed and fdc_id:
            return f"usda:{fdc_id}", parsed
    return None


def within_tol(current: float, source: float) -> bool:
    return relative_error(current, source) <= TOL


def apply_row(row: dict, source: dict[str, float], source_ref: str) -> str:
    cur = {
        "kcal": _f(row.get("kcal_100g")),
        "protein": _f(row.get("protein_100g")),
        "carbs": _f(row.get("carbs_100g")),
        "fat": _f(row.get("fat_100g")),
    }
    keep = all(within_tol(cur[k], source[k]) for k in ("kcal", "protein", "carbs", "fat"))
    if keep:
        if not str(row.get("source_ref") or "").strip():
            row["source_ref"] = source_ref
        action = "kept"
    else:
        row["protein_100g"] = source["protein"]
        row["carbs_100g"] = source["carbs"]
        row["fat_100g"] = source["fat"]
        expected = classic_atwater_kcal(source["protein"], source["carbs"], source["fat"])
        if within_tol(source["kcal"], expected):
            row["kcal_100g"] = source["kcal"]
        else:
            row["kcal_100g"] = round(expected, 2)
        serving = _f(row.get("serving_grams"), 100.0) or 100.0
        scale = serving / 100.0
        row["calories"] = round(_f(row["kcal_100g"]) * scale, 2)
        row["protein_g"] = round(_f(row["protein_100g"]) * scale, 2)
        row["carbs_g"] = round(_f(row["carbs_100g"]) * scale, 2)
        row["fat_g"] = round(_f(row["fat_100g"]) * scale, 2)
        row["source_ref"] = source_ref
        action = "replaced"
    apply_energy_alignment_dict(row)
    return action


def main() -> None:
    for path in JSON_TARGETS:
        if not path.is_file():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        _drop_fiber(payload)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    pantry_gen = SEEDS / "_gen_cooking_pantry.py"
    if pantry_gen.is_file():
        text = pantry_gen.read_text(encoding="utf-8")
        text = re.sub(r", fiber=[0-9.]+", "", text)
        pantry_gen.write_text(text, encoding="utf-8")

    audit_rows: list[dict] = []
    cache: dict[str, dict[str, float] | None] = {}
    for path in (
        SEEDS / "foods_catalog_v2.json",
        SEEDS / "grain_nut_foods.json",
        SEEDS / "foods_cooking_pantry.json",
    ):
        payload = json.loads(path.read_text(encoding="utf-8"))
        foods = _iter_foods(payload)
        changed = False
        for row in foods:
            if not _is_raw_ingredient(row):
                continue
            slug = str(row.get("slug") or "")
            if slug in SKIP_ENERGY_SLUGS:
                apply_energy_alignment_dict(row)
                continue
            fdc_id = _parse_fdc(str(row.get("source_ref") or ""))
            source = None
            source_name = str(row.get("source_ref") or "")
            if slug in USDA_BY_SLUG:
                kcal_s, p_s, c_s, f_s, ref = USDA_BY_SLUG[slug]
                source = {"kcal": kcal_s, "protein": p_s, "carbs": c_s, "fat": f_s}
                source_name = ref
            elif fdc_id:
                if fdc_id not in cache:
                    cache[fdc_id] = fetch_fdc(fdc_id)
                    time.sleep(0.25)
                source = cache[fdc_id]
                source_name = f"usda:{fdc_id}"
            if source is None:
                query = str(row.get("name_en") or row.get("name_vi") or slug)
                cache_key = f"q:{query.lower()}"
                if cache_key not in cache:
                    hit = search_fdc(query)
                    cache[cache_key] = hit
                    time.sleep(0.25)
                hit = cache[cache_key]
                if hit:
                    source_name, source = hit
            action = "review"
            deltas = ""
            if source is None:
                apply_energy_alignment_dict(row)
                if apply_energy_alignment_dict(row):
                    changed = True
                audit_rows.append(
                    {
                        "slug": slug,
                        "file": path.name,
                        "source": source_name or "",
                        "action": "REVIEW",
                        "delta_kcal_pct": "",
                        "delta_p_pct": "",
                        "delta_c_pct": "",
                        "delta_f_pct": "",
                    }
                )
                continue
            before = (
                _f(row.get("kcal_100g")),
                _f(row.get("protein_100g")),
                _f(row.get("carbs_100g")),
                _f(row.get("fat_100g")),
            )
            action = apply_row(row, source, source_name)
            after = (
                _f(row.get("kcal_100g")),
                _f(row.get("protein_100g")),
                _f(row.get("carbs_100g")),
                _f(row.get("fat_100g")),
            )
            if after != before:
                changed = True
            audit_rows.append(
                {
                    "slug": slug,
                    "file": path.name,
                    "source": source_name,
                    "action": action,
                    "delta_kcal_pct": round(100 * relative_error(before[0], source["kcal"]), 2),
                    "delta_p_pct": round(100 * relative_error(before[1], source["protein"]), 2),
                    "delta_c_pct": round(100 * relative_error(before[2], source["carbs"]), 2),
                    "delta_f_pct": round(100 * relative_error(before[3], source["fat"]), 2),
                }
            )
        if changed:
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    csv_path = SEEDS / "RAW_FOODS_SOURCE_AUDIT.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["slug", "file", "source", "action", "delta_kcal_pct", "delta_p_pct", "delta_c_pct", "delta_f_pct"],
        )
        writer.writeheader()
        writer.writerows(audit_rows)
    print(f"wrote {csv_path} ({len(audit_rows)} raw rows)")


if __name__ == "__main__":
    main()
