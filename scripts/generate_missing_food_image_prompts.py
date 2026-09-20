# -*- coding: utf-8 -*-
"""Generate image prompts for foods listed in foods-chua-co-anh.txt."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from generate_food_image_prompts import BASE, BASE_MEAT, is_meat, meat_parts, part_desc

CATALOG = ROOT / "seeds" / "foods_catalog_v2.json"
MISSING = Path(r"C:\Users\Tran Tai\Downloads\foods-chua-co-anh.txt")
OUT = Path(r"C:\Users\Tran Tai\Downloads\prompts-foods-chua-co-anh.txt")
OUT_MEAT = Path(r"C:\Users\Tran Tai\Downloads\prompts-thit-tu-158.txt")

SHEET_BY_CAT = {
    "rau-cu-qua": "1_Rau_Cu_Qua",
    "thit-gia-cam-noi-tang": "2_Thit_GiaSuc_GiaCam_NoiTang",
    "ca-thuy-hai-san": "3_Ca_ThuyHaiSan",
    "trung-whey": "6_Trung_Sua_Whey",
    "mon-truyen-thong": "4_Mon_An_Truyen_Thong",
    "an-vat-banh-keo-do-uong": "5_An_Vat_Banh_Keo_DoUong",
}


def nhom_vi(item: dict) -> str:
    for tag in item.get("tags") or []:
        if str(tag).startswith("nhom_vi:"):
            return str(tag).split(":", 1)[1]
    return item.get("category_slug") or "Thực phẩm"


def parse_missing() -> list[dict]:
    rows: list[dict] = []
    for line in MISSING.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if (
            not stripped
            or stripped.startswith("STT")
            or stripped.startswith("----")
            or stripped.startswith("Tổng")
            or stripped.startswith("Đã")
            or stripped.startswith("Còn")
        ):
            continue
        parts = [p.strip() for p in stripped.split("|")]
        if len(parts) < 4:
            continue
        rows.append(
            {
                "stt": int(parts[0]),
                "name": parts[1],
                "slug": parts[2],
                "category": parts[3],
            }
        )
    return rows


def fruit_parts(name: str) -> tuple[str, str]:
    return (
        "FRONT (Part 2 – prepared, must be in front): the same fruit cut in half to clearly show flesh, "
        "seeds, and interior structure.",
        f"BACK (Part 1 – original, slightly behind): whole intact fresh {name}, uncut, natural fruit "
        "shape, 3/4 angle.",
    )


def main() -> None:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    by_slug = {item["slug"]: item for item in catalog}
    missing = parse_missing()
    prompts: list[str] = []
    meat_prompts: list[str] = []

    for row in missing:
        item = by_slug.get(row["slug"])
        name = (item["name_vi"] if item else row["name"]).strip()
        group = nhom_vi(item) if item else row["category"]
        category = (item["category_slug"] if item else row["category"])
        sheet = SHEET_BY_CAT.get(category, "1_Rau_Cu_Qua")
        food = {"name": name, "group": group, "sheet": sheet}

        use_meat = category == "thit-gia-cam-noi-tang" or is_meat(group, name)
        # Fruit named "Trứng gà / Lekima" must not use the egg template.
        if "lekima" in name.lower() or (
            "quả" in group.lower() and "trứng" in name.lower()
        ):
            p2_front, p1_back = fruit_parts(name)
            base = BASE
        elif use_meat:
            p2_front, p1_back = meat_parts(name)
            base = BASE_MEAT
        else:
            p2_front, p1_back = part_desc(food)
            base = BASE

        prompt = (
            f'[{row["stt"]}] {name} ({group})\n'
            f'Create a professional realistic product photo of Vietnamese food item "{name}". {base} '
            f"{p2_front} {p1_back} "
            "The two food objects must stand closely next to each other in one continuous scene, "
            "with Part 2 clearly closer to the camera than Part 1. "
            "Use the most suitable 3/4 (or best clarifying) camera angle so shape and structure are obvious. "
            "Photorealistic commercial catalog look suitable for a fitness/nutrition website food database."
        )
        prompts.append(prompt)
        if use_meat and row["stt"] >= 158:
            meat_prompts.append(prompt)

    text = "\n\n".join(prompts) + "\n"
    OUT.write_text(text, encoding="utf-8")
    OUT_MEAT.write_text("\n\n".join(meat_prompts) + "\n", encoding="utf-8")
    print(f"Wrote {len(prompts)} prompts -> {OUT}")
    print(f"Wrote {len(meat_prompts)} meat prompts (STT >= 158) -> {OUT_MEAT}")
    print(f"Size: {OUT.stat().st_size} bytes; meat file: {OUT_MEAT.stat().st_size} bytes")


if __name__ == "__main__":
    main()
