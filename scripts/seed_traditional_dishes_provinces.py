# -*- coding: utf-8 -*-
"""Upsert Vietnamese specialty dishes with province_id / region_slug.

- Assign provinces to existing Excel traditional dishes
- Restore specialty dishes from legacy seed (git HEAD)
- Add extra iconic specialties for map coverage
- Upsert into DB under category mon-an-truyen-thong
- Write seeds/foods_traditional_dishes.json
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import unicodedata
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))

SOURCE_REF = "excel+specialty:viet-nam-dishes"


def slugify(text: str) -> str:
    s = unicodedata.normalize("NFD", text.strip().lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.replace("đ", "d").replace("Đ", "d")
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return re.sub(r"-{2,}", "-", s).strip("-")[:80] or "mon"


def load_db_url() -> str:
    for line in (ROOT / "api" / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith("DATABASE_URL="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("DATABASE_URL missing")


def load_legacy_specialties() -> list[dict]:
    raw = subprocess.check_output(
        ["git", "show", "HEAD:seeds/foods_traditional_dishes.json"],
        cwd=str(ROOT),
    )
    return json.loads(raw.decode("utf-8"))


# province assignments for Excel sheet-4 dishes (by exact name_vi)
EXCEL_PROVINCE: dict[str, tuple[str, str]] = {
    # Hà Nội
    "Phở bò chín (Nạc)": ("01", "mien-bac"),
    "Phở bò tái nạm / gầu": ("01", "mien-bac"),
    "Phở gà ta (Có da)": ("01", "mien-bac"),
    "Bún chả Hà Nội": ("01", "mien-bac"),
    "Bún đậu mắm tôm": ("01", "mien-bac"),
    "Bún ốc giấm bỗng": ("01", "mien-bac"),
    "Bún măng vịt": ("01", "mien-bac"),
    "Bún thang Hà Nội": ("01", "mien-bac"),
    "Bún riêu cua đồng": ("01", "mien-bac"),
    "Bánh cuốn nóng kèm chả quế": ("01", "mien-bac"),
    "Nem rán / Chả giò chiên": ("01", "mien-bac"),
    "Bánh chưng luộc truyền thống": ("01", "mien-bac"),
    "Bánh chưng rán": ("01", "mien-bac"),
    "Chả lá lốt rán": ("01", "mien-bac"),
    "Canh cua mồng tơi rau đay": ("01", "mien-bac"),
    "Canh sườn nấu chua sấu / me": ("01", "mien-bac"),
    "Rau muống xào tỏi": ("01", "mien-bac"),
    "Rau muống luộc dầm sấu / chanh": ("01", "mien-bac"),
    "Thịt chân giò luộc": ("01", "mien-bac"),
    "Thịt ba chỉ rang cháy cạnh": ("01", "mien-bac"),
    "Gà rang gừng lá chanh": ("01", "mien-bac"),
    "Bò xào cần tỏi tây": ("01", "mien-bac"),
    "Đậu phụ tẩm hành rán": ("01", "mien-bac"),
    "Đậu phụ sốt cà chua": ("01", "mien-bac"),
    "Cơm trắng (Gạo tẻ)": ("01", "mien-bac"),
    # Hải Phòng
    "Bánh đa cua Hải Phòng": ("31", "mien-bac"),
    # Huế
    "Bún bò Huế đầy đủ": ("46", "mien-trung"),
    "Bánh bèo chén Huế (5 chén)": ("46", "mien-trung"),
    "Bánh nậm Huế": ("46", "mien-trung"),
    "Bánh bột lọc Huế": ("46", "mien-trung"),
    # Đà Nẵng / Hội An (map id 48)
    "Mì Quảng (Tôm thịt heo / gà)": ("48", "mien-trung"),
    "Cao lầu Hội An": ("48", "mien-trung"),
    "Bánh xèo miền Trung (Bánh nhỏ)": ("48", "mien-trung"),
    "Bánh ướt lòng gà trứng non": ("44", "mien-trung"),
    # TP.HCM / Nam Bộ
    "Hủ tiếu Nam Vang (Nước)": ("79", "mien-nam"),
    "Hủ tiếu Nam Vang (Khô)": ("79", "mien-nam"),
    "Bánh mì kẹp thịt chả pate": ("79", "mien-nam"),
    "Bánh mì ốp la (2 trứng)": ("79", "mien-nam"),
    "Bánh mì xíu mại trứng muối": ("79", "mien-nam"),
    "Gỏi cuốn tôm thịt": ("79", "mien-nam"),
    "Bánh xèo miền Tây": ("79", "mien-nam"),
    "Cơm tấm Sườn Bì Chả đầy đủ": ("79", "mien-nam"),
    "Thịt kho tàu nước dừa": ("79", "mien-nam"),
    "Cá kho tộ (Cá lóc/trắm đen)": ("79", "mien-nam"),
    "Cá basa / tra kho tộ": ("79", "mien-nam"),
    "Canh chua cá lóc Nam Bộ": ("79", "mien-nam"),
    "Bánh canh cá lóc": ("79", "mien-nam"),
    "Bánh canh cua / ghẹ": ("79", "mien-nam"),
    # Vĩnh Long
    "Bánh tét nhân thịt đậu xanh": ("86", "mien-nam"),
}

# Extra specialties not in Excel / legacy seed (fill famous gaps)
EXTRA_SPECIALTIES: list[dict] = [
    {
        "slug": "bun-thit-nuong",
        "name_vi": "Bún thịt nướng",
        "name_en": "Grilled pork vermicelli",
        "province_id": "79",
        "region_slug": "mien-nam",
        "description_vi": "Bún tươi, thịt heo nướng than, đồ chua, nước mắm chua ngọt — phổ biến miền Nam và Trung.",
        "serving_size": "1 tô",
        "serving_grams": 450,
        "calories": 520,
        "protein_g": 28,
        "carbs_g": 62,
        "fat_g": 16,
        "group": "Món Nước & Sợi",
    },
    {
        "slug": "nem-nuong-nha-trang",
        "name_vi": "Nem nướng Nha Trang",
        "name_en": "Nha Trang grilled pork sausage",
        "province_id": "56",
        "region_slug": "mien-trung",
        "description_vi": "Nem heo nướng xiên, bánh ướt, đồ chua và nước sốt đặc trưng Khánh Hòa.",
        "serving_size": "1 suất",
        "serving_grams": 350,
        "calories": 480,
        "protein_g": 26,
        "carbs_g": 42,
        "fat_g": 22,
        "group": "Bánh Mì & Món Cuốn",
    },
    {
        "slug": "banh-khot-vung-tau",
        "name_vi": "Bánh khọt Vũng Tàu",
        "name_en": "Vung Tau banh khot",
        "province_id": "75",
        "region_slug": "mien-nam",
        "description_vi": "Bánh khọt giòn đáy, nhân tôm — đặc sản vùng biển Đông Nam Bộ (gán Đồng Nai trên bản đồ).",
        "serving_size": "10 cái",
        "serving_grams": 250,
        "calories": 420,
        "protein_g": 18,
        "carbs_g": 38,
        "fat_g": 22,
        "group": "Bánh Mì & Món Cuốn",
    },
    {
        "slug": "com-ga-hoi-an",
        "name_vi": "Cơm gà Hội An",
        "name_en": "Hoi An chicken rice",
        "province_id": "48",
        "region_slug": "mien-trung",
        "description_vi": "Cơm vàng nấu nước gà, gà luộc xé phay, đồ chua và nước mắm gừng.",
        "serving_size": "1 đĩa",
        "serving_grams": 450,
        "calories": 580,
        "protein_g": 32,
        "carbs_g": 68,
        "fat_g": 16,
        "group": "Món Cơm Gia Đình",
    },
    {
        "slug": "bo-kho",
        "name_vi": "Bò kho",
        "name_en": "Vietnamese beef stew",
        "province_id": "79",
        "region_slug": "mien-nam",
        "description_vi": "Bò hầm sả ớt cà rốt khoai tây — ăn với bánh mì hoặc hủ tiếu.",
        "serving_size": "1 tô",
        "serving_grams": 400,
        "calories": 480,
        "protein_g": 34,
        "carbs_g": 28,
        "fat_g": 24,
        "group": "Món Nước & Sợi",
    },
    {
        "slug": "bun-mam",
        "name_vi": "Bún mắm",
        "name_en": "Fermented fish noodle soup",
        "province_id": "91",
        "region_slug": "mien-nam",
        "description_vi": "Bún nước mắm cá linh/cá sặc, tôm, mực, thịt quay — đặc sản miền Tây.",
        "serving_size": "1 tô",
        "serving_grams": 500,
        "calories": 520,
        "protein_g": 30,
        "carbs_g": 58,
        "fat_g": 18,
        "group": "Món Nước & Sợi",
    },
    {
        "slug": "com-hen-hue",
        "name_vi": "Cơm hến Huế",
        "name_en": "Hue baby clam rice",
        "province_id": "46",
        "region_slug": "mien-trung",
        "description_vi": "Cơm nguội, hến xào, đậu phộng, bánh đa, ớt màu — món bình dân cố đô.",
        "serving_size": "1 đĩa",
        "serving_grams": 350,
        "calories": 420,
        "protein_g": 18,
        "carbs_g": 55,
        "fat_g": 14,
        "group": "Món Cơm Gia Đình",
    },
    {
        "slug": "banh-beo-chen-da-nang",
        "name_vi": "Bánh bèo chén Đà Nẵng",
        "name_en": "Da Nang banh beo",
        "province_id": "48",
        "region_slug": "mien-trung",
        "description_vi": "Bánh bèo chén nhỏ, tôm cháy, da heo chiên — gần với phong cách miền Trung.",
        "serving_size": "5 chén",
        "serving_grams": 200,
        "calories": 300,
        "protein_g": 10,
        "carbs_g": 40,
        "fat_g": 10,
        "group": "Bánh Mì & Món Cuốn",
    },
    {
        "slug": "bun-cha-ca-da-nang",
        "name_vi": "Bún chả cá Đà Nẵng",
        "name_en": "Da Nang fish cake noodles",
        "province_id": "48",
        "region_slug": "mien-trung",
        "description_vi": "Bún nước dùng cà chua, chả cá chiên/hấp — đặc sản Đà Nẵng.",
        "serving_size": "1 tô",
        "serving_grams": 450,
        "calories": 450,
        "protein_g": 26,
        "carbs_g": 55,
        "fat_g": 14,
        "group": "Món Nước & Sợi",
    },
    {
        "slug": "banh-trang-nuong-da-lat",
        "name_vi": "Bánh tráng nướng Đà Lạt",
        "name_en": "Da Lat grilled rice paper",
        "province_id": "68",
        "region_slug": "mien-trung",
        "description_vi": "Bánh tráng nướng than, trứng, hành, bò khô — ăn vặt phố núi.",
        "serving_size": "1 cái",
        "serving_grams": 120,
        "calories": 320,
        "protein_g": 10,
        "carbs_g": 36,
        "fat_g": 14,
        "group": "Bánh Mì & Món Cuốn",
    },
    {
        "slug": "banh-xeo-toc-tien",
        "name_vi": "Bánh xèo Tóc Tiên",
        "name_en": "Toc Tien banh xeo",
        "province_id": "75",
        "region_slug": "mien-nam",
        "description_vi": "Bánh xèo tôm thịt giòn lớn kiểu Đông Nam Bộ.",
        "serving_size": "1 cái",
        "serving_grams": 280,
        "calories": 560,
        "protein_g": 22,
        "carbs_g": 48,
        "fat_g": 30,
        "group": "Bánh Mì & Món Cuốn",
    },
    {
        "slug": "hu-tieu-my-tho",
        "name_vi": "Hủ tiếu Mỹ Tho",
        "name_en": "My Tho hu tieu",
        "province_id": "82",
        "region_slug": "mien-nam",
        "description_vi": "Hủ tiếu xương, tôm, thịt, gan — đặc sản Tiền Giang / Đồng Tháp (gán Đồng Tháp).",
        "serving_size": "1 tô",
        "serving_grams": 480,
        "calories": 490,
        "protein_g": 26,
        "carbs_g": 64,
        "fat_g": 14,
        "group": "Món Nước & Sợi",
    },
    {
        "slug": "bun-nuoc-leo-can-tho",
        "name_vi": "Bún nước lèo Cần Thơ",
        "name_en": "Can Tho bun nuoc leo",
        "province_id": "92",
        "region_slug": "mien-nam",
        "description_vi": "Bún nước dùng mắm cá linh, tôm, thịt quay — đặc sản Tây Đô.",
        "serving_size": "1 tô",
        "serving_grams": 480,
        "calories": 510,
        "protein_g": 28,
        "carbs_g": 60,
        "fat_g": 16,
        "group": "Món Nước & Sợi",
    },
]


def dish_payload(
    *,
    slug: str,
    name_vi: str,
    name_en: str | None,
    province_id: str,
    region_slug: str,
    description_vi: str | None,
    serving_size: str,
    serving_grams: float,
    calories: float,
    protein_g: float,
    carbs_g: float,
    fat_g: float,
    group: str,
    fiber_g: float | None = None,
) -> dict:
    scale = 100.0 / serving_grams if serving_grams else 0.25
    group_slug = slugify(group)
    return {
        "slug": slug,
        "name_vi": name_vi,
        "name_en": name_en,
        "category_slug": "mon-an-truyen-thong",
        "food_kind": "dish",
        "prep_state": "cooked",
        "serving_size": serving_size,
        "serving_grams": serving_grams,
        "calories": round(float(calories), 2),
        "protein_g": round(float(protein_g), 2),
        "carbs_g": round(float(carbs_g), 2),
        "fat_g": round(float(fat_g), 2),
        "fiber_g": fiber_g,
        "kcal_100g": round(float(calories) * scale, 2),
        "protein_100g": round(float(protein_g) * scale, 2),
        "carbs_100g": round(float(carbs_g) * scale, 2),
        "fat_100g": round(float(fat_g) * scale, 2),
        "fiber_100g": round(fiber_g * scale, 2) if fiber_g is not None else None,
        "is_common": True,
        "is_verified": False,
        "confidence": "estimated",
        "source_ref": SOURCE_REF,
        "tags": [
            f"nhom:{group_slug}",
            f"nhom_vi:{group}",
            "viet-nam",
            "complete_meal",
            region_slug,
        ],
        "macro_roles": ["carb", "protein"],
        "meal_slots": ["lunch", "dinner"],
        "ai_eligible": True,
        "ai_priority": 30,
        "is_complete_meal": True,
        "default_for_ai": False,
        "province_id": province_id,
        "region_slug": region_slug,
        "description_vi": description_vi,
        "portions": [
            {
                "label_vi": serving_size[:80],
                "grams": float(serving_grams),
                "is_default": True,
                "sort_order": 0,
            }
        ],
    }


def normalize_name(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().lower())


def names_overlap(a: str, b: str) -> bool:
    """True if two dish names are the same specialty (avoid duplicates).

    Regional variants that share only a dish type (bánh xèo miền Tây vs Tóc Tiên,
    bánh bèo Huế vs Đà Nẵng) are NOT treated as duplicates.
    """
    na, nb = normalize_name(a), normalize_name(b)
    if na == nb:
        return True
    sa = re.sub(r"\([^)]*\)", "", na).strip()
    sb = re.sub(r"\([^)]*\)", "", nb).strip()
    if sa and sb and sa == sb:
        return True

    stop = {
        "mon", "va", "cua", "voi", "day", "du", "nong", "lanh", "mien", "nam",
        "bac", "trung", "ta", "co", "da", "khong", "kem", "toi",
    }
    placeish = {
        "ha", "noi", "sai", "gon", "hue", "nang", "phong", "trang", "lat",
        "tau", "tho", "an", "hoi", "vung", "khanh", "hoa", "dong", "nai",
        "vinh", "long", "thanh", "nghe", "tinh", "quang", "tri", "ngai",
        "binh", "dinh", "dak", "lak", "lai", "chau", "cao", "bang", "son",
        "la", "lao", "cai", "thai", "nguyen", "ninh", "phu", "hung", "yen",
        "hai", "tuyen", "gia", "mau", "giang", "tay", "toc", "tien", "my",
        "chau", "doc", "nha",
    }
    dish_type = {
        "banh", "bun", "pho", "com", "mi", "nem", "goi", "cha", "canh", "thit",
        "ca", "ga", "bo", "heo", "tom", "xeo", "beo", "uot", "cuon", "ran",
        "nuong", "kho", "luoc", "xao", "hu", "tieu", "hutieu", "chen",
    }

    def fold_tokens(s: str) -> set[str]:
        x = unicodedata.normalize("NFD", s)
        x = "".join(c for c in x if unicodedata.category(c) != "Mn").replace("đ", "d")
        return {
            t
            for t in re.split(r"[^a-z0-9]+", x)
            if len(t) > 2 and t not in stop
        }

    fa, fb = fold_tokens(sa), fold_tokens(sb)
    if not fa or not fb:
        return False

    places_a, places_b = fa & placeish, fb & placeish
    if places_a and places_b and places_a != places_b:
        return False

    if sa in sb or sb in sa:
        longer, shorter = (sb, sa) if sa in sb else (sa, sb)
        leftover = fold_tokens(longer) - fold_tokens(shorter)
        if leftover <= placeish:
            return True

    inter = fa & fb
    distinctive = inter - dish_type - placeish
    if len(distinctive) >= 2:
        return True
    if len(distinctive) == 1 and len(inter - placeish) >= 3:
        return True

    core_a, core_b = fa - placeish, fb - placeish
    if core_a and core_a == core_b and len(core_a) >= 2:
        if not places_a and not places_b:
            return True
        if places_a == places_b or not places_a or not places_b:
            return True
    return False


def build_all_dishes(existing_excel_dishes: list[dict]) -> list[dict]:
    """Merge Excel dishes (with province), legacy specialties, extras."""
    by_norm: dict[str, dict] = {}

    for d in existing_excel_dishes:
        name = d["name_vi"]
        prov = EXCEL_PROVINCE.get(name)
        if prov:
            d = {**d, "province_id": prov[0], "region_slug": prov[1]}
            if not d.get("description_vi"):
                d["description_vi"] = f"Món truyền thống Việt Nam ({prov[1]})."
        tags = list(d.get("tags") or [])
        if d.get("region_slug") and d["region_slug"] not in tags:
            tags.append(d["region_slug"])
        if "viet-nam" not in tags:
            tags.append("viet-nam")
        if "complete_meal" not in tags:
            tags.append("complete_meal")
        d["tags"] = tags
        d["food_kind"] = "dish"
        d["is_complete_meal"] = True
        by_norm[normalize_name(name)] = d

    for item in load_legacy_specialties():
        name = item["name_vi"]
        matched = None
        for existing in by_norm.values():
            if names_overlap(name, existing["name_vi"]):
                matched = existing
                break
        if matched is not None:
            if not matched.get("province_id") and item.get("province_id"):
                matched["province_id"] = str(item["province_id"])
                matched["region_slug"] = item.get("region_slug")
            if item.get("description_vi") and (
                not matched.get("description_vi")
                or "truyền thống Việt Nam" in (matched.get("description_vi") or "")
            ):
                matched["description_vi"] = item["description_vi"]
            if matched.get("region_slug") and matched["region_slug"] not in (matched.get("tags") or []):
                matched.setdefault("tags", []).append(matched["region_slug"])
            continue

        payload = dish_payload(
            slug=item["slug"],
            name_vi=name,
            name_en=item.get("name_en"),
            province_id=str(item["province_id"]),
            region_slug=str(item["region_slug"]),
            description_vi=item.get("description_vi"),
            serving_size=str(item.get("serving_size") or "1 phần"),
            serving_grams=float(item.get("serving_grams") or 400),
            calories=float(item.get("calories") or 0),
            protein_g=float(item.get("protein_g") or 0),
            carbs_g=float(item.get("carbs_g") or 0),
            fat_g=float(item.get("fat_g") or 0),
            group="Đặc sản vùng miền",
        )
        by_norm[normalize_name(name)] = payload

    for item in EXTRA_SPECIALTIES:
        if any(names_overlap(item["name_vi"], e["name_vi"]) for e in by_norm.values()):
            continue
        by_norm[normalize_name(item["name_vi"])] = dish_payload(
            slug=item["slug"],
            name_vi=item["name_vi"],
            name_en=item.get("name_en"),
            province_id=item["province_id"],
            region_slug=item["region_slug"],
            description_vi=item.get("description_vi"),
            serving_size=item["serving_size"],
            serving_grams=float(item["serving_grams"]),
            calories=float(item["calories"]),
            protein_g=float(item["protein_g"]),
            carbs_g=float(item["carbs_g"]),
            fat_g=float(item["fat_g"]),
            group=item.get("group") or "Đặc sản vùng miền",
        )

    return list(by_norm.values())


def existing_excel_from_db(db: Session) -> list[dict]:
    from app.models.entities import Food, FoodCategory

    cat = db.query(FoodCategory).filter(FoodCategory.slug == "mon-an-truyen-thong").first()
    if not cat:
        return []
    rows = db.query(Food).filter(Food.category_id == cat.id).all()
    out = []
    for f in rows:
        out.append(
            {
                "slug": f.slug,
                "name_vi": f.name_vi,
                "name_en": f.name_en,
                "category_slug": "mon-an-truyen-thong",
                "food_kind": "dish",
                "prep_state": f.prep_state or "cooked",
                "serving_size": f.serving_size,
                "serving_grams": f.serving_grams or 400,
                "calories": f.calories,
                "protein_g": f.protein_g,
                "carbs_g": f.carbs_g,
                "fat_g": f.fat_g,
                "fiber_g": f.fiber_g,
                "kcal_100g": f.kcal_100g,
                "protein_100g": f.protein_100g,
                "carbs_100g": f.carbs_100g,
                "fat_100g": f.fat_100g,
                "fiber_100g": f.fiber_100g,
                "is_common": True,
                "is_verified": bool(f.is_verified),
                "confidence": f.confidence or "estimated",
                "source_ref": f.source_ref or SOURCE_REF,
                "tags": list(f.tags or []),
                "macro_roles": list(f.macro_roles or ["carb", "protein"]),
                "meal_slots": list(f.meal_slots or ["lunch", "dinner"]),
                "ai_eligible": True,
                "ai_priority": f.ai_priority or 30,
                "is_complete_meal": True,
                "default_for_ai": False,
                "province_id": f.province_id,
                "region_slug": f.region_slug,
                "description_vi": f.description_vi,
                "portions": [
                    {
                        "label_vi": (f.serving_size or "1 phần")[:80],
                        "grams": float(f.serving_grams or 400),
                        "is_default": True,
                        "sort_order": 0,
                    }
                ],
            }
        )
    return out


def upsert_dishes(dishes: list[dict]) -> None:
    from app.models.entities import Food, FoodAlias, FoodCategory, FoodPortion

    url = load_db_url()
    engine = create_engine(url)
    now = datetime.now(UTC)

    with Session(engine) as db:
        cat = db.query(FoodCategory).filter(FoodCategory.slug == "mon-an-truyen-thong").first()
        if not cat:
            cat = FoodCategory(
                slug="mon-an-truyen-thong",
                name_vi="Món truyền thống",
                sort_order=5,
            )
            db.add(cat)
            db.flush()

        updated = created = 0
        for item in dishes:
            slug = item["slug"]
            row = db.query(Food).filter(Food.slug == slug).first()
            # also match by exact name under dish category
            if row is None:
                row = (
                    db.query(Food)
                    .filter(
                        Food.category_id == cat.id,
                        Food.name_vi == item["name_vi"],
                    )
                    .first()
                )
            fields = {
                "name_vi": item["name_vi"],
                "name_en": item.get("name_en"),
                "category_id": cat.id,
                "serving_size": item["serving_size"],
                "serving_grams": item.get("serving_grams"),
                "calories": float(item["calories"]),
                "protein_g": float(item["protein_g"]),
                "carbs_g": float(item["carbs_g"]),
                "fat_g": float(item["fat_g"]),
                "fiber_g": item.get("fiber_g"),
                "is_verified": bool(item.get("is_verified")),
                "is_common": True,
                "tags": item.get("tags") or [],
                "vitamins_json": {},
                "food_kind": "dish",
                "prep_state": "cooked",
                "status": "active",
                "kcal_100g": item.get("kcal_100g"),
                "protein_100g": item.get("protein_100g"),
                "carbs_100g": item.get("carbs_100g"),
                "fat_100g": item.get("fat_100g"),
                "fiber_100g": item.get("fiber_100g"),
                "source_ref": item.get("source_ref") or SOURCE_REF,
                "confidence": item.get("confidence") or "estimated",
                "macro_roles": item.get("macro_roles") or ["carb", "protein"],
                "meal_slots": item.get("meal_slots") or ["lunch", "dinner"],
                "ai_eligible": True,
                "ai_priority": int(item.get("ai_priority") or 30),
                "is_complete_meal": True,
                "default_for_ai": False,
                "province_id": item.get("province_id"),
                "region_slug": item.get("region_slug"),
                "description_vi": item.get("description_vi"),
            }
            if row is None:
                row = Food(slug=slug, created_at=now, **fields)
                db.add(row)
                db.flush()
                created += 1
            else:
                # keep existing slug
                for k, v in fields.items():
                    setattr(row, k, v)
                updated += 1
                db.flush()

            # ensure default portion
            has_portion = (
                db.query(FoodPortion).filter(FoodPortion.food_id == row.id).first() is not None
            )
            if not has_portion:
                p = (item.get("portions") or [{}])[0]
                db.add(
                    FoodPortion(
                        food_id=row.id,
                        label_vi=str(p.get("label_vi") or item["serving_size"])[:80],
                        grams=float(p.get("grams") or item.get("serving_grams") or 400),
                        is_default=True,
                        sort_order=0,
                    )
                )
        db.commit()
        print(f"Upserted dishes: created={created}, updated={updated}, total={len(dishes)}")


def write_seed(dishes: list[dict]) -> None:
    # Traditional seed used by ensure_traditional_dish_seeds — keep specialty payload shape
    seed = []
    for d in dishes:
        if not d.get("province_id"):
            continue
        seed.append(
            {
                "slug": d["slug"],
                "name_vi": d["name_vi"],
                "name_en": d.get("name_en"),
                "province_id": d["province_id"],
                "region_slug": d.get("region_slug"),
                "description_vi": d.get("description_vi"),
                "serving_size": d.get("serving_size"),
                "serving_grams": d.get("serving_grams"),
                "calories": d.get("calories"),
                "protein_g": d.get("protein_g"),
                "carbs_g": d.get("carbs_g"),
                "fat_g": d.get("fat_g"),
                "tags": d.get("tags") or ["viet-nam", "complete_meal"],
                "macro_roles": d.get("macro_roles") or ["carb", "protein"],
                "ai_priority": d.get("ai_priority") or 30,
                "is_verified": False,
                "is_common": True,
                "source_ref": SOURCE_REF,
            }
        )
    path = ROOT / "seeds" / "foods_traditional_dishes.json"
    path.write_text(json.dumps(seed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(seed)} dishes -> {path}")


def main() -> None:
    from app.models.entities import FoodCategory
    from sqlalchemy.orm import Session as SASession

    engine = create_engine(load_db_url())
    with SASession(engine) as db:
        excel_shaped = existing_excel_from_db(db)

    dishes = build_all_dishes(excel_shaped)
    with_prov = sum(1 for d in dishes if d.get("province_id"))
    print(f"Built {len(dishes)} dishes ({with_prov} with province)")

    # stats by region
    from collections import Counter

    print(Counter(d.get("region_slug") or "none" for d in dishes))
    write_seed(dishes)
    upsert_dishes(dishes)

    # verify DB
    with engine.connect() as conn:
        n = conn.execute(
            text(
                """
                SELECT COUNT(*) FROM foods f
                JOIN food_categories fc ON fc.id=f.category_id
                WHERE fc.slug='mon-an-truyen-thong'
                """
            )
        ).scalar()
        n_prov = conn.execute(
            text(
                """
                SELECT COUNT(*) FROM foods f
                JOIN food_categories fc ON fc.id=f.category_id
                WHERE fc.slug='mon-an-truyen-thong'
                  AND f.province_id IS NOT NULL AND f.province_id <> ''
                """
            )
        ).scalar()
        print(f"DB mon-an-truyen-thong: {n} (with province: {n_prov})")


if __name__ == "__main__":
    main()
