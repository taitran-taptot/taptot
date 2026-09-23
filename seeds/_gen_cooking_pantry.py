"""Generate seeds/foods_cooking_pantry.json and FOODS_COOKING_ADDED.md."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MEDIA = ROOT / "uploads" / "media"

CATEGORIES = [
    {"slug": "gia-vi-mam-dau", "name_vi": "Gia vị - Mắm - Dầu", "sort_order": 8},
    {"slug": "rau-cu-qua", "name_vi": "Rau - Củ - Quả", "sort_order": 1},
    {"slug": "thit-gia-cam-noi-tang", "name_vi": "Thịt - Gia cầm - Nội tạng", "sort_order": 2},
    {"slug": "ca-thuy-hai-san", "name_vi": "Cá & Thủy hải sản", "sort_order": 3},
    {"slug": "ngu-coc-hat", "name_vi": "Ngũ cốc - Hạt", "sort_order": 5},
]


def portions(*extra):
    items = [{"label_vi": "100g", "grams": 100.0, "is_default": True, "sort_order": 0}]
    for i, (label, grams) in enumerate(extra, start=1):
        items.append({"label_vi": label, "grams": grams, "is_default": False, "sort_order": i})
    return items


def food(
    slug,
    name_vi,
    name_en,
    category_slug,
    kcal,
    p,
    c,
    f,
    *,
    fiber=None,
    sodium=None,
    tags=None,
    aliases=None,
    image_url=None,
    extra_portions=(),
    macro_roles=None,
    prep_state="raw",
    dishes="",
):
    cover = image_url or f"foods/{slug}.jpg"
    return {
        "slug": slug,
        "name_vi": name_vi,
        "name_en": name_en,
        "category_slug": category_slug,
        "food_kind": "ingredient",
        "prep_state": prep_state,
        "kcal_100g": kcal,
        "protein_100g": p,
        "carbs_100g": c,
        "fat_100g": f,
        "fiber_100g": fiber,
        "sodium_100mg": sodium,
        "source_ref": "usda-vn-table",
        "confidence": "estimated",
        "is_common": True,
        "tags": tags or ["gia-vi"],
        "aliases": aliases or [],
        "image_url": cover,
        "portions": portions(*extra_portions),
        "serving_size": "100g",
        "serving_grams": 100,
        "macro_roles": macro_roles or ["produce"],
        "meal_slots": ["lunch", "dinner"],
        "ai_priority": 1,
        "default_for_ai": False,
        "used_in": dishes,
    }


FOODS = [
    food("nuoc-mam", "Nước mắm", "Fish sauce", "gia-vi-mam-dau", 35, 5.1, 3.6, 0.0, sodium=7800, tags=["gia-vi"], aliases=["nước mắm nhĩ"], extra_portions=(("1 muỗng canh (15ml)", 18), ("1 muỗng cà phê (5ml)", 6)), dishes="hầu hết món Việt"),
    food("nuoc-tuong", "Nước tương", "Soy sauce", "gia-vi-mam-dau", 53, 8.1, 4.9, 0.1, sodium=5500, tags=["gia-vi"], extra_portions=(("1 muỗng canh (15ml)", 16),), dishes="xào, ướp"),
    food("mam-tom", "Mắm tôm", "Shrimp paste", "gia-vi-mam-dau", 80, 13.0, 3.0, 1.5, sodium=6500, tags=["gia-vi"], extra_portions=(("1 muỗng cà phê", 8),), dishes="bún đậu, bún mắm"),
    food("mam-ruoc", "Mắm ruốc", "Fermented krill paste", "gia-vi-mam-dau", 95, 14.0, 4.0, 2.0, sodium=6200, tags=["gia-vi"], extra_portions=(("1 muỗng cà phê", 8),), dishes="bún bò Huế, lẩu mắm"),
    food("dau-an", "Dầu ăn", "Vegetable cooking oil", "gia-vi-mam-dau", 884, 0.0, 0.0, 100.0, tags=["gia-vi", "beo"], extra_portions=(("1 muỗng canh (15ml)", 14),), macro_roles=["fat"], dishes="chiên, xào"),
    food("duong-cat", "Đường cát trắng", "White sugar", "gia-vi-mam-dau", 387, 0.0, 100.0, 0.0, tags=["gia-vi"], extra_portions=(("1 muỗng canh", 12), ("1 muỗng cà phê", 4)), macro_roles=["carb"], dishes="nước mắm chua ngọt, kho"),
    food("muoi", "Muối", "Salt", "gia-vi-mam-dau", 0, 0.0, 0.0, 0.0, sodium=38758, tags=["gia-vi"], extra_portions=(("1 muỗng cà phê", 6),), dishes="nêm, luộc"),
    food("tieu-den", "Tiêu đen", "Black pepper", "gia-vi-mam-dau", 251, 10.4, 64.0, 3.3, fiber=25.0, tags=["gia-vi"], extra_portions=(("1 muỗng cà phê", 2),), dishes="ướp thịt, kho"),
    food("ot-hiem", "Ớt hiểm", "Bird's eye chili", "gia-vi-mam-dau", 40, 1.9, 8.8, 0.4, fiber=1.5, tags=["gia-vi"], extra_portions=(("1 trái (~4g)", 4),), dishes="nước chấm, xào"),
    food("giam-gao", "Giấm gạo", "Rice vinegar", "gia-vi-mam-dau", 18, 0.0, 0.6, 0.0, tags=["gia-vi"], extra_portions=(("1 muỗng canh (15ml)", 15),), dishes="nước chấm, gỏi"),
    food("toi", "Tỏi", "Garlic", "rau-cu-qua", 149, 6.4, 33.1, 0.5, fiber=2.1, tags=["gia-vi", "rau"], aliases=["tỏi ta"], extra_portions=(("1 tép (~5g)", 5), ("1 củ (~30g)", 30)), dishes="phi, xào, ướp"),
    food("hanh-tim", "Hành tím khô", "Shallot", "rau-cu-qua", 72, 2.5, 16.8, 0.1, fiber=3.2, tags=["gia-vi", "rau"], extra_portions=(("1 củ (~15g)", 15),), dishes="phi vàng, kho"),
    food("sa", "Sả", "Lemongrass", "rau-cu-qua", 99, 1.8, 25.3, 0.5, fiber=4.0, tags=["gia-vi", "rau"], extra_portions=(("1 cây (~20g)", 20),), dishes="bún bò, gà nướng, lẩu"),
    food("gung", "Gừng", "Ginger", "rau-cu-qua", 80, 1.8, 17.8, 0.8, fiber=2.0, tags=["gia-vi", "rau"], extra_portions=(("1 nhánh (~20g)", 20),), dishes="gà rang gừng, kho"),
    food("rieng", "Riềng", "Galangal", "rau-cu-qua", 71, 1.0, 15.0, 0.8, fiber=2.0, tags=["gia-vi", "rau"], extra_portions=(("1 nhánh (~20g)", 20),), dishes="chả cá, giả cầy"),
    food("nghe", "Nghệ tươi", "Fresh turmeric", "rau-cu-qua", 39, 1.1, 6.8, 0.3, fiber=2.1, tags=["gia-vi", "rau"], extra_portions=(("1 nhánh (~15g)", 15),), dishes="chả cá Lã Vọng"),
    food("la-lot", "Lá lốt", "Piper lolot leaf", "rau-cu-qua", 37, 3.5, 6.0, 0.5, fiber=2.5, tags=["rau"], extra_portions=(("10 lá (~20g)", 20),), dishes="chả lá lốt, bò nướng"),
    food("la-chanh", "Lá chanh", "Kaffir lime leaf", "rau-cu-qua", 43, 1.5, 8.0, 0.5, fiber=2.0, tags=["gia-vi", "rau"], extra_portions=(("5 lá (~5g)", 5),), dishes="gà rang gừng lá chanh"),
    food("ngo-om", "Ngò om", "Rice paddy herb", "rau-cu-qua", 23, 2.0, 3.5, 0.3, fiber=1.5, tags=["rau"], extra_portions=(("1 nắm (~15g)", 15),), dishes="canh chua, lẩu"),
    food("bac-ha-rau", "Bạc hà (rau canh chua)", "Vietnamese mint / spearmint", "rau-cu-qua", 44, 3.3, 8.0, 0.7, fiber=2.0, tags=["rau"], extra_portions=(("1 nắm (~30g)", 30),), dishes="canh chua"),
    food("thi-la", "Thì là", "Dill", "rau-cu-qua", 43, 3.5, 7.0, 1.1, fiber=2.1, tags=["rau"], extra_portions=(("1 nắm (~20g)", 20),), dishes="chả cá Lã Vọng"),
    food("kinh-gioi", "Kinh giới", "Elsholtzia / Vietnamese balm", "rau-cu-qua", 30, 2.2, 5.0, 0.4, fiber=1.8, tags=["rau"], extra_portions=(("1 nắm (~15g)", 15),), dishes="chả cá, bún"),
    food("toi-tay", "Tỏi tây", "Leek", "rau-cu-qua", 61, 1.5, 14.2, 0.3, fiber=1.8, tags=["rau"], extra_portions=(("1 cây (~80g)", 80),), dishes="bò xào cần tỏi tây"),
    food("can-tay", "Cần tây", "Celery", "rau-cu-qua", 16, 0.7, 3.0, 0.2, fiber=1.6, tags=["rau"], extra_portions=(("1 cây (~40g)", 40),), dishes="bò xào cần tỏi tây"),
    food("chanh-ta", "Chanh ta", "Vietnamese lime", "rau-cu-qua", 29, 0.7, 9.3, 0.2, fiber=2.8, tags=["trai-cay"], image_url="foods/chanh-ta.jpg", extra_portions=(("1 quả (~40g)", 40),), dishes="nước chấm, phở"),
    food("sau-xanh", "Sấu xanh", "Dracontomelon", "rau-cu-qua", 54, 0.8, 13.0, 0.3, fiber=2.5, tags=["trai-cay"], extra_portions=(("3 quả (~40g)", 40),), dishes="canh sấu, rau muống dầm sấu"),
    food("ngo-gai", "Ngò gai", "Culantro", "rau-cu-qua", 23, 2.0, 3.7, 0.2, fiber=1.5, tags=["rau"], extra_portions=(("5 lá (~10g)", 10),), dishes="phở, bún bò"),
    food("cua-dong", "Cua đồng", "Rice-field crab", "ca-thuy-hai-san", 87, 17.0, 1.0, 1.5, tags=["protein", "hai-san"], extra_portions=(("10 con (~200g)", 200),), macro_roles=["protein"], dishes="canh cua, bún riêu"),
    food("hen", "Hến", "Baby clam", "ca-thuy-hai-san", 74, 12.8, 2.6, 1.4, tags=["protein", "hai-san"], extra_portions=(("1 bát (~150g)", 150),), macro_roles=["protein"], dishes="cơm hến Huế"),
    food("luon", "Lươn đồng", "Swamp eel", "ca-thuy-hai-san", 99, 18.4, 0.0, 2.5, tags=["protein"], extra_portions=(("1 con (~250g)", 250),), macro_roles=["protein"], dishes="cháo lươn Nghệ An"),
    food("ca-linh", "Cá linh", "Linh fish", "ca-thuy-hai-san", 110, 18.0, 0.0, 4.0, tags=["protein"], extra_portions=(("1 phần (~200g)", 200),), macro_roles=["protein"], dishes="lẩu cá linh Đồng Tháp"),
    food("thit-trau", "Thịt trâu", "Buffalo meat", "thit-gia-cam-noi-tang", 143, 21.4, 0.0, 6.0, tags=["protein"], extra_portions=(("1 phần (~150g)", 150),), macro_roles=["protein"], dishes="thịt trâu gác bếp"),
    food("chan-gio-heo", "Chân giò heo", "Pork hock", "thit-gia-cam-noi-tang", 243, 18.0, 0.0, 18.5, tags=["protein"], extra_portions=(("1 cái (~400g)", 400),), macro_roles=["protein"], dishes="chân giò luộc, bún bò"),
    food("xuong-ong-bo", "Xương ống bò", "Beef marrow bone", "thit-gia-cam-noi-tang", 170, 12.0, 0.0, 13.0, tags=["protein"], extra_portions=(("1 kg", 1000),), macro_roles=["protein"], dishes="phở bò, bò kho"),
    food("canh-ga", "Cánh gà", "Chicken wing", "thit-gia-cam-noi-tang", 191, 17.5, 0.0, 13.0, tags=["protein"], extra_portions=(("2 cánh (~120g)", 120),), macro_roles=["protein"], dishes="gà nướng, rang"),
    food("long-heo", "Lòng heo", "Pork offal mix", "thit-gia-cam-noi-tang", 152, 18.0, 0.0, 8.5, tags=["protein"], extra_portions=(("1 phần (~150g)", 150),), macro_roles=["protein"], dishes="bánh hỏi lòng heo, bánh ướt lòng"),
    food("gan-heo", "Gan heo", "Pork liver", "thit-gia-cam-noi-tang", 135, 21.4, 2.5, 3.7, tags=["protein"], extra_portions=(("1 phần (~80g)", 80),), macro_roles=["protein"], dishes="hủ tiếu Nam Vang, pate"),
    food("gau-bo", "Gầu bò", "Beef brisket fat cap", "thit-gia-cam-noi-tang", 278, 16.0, 0.0, 24.0, tags=["protein"], extra_portions=(("1 phần (~80g)", 80),), macro_roles=["protein"], dishes="phở tái nạm gầu"),
    food("gio-bo", "Gìn bò / giò bò", "Beef shank tendon", "thit-gia-cam-noi-tang", 131, 22.0, 0.0, 4.5, tags=["protein"], extra_portions=(("1 phần (~80g)", 80),), macro_roles=["protein"], dishes="bún bò Huế"),
    food("bi-heo", "Bì heo", "Shredded pork skin", "thit-gia-cam-noi-tang", 212, 22.0, 0.0, 14.0, tags=["protein"], extra_portions=(("1 phần (~40g)", 40),), macro_roles=["protein"], dishes="cơm tấm sườn bì chả"),
    food("cha-trung", "Chả trứng hấp", "Steamed egg meatloaf", "thit-gia-cam-noi-tang", 198, 13.0, 4.0, 14.0, tags=["protein"], extra_portions=(("1 miếng (~60g)", 60),), macro_roles=["protein"], dishes="cơm tấm"),
    food("pate-gan", "Pate gan", "Liver pâté", "thit-gia-cam-noi-tang", 319, 14.0, 1.5, 28.0, tags=["protein", "beo"], extra_portions=(("1 muỗng canh (~20g)", 20),), macro_roles=["protein", "fat"], dishes="bánh mì thịt"),
    food("cha-lua", "Chả lụa", "Vietnamese pork roll", "thit-gia-cam-noi-tang", 220, 14.0, 4.0, 16.0, tags=["protein"], extra_portions=(("2 lát (~40g)", 40),), macro_roles=["protein"], dishes="bánh mì, bún thang"),
    food("trung-muoi", "Trứng muối", "Salted duck egg", "thit-gia-cam-noi-tang", 185, 13.0, 1.5, 14.0, sodium=1200, tags=["protein"], extra_portions=(("1 quả (~50g)", 50),), macro_roles=["protein"], dishes="bánh mì xíu mại trứng muối"),
    food("banh-mi", "Bánh mì", "Vietnamese baguette", "ngu-coc-hat", 265, 9.0, 49.0, 3.2, fiber=2.4, tags=["carb"], extra_portions=(("1 ổ (~120g)", 120),), macro_roles=["carb"], dishes="bánh mì kẹp, ốp la"),
    food("banh-trang", "Bánh tráng", "Rice paper", "ngu-coc-hat", 352, 6.0, 80.0, 0.6, tags=["carb"], extra_portions=(("1 tờ (~10g)", 10),), macro_roles=["carb"], dishes="gỏi cuốn, nem rán, bánh tráng nướng"),
    food("hu-tieu", "Hủ tiếu tươi", "Hu tieu noodles", "ngu-coc-hat", 109, 2.0, 24.0, 0.3, tags=["carb"], extra_portions=(("1 tô (~150g)", 150),), macro_roles=["carb"], dishes="hủ tiếu Nam Vang, Mỹ Tho"),
    food("bot-gao", "Bột gạo", "Rice flour", "ngu-coc-hat", 366, 6.0, 80.0, 1.4, tags=["carb"], extra_portions=(("1 chén (~120g)", 120),), macro_roles=["carb"], dishes="bánh xèo, bánh cuốn, bánh bèo"),
    food("bot-nang", "Bột năng", "Tapioca starch", "ngu-coc-hat", 358, 0.2, 88.0, 0.0, tags=["carb"], extra_portions=(("1 muỗng canh", 10),), macro_roles=["carb"], dishes="bánh bột lọc, bánh canh"),
    food("dau-xanh", "Đậu xanh cà vỏ", "Mung bean", "ngu-coc-hat", 347, 24.0, 63.0, 1.2, fiber=16.0, tags=["protein", "carb"], extra_portions=(("1 chén (~80g)", 80),), macro_roles=["protein", "carb"], dishes="bánh chưng, bánh tét, bánh xèo"),
    food("dau-phong", "Đậu phộng rang", "Roasted peanuts", "ngu-coc-hat", 585, 24.0, 21.0, 49.0, fiber=8.0, tags=["protein", "beo"], extra_portions=(("1 muỗng canh (~12g)", 12),), macro_roles=["protein", "fat"], dishes="gỏi cuốn, cơm hến, mì Quảng"),
    food("nuoc-dua-tuoi", "Nước dừa tươi", "Fresh coconut water", "gia-vi-mam-dau", 19, 0.7, 3.7, 0.2, tags=["gia-vi"], extra_portions=(("1 ly (200ml)", 200),), dishes="thịt kho tàu, cá kho tộ"),
    food("banh-hoi", "Bánh hỏi", "Fine rice vermicelli sheet", "ngu-coc-hat", 110, 1.8, 25.0, 0.2, tags=["carb"], extra_portions=(("1 phần (~120g)", 120),), macro_roles=["carb"], dishes="bánh hỏi lòng heo, nem nướng"),
    food("banh-da", "Bánh đa đỏ", "Red rice noodles", "ngu-coc-hat", 130, 3.0, 28.0, 0.4, tags=["carb"], extra_portions=(("1 tô (~150g)", 150),), macro_roles=["carb"], dishes="bánh đa cua Hải Phòng"),
    food("soi-banh-canh", "Sợi bánh canh", "Banh canh noodles", "ngu-coc-hat", 120, 2.0, 26.0, 0.4, tags=["carb"], extra_portions=(("1 tô (~180g)", 180),), macro_roles=["carb"], dishes="bánh canh cua, bánh canh Trảng Bàng"),
    food("mi-quang", "Mì Quảng sợi", "Quang noodles", "ngu-coc-hat", 140, 3.5, 28.0, 1.0, tags=["carb"], extra_portions=(("1 tô (~150g)", 150),), macro_roles=["carb"], dishes="mì Quảng"),
]

# Live TapTot already has these ingredients under longer slugs — do not seed duplicates.
MERGED_INTO = {
    "toi": "toi-ta-toi-tia",
    "toi-tay": "toi-tay-poireau",
    "hanh-tim": "hanh-tim-kho",
    "gung": "gung-gia",
    "rieng": "cu-rieng",
    "nghe": "nghe-vang",
    "can-tay": "can-tay-da-lat",
    "hen": "hen-song-trung-truc",
    "luon": "luon-dong",
    "ca-linh": "ca-linh-mua-nuoc-noi",
    "chan-gio-heo": "bap-gio-heo-chan-gio-truoc",
    "canh-ga": "canh-ga-nguyen-chiec-canh-tien",
    "bac-ha-rau": "doc-mung-bac-ha",
    "ngo-gai": "mui-tau-ngo-gai",
    "gau-bo": "gau-gion-bo-gau-pho",
    "gio-bo": "gan-bo-gan-chu-y-gan-trong",
}


def has_image(item) -> bool:
    rel = (item.get("image_url") or "").lstrip("/")
    return (MEDIA / rel).is_file()


def main() -> None:
    foods = [item for item in FOODS if item["slug"] not in MERGED_INTO]
    payload = {
        "categories": CATEGORIES,
        "foods": [{k: v for k, v in item.items() if k != "used_in"} for item in foods],
    }
    out = ROOT / "seeds" / "foods_cooking_pantry.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Thực phẩm thêm cho bài cách nấu",
        "",
        "Các mục dưới đây **chưa có** trong catalog `foods_catalog_v2.json` / `grain_nut_foods.json` nên được thêm qua `seeds/foods_cooking_pantry.json`.",
        "",
        f"Tổng: **{len(foods)}** thực phẩm (đã bỏ {len(MERGED_INTO)} món trùng catalog live).",
        "",
        "| Tên | Slug | Nhóm | kcal/100g | P | C | F | Ảnh | Dùng cho |",
        "|-----|------|------|-----------|---|---|---|-----|----------|",
    ]
    for item in foods:
        img = "có" if has_image(item) else "chưa có file"
        lines.append(
            f"| {item['name_vi']} | `{item['slug']}` | {item['category_slug']} | "
            f"{item['kcal_100g']} | {item['protein_100g']} | {item['carbs_100g']} | {item['fat_100g']} | "
            f"{img} | {item.get('used_in') or ''} |"
        )
    lines.extend(
        [
            "",
            "## Ghi chú ảnh",
            "",
            "- Nếu cột Ảnh = **có**: file `uploads/media/foods/{slug}.jpg` (ảnh Gemini 16:9, trừ `chanh-ta` giữ ảnh catalog cũ vì Gemini sai).",
            "- Nếu **chưa có file**: chờ gen lại — xem `FOODS_COOKING_IMAGE_PROMPTS_RETRY.md`.",
            "",
            "## Trùng catalog live (không seed)",
            "",
        ]
    )
    for src, dest in MERGED_INTO.items():
        lines.append(f"- `{src}` → `{dest}`")
    lines.extend(
        [
            "",
        ]
    )
    md = ROOT / "seeds" / "FOODS_COOKING_ADDED.md"
    md.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {out} ({len(foods)} foods)")
    print(f"wrote {md}")


if __name__ == "__main__":
    main()
