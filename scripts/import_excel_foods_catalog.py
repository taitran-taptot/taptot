# -*- coding: utf-8 -*-
"""Parse CSDL Excel → seed JSON + optional wipe/reimport into Postgres.

Usage:
  python scripts/import_excel_foods_catalog.py              # generate seeds only
  python scripts/import_excel_foods_catalog.py --import-db  # generate + wipe/import DB
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEEDS = ROOT / "seeds"
DEFAULT_EXCEL = Path(
    r"c:\Users\Tran Tai\Downloads\CSDL_Dinh_Duong_Toan_Dien_Thuc_Pham_Viet_Nam (3).xlsx"
)
SOURCE_REF = "excel:csdl-dinh-duong-vn-2026"

SHEET_META: list[dict] = [
    {
        "sheet": "1_Rau_Cu_Qua",
        "slug": "rau-cu-qua",
        "name_vi": "Rau - Củ - Quả",
        "sort_order": 1,
        "food_kind": "ingredient",
        "prep_state": "raw",
        "macro_roles": ["produce"],
        "meal_slots": ["breakfast", "lunch", "dinner", "snack"],
        "confidence": "reference",
        "per_100g": True,
        "ai_eligible": True,
        "ai_priority": 40,
        "is_complete_meal": False,
    },
    {
        "sheet": "2_Thit_GiaSuc_GiaCam_NoiTang",
        "slug": "thit-gia-cam-noi-tang",
        "name_vi": "Thịt - Gia cầm - Nội tạng",
        "sort_order": 2,
        "food_kind": "ingredient",
        "prep_state": "raw",
        "macro_roles": ["protein"],
        "meal_slots": ["breakfast", "lunch", "dinner"],
        "confidence": "reference",
        "per_100g": True,
        "ai_eligible": True,
        "ai_priority": 80,
        "is_complete_meal": False,
    },
    {
        "sheet": "3_Ca_ThuyHaiSan",
        "slug": "ca-thuy-hai-san",
        "name_vi": "Cá & Thủy hải sản",
        "sort_order": 3,
        "food_kind": "ingredient",
        "prep_state": "raw",
        "macro_roles": ["protein"],
        "meal_slots": ["lunch", "dinner"],
        "confidence": "reference",
        "per_100g": True,
        "ai_eligible": True,
        "ai_priority": 75,
        "is_complete_meal": False,
    },
    {
        "sheet": "6_Trung_Sua_Whey",
        "slug": "trung-whey",
        "name_vi": "Trứng & Whey",
        "sort_order": 4,
        "food_kind": "ingredient",
        "prep_state": "raw",
        "macro_roles": ["protein", "dairy"],
        "meal_slots": ["breakfast", "snack", "lunch", "dinner"],
        "confidence": "reference",
        "per_100g": True,
        "ai_eligible": True,
        "ai_priority": 70,
        "is_complete_meal": False,
    },
    {
        "sheet": "4_Mon_An_Truyen_Thong",
        "slug": "mon-an-truyen-thong",
        "name_vi": "Món truyền thống",
        "sort_order": 5,
        "food_kind": "dish",
        "prep_state": "cooked",
        "macro_roles": ["carb", "protein"],
        "meal_slots": ["lunch", "dinner"],
        "confidence": "estimated",
        "per_100g": False,
        "ai_eligible": True,
        "ai_priority": 25,
        "is_complete_meal": True,
    },
    {
        "sheet": "5_An_Vat_Banh_Keo_DoUong",
        "slug": "an-vat-do-uong",
        "name_vi": "Ăn vặt - Bánh kẹo - Đồ uống",
        "sort_order": 6,
        "food_kind": "packaged",
        "prep_state": None,
        "macro_roles": ["carb"],
        "meal_slots": ["snack"],
        "confidence": "estimated",
        "per_100g": False,
        "ai_eligible": False,
        "ai_priority": 5,
        "is_complete_meal": False,
    },
]


def slugify(text: str) -> str:
    s = unicodedata.normalize("NFD", text.strip().lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.replace("đ", "d").replace("Đ", "d")
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s[:80] or "food"


def parse_number(value) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, datetime):
        # Excel mis-parsed small integers as dates → day-of-month is the number
        return float(value.day)
    if isinstance(value, str):
        text = value.strip().replace(",", ".")
        if not text or text.lower() in {"null", "none", "-", "n/a"}:
            return None
        m = re.match(
            r"^([+-]?\d+(?:\.\d+)?)\s*[-–—]\s*([+-]?\d+(?:\.\d+)?)$",
            text,
        )
        if m:
            a, b = float(m.group(1)), float(m.group(2))
            return round((a + b) / 2.0, 2)
        m2 = re.search(r"[+-]?\d+(?:\.\d+)?", text)
        if m2:
            return float(m2.group(0))
    return None


def unique_slug(base: str, used: set[str]) -> str:
    slug = base
    i = 2
    while slug in used:
        slug = f"{base}-{i}"
        i += 1
    used.add(slug)
    return slug


def build_aliases(name: str) -> list[str]:
    aliases: list[str] = []
    if "/" in name:
        for part in re.split(r"[/|]", name):
            p = part.strip()
            if p and p.lower() != name.lower():
                aliases.append(p)
    # drop parenthetical clarifications as secondary alias stem
    no_paren = re.sub(r"\([^)]*\)", "", name).strip()
    if no_paren and no_paren.lower() != name.lower():
        aliases.append(no_paren)
    # unique preserve order
    out: list[str] = []
    seen: set[str] = set()
    for a in aliases:
        key = a.lower()
        if key not in seen:
            seen.add(key)
            out.append(a)
    return out[:8]


def parse_excel(excel_path: Path) -> tuple[list[dict], list[dict], list[dict]]:
    import openpyxl

    wb = openpyxl.load_workbook(excel_path, data_only=True)
    categories = [
        {"slug": m["slug"], "name_vi": m["name_vi"], "sort_order": m["sort_order"]}
        for m in SHEET_META
    ]
    foods: list[dict] = []
    aliases_rows: list[dict] = []
    used_slugs: set[str] = set()

    for meta in SHEET_META:
        ws = wb[meta["sheet"]]
        for row in ws.iter_rows(min_row=4, values_only=True):
            stt, group, name = row[0], row[1], row[2]
            if name is None or stt is None:
                continue
            name_vi = str(name).strip()
            if not name_vi:
                continue
            group_vi = str(group).strip() if group else "Khác"
            serving_label = str(row[3]).strip() if row[3] else ("100g" if meta["per_100g"] else "1 phần")

            kcal = parse_number(row[4]) or 0.0
            carbs = parse_number(row[5]) or 0.0
            protein = parse_number(row[6]) or 0.0
            fat = parse_number(row[7]) or 0.0
            # fiber column index differs: ingredients sheets have fiber at [8];
            # trung-whey sheet has no fiber (index 8 is authenticity)
            fiber = None
            if meta["sheet"] not in {"6_Trung_Sua_Whey"}:
                fiber = parse_number(row[8])

            notes = None
            # last descriptive column often at index 11 or 10
            for idx in (11, 10, 9):
                if idx < len(row) and isinstance(row[idx], str) and row[idx].strip():
                    notes = row[idx].strip()
                    break

            group_slug = slugify(group_vi) or "khac"
            food_slug = unique_slug(slugify(name_vi), used_slugs)
            tags = [
                f"nhom:{group_slug}",
                f"nhom_vi:{group_vi}",
            ]
            if meta["food_kind"] == "dish":
                tags.extend(["viet-nam", "complete_meal"])

            aliases = build_aliases(name_vi)

            if meta["per_100g"]:
                serving_size = "100g"
                serving_grams = 100.0
                calories = round(kcal, 2)
                protein_g = round(protein, 2)
                carbs_g = round(carbs, 2)
                fat_g = round(fat, 2)
                fiber_g = round(fiber, 2) if fiber is not None else None
                kcal_100g = calories
                protein_100g = protein_g
                carbs_100g = carbs_g
                fat_100g = fat_g
                fiber_100g = fiber_g
                portions = [
                    {
                        "label_vi": "100g",
                        "grams": 100.0,
                        "is_default": True,
                        "sort_order": 0,
                    }
                ]
            else:
                serving_size = serving_label[:120]
                # estimate grams from label if possible
                gm = re.search(r"(\d+(?:[.,]\d+)?)\s*g", serving_label, re.I)
                serving_grams = float(gm.group(1).replace(",", ".")) if gm else 400.0
                calories = round(kcal, 2)
                protein_g = round(protein, 2)
                carbs_g = round(carbs, 2)
                fat_g = round(fat, 2)
                fiber_g = round(fiber, 2) if fiber is not None else None
                scale = 100.0 / serving_grams if serving_grams else 0.25
                kcal_100g = round(calories * scale, 2)
                protein_100g = round(protein_g * scale, 2)
                carbs_100g = round(carbs_g * scale, 2)
                fat_100g = round(fat_g * scale, 2)
                fiber_100g = round(fiber_g * scale, 2) if fiber_g is not None else None
                portions = [
                    {
                        "label_vi": serving_size[:80],
                        "grams": serving_grams,
                        "is_default": True,
                        "sort_order": 0,
                    }
                ]

            # whey/eggs: adjust macro roles lightly
            macro_roles = list(meta["macro_roles"])
            if "whey" in name_vi.lower():
                macro_roles = ["protein"]
            elif "trứng" in name_vi.lower() or "lòng" in name_vi.lower():
                macro_roles = ["protein", "dairy"]

            food = {
                "slug": food_slug,
                "name_vi": name_vi,
                "name_en": None,
                "category_slug": meta["slug"],
                "food_kind": meta["food_kind"],
                "prep_state": meta["prep_state"],
                "kcal_100g": kcal_100g,
                "protein_100g": protein_100g,
                "carbs_100g": carbs_100g,
                "fat_100g": fat_100g,
                "fiber_100g": fiber_100g,
                "sugar_100g": None,
                "sodium_100mg": None,
                "alcohol_100g": None,
                "yield_factor": None,
                "source_ref": SOURCE_REF,
                "confidence": meta["confidence"],
                "is_common": True,
                "is_verified": meta["confidence"] == "reference",
                "tags": tags,
                "aliases": aliases,
                "portions": portions,
                "vitamins": {},
                "serving_size": serving_size,
                "serving_grams": serving_grams,
                "calories": calories,
                "protein_g": protein_g,
                "carbs_g": carbs_g,
                "fat_g": fat_g,
                "fiber_g": fiber_g,
                "sugar_g": None,
                "sodium_mg": None,
                "is_complete_meal": meta["is_complete_meal"],
                "macro_roles": macro_roles,
                "ai_eligible": meta["ai_eligible"],
                "meal_slots": list(meta["meal_slots"]),
                "ai_priority": meta["ai_priority"],
                "default_for_ai": False,
                "status": "deprecated" if meta["slug"] == "an-vat-do-uong" else "active",
                "description_vi": notes,
                "region_slug": None,
                "province_id": None,
            }
            foods.append(food)
            if aliases:
                aliases_rows.append({"food_slug": food_slug, "aliases": aliases})

    return categories, foods, aliases_rows


def write_seeds(categories: list[dict], foods: list[dict], aliases_rows: list[dict]) -> None:
    SEEDS.mkdir(parents=True, exist_ok=True)
    (SEEDS / "food_categories.json").write_text(
        json.dumps(categories, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (SEEDS / "foods_catalog_v2.json").write_text(
        json.dumps(foods, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (SEEDS / "food_aliases.json").write_text(
        json.dumps(aliases_rows, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    # Empty traditional dishes seed — dishes live in catalog sheet 4
    (SEEDS / "foods_traditional_dishes.json").write_text("[]\n", encoding="utf-8")
    print(f"Wrote {len(categories)} categories, {len(foods)} foods, {len(aliases_rows)} alias rows")


def load_database_url() -> str:
    env_path = ROOT / "api" / ".env"
    if env_path.is_file():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("DATABASE_URL="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    url = __import__("os").environ.get("DATABASE_URL")
    if not url:
        raise SystemExit("DATABASE_URL not found in api/.env or environment")
    return url


def overlay_food_images(db) -> int:
    """Apply seeds/food_images.json onto Food.image_url when the media file exists."""
    from app.models.entities import Food

    mapping_path = SEEDS / "food_images.json"
    if not mapping_path.is_file():
        return 0
    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    if not isinstance(mapping, dict) or not mapping:
        return 0
    media_root = ROOT / "uploads" / "media"
    n = 0
    for slug, rel in mapping.items():
        if not isinstance(slug, str) or not isinstance(rel, str):
            continue
        rel_norm = rel.replace("\\", "/").lstrip("/")
        dest = media_root / Path(*rel_norm.split("/"))
        if not dest.is_file():
            continue
        row = db.query(Food).filter(Food.slug == slug).first()
        if row is None:
            continue
        if row.image_url != rel_norm:
            row.image_url = rel_norm
        n += 1
    return n


def wipe_and_import(categories: list[dict], foods: list[dict]) -> None:
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import Session

    sys.path.insert(0, str(ROOT / "api"))
    from app.models.entities import (  # noqa: WPS433
        Food,
        FoodAlias,
        FoodCategory,
        FoodPortion,
    )

    url = load_database_url()
    engine = create_engine(url)
    now = datetime.now(UTC)

    with engine.begin() as conn:
        # Clear plans / meal refs that block food deletes
        statements = [
            "DELETE FROM meal_plan_items",
            "DELETE FROM meal_plans",
            "DELETE FROM program_day_meals",
            "DELETE FROM user_daily_plan_meals",
            "DELETE FROM user_daily_plan_exercises",
            "UPDATE workout_sessions SET daily_plan_id = NULL, daily_plan_day_id = NULL",
            "DELETE FROM user_daily_plan_days",
            "UPDATE product_redeem_codes SET plan_id = NULL WHERE plan_id IS NOT NULL",
            "UPDATE trainer_assigned_plans SET daily_plan_id = NULL WHERE daily_plan_id IS NOT NULL",
            "DELETE FROM user_daily_plans",
            "DELETE FROM user_workout_plan_exercises",
            "DELETE FROM user_workout_plans",
            "UPDATE foods SET merged_into_id = NULL",
            "DELETE FROM food_aliases",
            "DELETE FROM food_portions",
            "DELETE FROM foods",
            "DELETE FROM food_categories",
        ]
        for sql in statements:
            try:
                conn.execute(text(sql))
                print(f"ok: {sql}")
            except Exception as exc:  # noqa: BLE001
                print(f"skip/warn: {sql} -> {exc}")

    with Session(engine) as db:
        cat_by_slug: dict[str, FoodCategory] = {}
        for c in categories:
            row = FoodCategory(
                slug=c["slug"],
                name_vi=c["name_vi"],
                sort_order=int(c["sort_order"]),
            )
            db.add(row)
            db.flush()
            cat_by_slug[c["slug"]] = row

        for item in foods:
            cat = cat_by_slug[item["category_slug"]]
            food = Food(
                slug=item["slug"],
                name_vi=item["name_vi"],
                name_en=item.get("name_en"),
                category_id=cat.id,
                serving_size=item["serving_size"],
                serving_grams=item.get("serving_grams"),
                calories=float(item["calories"]),
                protein_g=float(item["protein_g"]),
                carbs_g=float(item["carbs_g"]),
                fat_g=float(item["fat_g"]),
                fiber_g=item.get("fiber_g"),
                sugar_g=item.get("sugar_g"),
                sodium_mg=item.get("sodium_mg"),
                is_verified=bool(item.get("is_verified")),
                is_common=bool(item.get("is_common", True)),
                tags=item.get("tags") or [],
                vitamins_json=item.get("vitamins") or {},
                image_url=item.get("image_url"),
                owner_user_id=None,
                food_kind=item.get("food_kind") or "ingredient",
                prep_state=item.get("prep_state"),
                status=(item.get("status") or "active"),
                kcal_100g=item.get("kcal_100g"),
                protein_100g=item.get("protein_100g"),
                carbs_100g=item.get("carbs_100g"),
                fat_100g=item.get("fat_100g"),
                fiber_100g=item.get("fiber_100g"),
                sugar_100g=item.get("sugar_100g"),
                sodium_100mg=item.get("sodium_100mg"),
                alcohol_100g=item.get("alcohol_100g"),
                source_ref=item.get("source_ref"),
                confidence=item.get("confidence") or "estimated",
                yield_factor=item.get("yield_factor"),
                density_g_per_ml=None,
                macro_roles=item.get("macro_roles") or [],
                meal_slots=item.get("meal_slots") or [],
                ai_eligible=bool(item.get("ai_eligible", True)),
                ai_priority=int(item.get("ai_priority") or 0),
                is_complete_meal=item.get("is_complete_meal"),
                default_for_ai=bool(item.get("default_for_ai", False)),
                region_slug=item.get("region_slug"),
                province_id=item.get("province_id"),
                description_vi=item.get("description_vi"),
                created_at=now,
            )
            db.add(food)
            db.flush()
            for p in item.get("portions") or []:
                db.add(
                    FoodPortion(
                        food_id=food.id,
                        label_vi=str(p.get("label_vi") or "100g"),
                        grams=float(p.get("grams") or 100),
                        is_default=bool(p.get("is_default", True)),
                        sort_order=int(p.get("sort_order") or 0),
                    )
                )
            for alias in item.get("aliases") or []:
                a = str(alias).strip()
                if a:
                    db.add(FoodAlias(food_id=food.id, alias=a))
        n_images = overlay_food_images(db)
        db.commit()
        print(f"DB import done: {len(categories)} categories, {len(foods)} foods, {n_images} images")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--excel", type=Path, default=DEFAULT_EXCEL)
    parser.add_argument("--import-db", action="store_true")
    args = parser.parse_args()
    if not args.excel.is_file():
        raise SystemExit(f"Excel not found: {args.excel}")

    categories, foods, aliases_rows = parse_excel(args.excel)
    write_seeds(categories, foods, aliases_rows)
    by_cat: dict[str, int] = {}
    for f in foods:
        by_cat[f["category_slug"]] = by_cat.get(f["category_slug"], 0) + 1
    for slug, n in by_cat.items():
        print(f"  {slug}: {n}")

    if args.import_db:
        wipe_and_import(categories, foods)


if __name__ == "__main__":
    main()
