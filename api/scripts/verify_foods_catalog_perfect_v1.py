"""Verify DB against foods_catalog_perfect_v1.xlsx; write error report JSON."""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

API_DIR = Path(__file__).resolve().parents[1]
ROOT = API_DIR.parent
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from app.core.database import SessionLocal
from app.models.entities import Food, FoodCategory
from app.services.food_catalog_perfect_import import (
    ZERO_MACRO_OK,
    default_perfect_xlsx_path,
    load_curated_dish_rows,
    load_perfect_master_rows,
)

KCAL_TOL = 1.0
MACRO_TOL = 0.1
ATWATER_ABS = 25.0
ATWATER_REL = 0.20


def _close(a: float | None, b: float | None, tol: float) -> bool:
    aa = 0.0 if a is None else float(a)
    bb = 0.0 if b is None else float(b)
    return abs(aa - bb) <= tol


def main() -> int:
    xlsx = default_perfect_xlsx_path(ROOT)
    if not xlsx.is_file():
        raise SystemExit(f"missing {xlsx}")

    master = load_perfect_master_rows(xlsx)
    curated = load_curated_dish_rows(xlsx)
    master_by_slug = {r.slug: r for r in master}
    master_by_id = {r.id: r for r in master if r.id is not None}

    report: dict[str, Any] = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "xlsx": str(xlsx),
        "master_rows": len(master),
        "curated_rows": len(curated),
        "db_mismatch": [],
        "macro_mass_over_105": [],
        "atwater_mismatch": [],
        "zero_macro": [],
        "curated_mismatch": [],
        "missing_in_db": [],
        "duplicate_ids_in_xlsx": [],
    }

    # duplicate IDs in xlsx
    seen_ids: dict[int, str] = {}
    for r in master:
        if r.id is None:
            continue
        if r.id in seen_ids:
            report["duplicate_ids_in_xlsx"].append(
                {"id": r.id, "slugs": [seen_ids[r.id], r.slug]}
            )
        else:
            seen_ids[r.id] = r.slug

    with SessionLocal() as db:
        foods = db.query(Food).filter(Food.owner_user_id.is_(None)).all()
        by_slug = {f.slug: f for f in foods}
        by_id = {f.id: f for f in foods}
        cats = {c.id: c for c in db.query(FoodCategory).all()}

        for item in master:
            food = by_slug.get(item.slug) or (by_id.get(item.id) if item.id else None)
            if food is None:
                report["missing_in_db"].append({"slug": item.slug, "id": item.id})
                continue

            diffs: list[dict[str, Any]] = []
            checks = [
                ("calories", item.calories, food.calories, KCAL_TOL),
                ("protein_g", item.protein_g, food.protein_g, MACRO_TOL),
                ("carbs_g", item.carbs_g, food.carbs_g, MACRO_TOL),
                ("fat_g", item.fat_g, food.fat_g, MACRO_TOL),
                ("fiber_g", item.fiber_g, food.fiber_g, MACRO_TOL),
                ("kcal_100g", item.kcal_100g, food.kcal_100g, KCAL_TOL),
                ("protein_100g", item.protein_100g, food.protein_100g, MACRO_TOL),
                ("carbs_100g", item.carbs_100g, food.carbs_100g, MACRO_TOL),
                ("fat_100g", item.fat_100g, food.fat_100g, MACRO_TOL),
                ("fiber_100g", item.fiber_100g, food.fiber_100g, MACRO_TOL),
                ("serving_grams", item.serving_grams, food.serving_grams, MACRO_TOL),
            ]
            for name, expected, actual, tol in checks:
                if not _close(expected, actual, tol):
                    diffs.append(
                        {
                            "field": name,
                            "xlsx": expected,
                            "db": actual,
                        }
                    )
            if (item.prep_state or "") != (food.prep_state or ""):
                diffs.append(
                    {
                        "field": "prep_state",
                        "xlsx": item.prep_state,
                        "db": food.prep_state,
                    }
                )
            if (item.name_vi or "") != (food.name_vi or ""):
                diffs.append(
                    {"field": "name_vi", "xlsx": item.name_vi, "db": food.name_vi}
                )
            cat = cats.get(food.category_id) if food.category_id else None
            if item.group_name and cat and cat.name_vi != item.group_name:
                diffs.append(
                    {
                        "field": "category",
                        "xlsx": item.group_name,
                        "db": cat.name_vi,
                    }
                )
            if diffs:
                report["db_mismatch"].append(
                    {
                        "id": food.id,
                        "slug": food.slug,
                        "name_vi": food.name_vi,
                        "food_kind": food.food_kind,
                        "diffs": diffs,
                    }
                )

            p = float(food.protein_100g or 0)
            c = float(food.carbs_100g or 0)
            f = float(food.fat_100g or 0)
            mass = p + c + f
            if mass > 105:
                report["macro_mass_over_105"].append(
                    {
                        "id": food.id,
                        "slug": food.slug,
                        "name_vi": food.name_vi,
                        "mass_g": round(mass, 2),
                        "protein_100g": p,
                        "carbs_100g": c,
                        "fat_100g": f,
                    }
                )

            kcal = float(food.kcal_100g or 0)
            atw = 4 * p + 4 * c + 9 * f
            if kcal > 0:
                delta = abs(kcal - atw)
                if delta > max(ATWATER_ABS, ATWATER_REL * kcal):
                    report["atwater_mismatch"].append(
                        {
                            "id": food.id,
                            "slug": food.slug,
                            "name_vi": food.name_vi,
                            "kcal_100g": kcal,
                            "atwater": round(atw, 1),
                            "delta": round(kcal - atw, 1),
                        }
                    )

            if (
                food.slug not in ZERO_MACRO_OK
                and kcal == 0
                and p == 0
                and c == 0
                and f == 0
            ):
                report["zero_macro"].append(
                    {
                        "id": food.id,
                        "slug": food.slug,
                        "name_vi": food.name_vi,
                    }
                )

        for cur in curated:
            food = by_id.get(cur.id)
            master_row = master_by_id.get(cur.id)
            entry: dict[str, Any] = {
                "id": cur.id,
                "name_vi": cur.name_vi,
                "issues": [],
            }
            if food is None:
                entry["issues"].append("missing_in_db")
                report["curated_mismatch"].append(entry)
                continue
            if master_row is None:
                entry["issues"].append("missing_in_master")
            else:
                if not _close(cur.calories, master_row.calories, KCAL_TOL):
                    entry["issues"].append(
                        {
                            "field": "calories_master",
                            "curated": cur.calories,
                            "master": master_row.calories,
                        }
                    )
                if not _close(cur.protein_g, master_row.protein_g, MACRO_TOL):
                    entry["issues"].append(
                        {
                            "field": "protein_master",
                            "curated": cur.protein_g,
                            "master": master_row.protein_g,
                        }
                    )
            if not _close(cur.calories, food.calories, KCAL_TOL):
                entry["issues"].append(
                    {
                        "field": "calories_db",
                        "curated": cur.calories,
                        "db": food.calories,
                    }
                )
            if not _close(cur.protein_g, food.protein_g, MACRO_TOL):
                entry["issues"].append(
                    {
                        "field": "protein_db",
                        "curated": cur.protein_g,
                        "db": food.protein_g,
                    }
                )
            if entry["issues"]:
                entry["slug"] = food.slug
                report["curated_mismatch"].append(entry)

    exports = API_DIR / "exports"
    exports.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    out_path = exports / f"perfect_catalog_verify_{stamp}.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    error_counts = {
        k: len(report[k])
        for k in (
            "db_mismatch",
            "macro_mass_over_105",
            "atwater_mismatch",
            "zero_macro",
            "curated_mismatch",
            "missing_in_db",
            "duplicate_ids_in_xlsx",
        )
    }
    total_errors = sum(error_counts.values())
    print(f"wrote {out_path}")
    print("error_counts", error_counts)
    print("total_error_groups", total_errors)

    # Human-readable summary of macro/calo issues
    print("\n=== MACRO / CALO ISSUES ===")
    if not report["macro_mass_over_105"] and not report["atwater_mismatch"] and not report["zero_macro"]:
        print("(none)")
    for row in report["macro_mass_over_105"]:
        print(
            f"[macro>105] {row['slug']} ({row['name_vi']}): "
            f"P+C+F={row['mass_g']}g/100g"
        )
    for row in report["atwater_mismatch"]:
        print(
            f"[atwater] {row['slug']} ({row['name_vi']}): "
            f"kcal_100g={row['kcal_100g']} vs 4P+4C+9F={row['atwater']} "
            f"(delta={row['delta']})"
        )
    for row in report["zero_macro"]:
        print(f"[zero-macro] {row['slug']} ({row['name_vi']})")

    if report["db_mismatch"]:
        print(f"\n=== DB ≠ EXCEL ({len(report['db_mismatch'])}) ===")
        for row in report["db_mismatch"][:40]:
            fields = ", ".join(d["field"] for d in row["diffs"])
            print(f"  {row['slug']}: {fields}")
        if len(report["db_mismatch"]) > 40:
            print(f"  ... and {len(report['db_mismatch']) - 40} more")

    return 1 if total_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
