#!/usr/bin/env python3
"""Publish audited-correct photos from Downloads/gemini-folder-1.

Filename STT is the second number (``001_233-…``).
Only chắc chắn photos are published. Sai / hơi sai get identity prompts appended.
"""
from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from generate_food_image_prompts import BASE, BASE_MEAT, is_meat, meat_parts, part_desc
from publish_food_catalog_images import (
    MEDIA_FOODS,
    MISSING_OUT,
    load_catalog,
    load_map,
    save_as_jpeg,
    update_db,
    write_merged_map,
    write_missing_list,
)

SOURCE = Path(r"C:\Users\Tran Tai\Downloads\gemini-folder-1")
PROMPT_FILE = Path(r"C:\Users\Tran Tai\Downloads\prompts-sai-hai-san-5.txt")
FILE_RE = re.compile(r"^(\d{3})_(\d{1,3})-.*\.(jfif|jpe?g|png|webp)$", re.IGNORECASE)

DUNG_STTS = frozenset()

SAI_ITEMS: list[tuple[int, str]] = [
    (
        238,
        "FIFTH TIME still a cichlid/tilapia shape: pointed snout, smooth gill cover, even if olive-brown "
        "with a tail spot. Search photo: 'Anabas testudineus climbing perch gill spine'. Cá rô đồng MUST "
        "show a HARD SERRATED OPERCULAR SPINE sticking out of the gill cover (the #1 ID you can see from "
        "the side), olive-brown hard scales, compact body, very spiny dorsal AND anal, short blunt snout. "
        "RAW. NOT cá rô phi, NOT tilapia, NOT snakehead.",
    ),
    (
        248,
        "This round is LIZARDFISH / cá mối: pointed snout, eyes on the SIDE of the head, small thin fillets. "
        "Search photo: 'cá kèo Pseudapocryptes elongatus'. Cá kèo has a FLAT mudskipper-like head, tiny eyes "
        "on TOP looking upward, a brown PENCIL body 8–10 times longer than the head is wide. FRONT = thin "
        "small fillets matching that small fish. RAW. NOT cá mối, NOT cá bống, NOT snakehead.",
    ),
    (
        298,
        "FIFTH TIME still cá chim / pompano: large deep silver body, yellow fins, and a THICK STEAK. "
        "Cá liệt is PONYFISH (Leiognathidae): SMALL, about 3–4 fingers long, very compressed rhomboid/"
        "spindle silver body, scaleless head, mouth that protrudes DOWNWARD. FRONT = small thin fillets, "
        "never a steak. RAW. NOT cá chim, NOT Pampus, NOT Trachinotus. Search: 'Leiognathus equulus cá liệt'.",
    ),
]

RAW_SEAFOOD = (
    "CRITICAL: both states are RAW fresh uncooked Vietnamese wet-market seafood/eggs — "
    "never cooked, never grilled, never fried, never steamed, no sauce, no garnish, no plate. "
)


def group_of(item: dict) -> str:
    for tag in item.get("tags") or []:
        text = str(tag)
        if text.startswith("nhom_vi:"):
            return text.split(":", 1)[1]
    return str(item.get("category_slug") or "")


def sheet_of(item: dict) -> str:
    cat = str(item.get("category_slug") or "")
    if cat == "rau-cu-qua":
        return "1_Rau_Cu_Qua"
    if "thit" in cat or "noi-tang" in cat or "gia-cam" in cat:
        return "2_Thit_GiaSuc_GiaCam_NoiTang"
    if cat == "ca-thuy-hai-san":
        return "3_Ca_ThuyHaiSan"
    if cat == "trung-whey":
        return "6_Trung_Sua_Whey"
    return ""


def collect_dung(catalog: list[dict]) -> list[tuple[int, Path, str, str]]:
    rows: list[tuple[int, Path, str, str]] = []
    seen: set[int] = set()
    hashes: dict[str, int] = {}
    for path in sorted(SOURCE.iterdir(), key=lambda p: p.name):
        if not path.is_file():
            continue
        match = FILE_RE.match(path.name)
        if not match:
            continue
        stt = int(match.group(2))
        if stt not in DUNG_STTS:
            continue
        if stt in seen:
            raise SystemExit(f"duplicate STT {stt}: {path.name}")
        digest = hashlib.md5(path.read_bytes()).hexdigest()
        if digest in hashes:
            raise SystemExit(f"duplicate image hash {digest} STT {hashes[digest]} and {stt}")
        hashes[digest] = stt
        if stt < 1 or stt > len(catalog):
            raise SystemExit(f"STT {stt} out of catalog range")
        slug = str(catalog[stt - 1]["slug"])
        seen.add(stt)
        rows.append((stt, path, slug, f"foods/{slug}.jpg"))
    missing = sorted(DUNG_STTS - seen)
    if missing:
        raise SystemExit(f"correct STTs have no file: {missing}")
    return rows


def build_sai_prompt(stt: int, catalog: list[dict], identity: str) -> str:
    item = catalog[stt - 1]
    name = str(item.get("name_vi") or item.get("name") or "")
    group = group_of(item)
    food = {"name": name, "group": group, "sheet": sheet_of(item)}
    if is_meat(group, name):
        base = BASE_MEAT
        extra = ""
        p2_front, p1_back = meat_parts(name)
    else:
        base = BASE
        extra = RAW_SEAFOOD
        p2_front, p1_back = part_desc(food)
    return (
        f"[{stt}] {name} ({group})\n"
        f'Create a professional realistic product photo of Vietnamese food item "{name}". {base} '
        f"{extra}"
        f"IDENTITY CRITICAL — previous images were WRONG: {identity} "
        f"{p2_front} {p1_back} "
        "The two food objects must stand closely next to each other in one continuous scene, "
        "with Part 2 clearly closer to the camera than Part 1. "
        "Use the most suitable 3/4 (or best clarifying) camera angle so shape and structure are obvious. "
        "Photorealistic commercial catalog look suitable for a fitness/nutrition website food database."
    )


def write_sai_prompts(catalog: list[dict]) -> int:
    prompts = [build_sai_prompt(stt, catalog, ident) for stt, ident in SAI_ITEMS]
    PROMPT_FILE.write_text("\n\n".join(prompts) + "\n", encoding="utf-8")
    return len(prompts)


def main() -> None:
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")
    if not SOURCE.is_dir():
        raise SystemExit(f"missing folder: {SOURCE}")
    catalog = load_catalog()
    rows = collect_dung(catalog)
    mapping = load_map()
    old = len(mapping)
    print(f"publishing {len(rows)} chắc chắn photos from {SOURCE}")
    if rows:
        MEDIA_FOODS.mkdir(parents=True, exist_ok=True)
        for stt, src, slug, rel in rows:
            save_as_jpeg(src, MEDIA_FOODS / f"{slug}.jpg")
            mapping[slug] = rel
            print(f"  {stt:3d} → {rel}")
        write_merged_map(catalog, mapping)
        print(f"wrote seeds/food_images.json ({old} → {len(mapping)} slugs)")
        updated = update_db({slug: rel for _stt, _src, slug, rel in rows})
        print(f"updated {updated} foods.image_url rows")
        missing_n = write_missing_list(catalog, mapping, MISSING_OUT)
        print(f"wrote {MISSING_OUT} ({missing_n} foods without photo)")
    else:
        print("no chắc chắn photos — skipped media/map/DB")
    n_prompts = write_sai_prompts(catalog)
    print(f"wrote {n_prompts} sai/hơi-sai prompts → {PROMPT_FILE}")


if __name__ == "__main__":
    main()
