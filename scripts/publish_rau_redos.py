#!/usr/bin/env python3
"""Publish audited-correct photos from Downloads/rau (filename STT = second number)."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from generate_food_image_prompts import BASE, part_desc
from publish_food_catalog_images import (
    MAP_PATH,
    MEDIA_FOODS,
    MISSING_OUT,
    load_catalog,
    load_map,
    save_as_jpeg,
    update_db,
    write_merged_map,
    write_missing_list,
)

SOURCE = Path(r"C:\Users\Tran Tai\Downloads\rau")
PROMPT_FILE = Path(r"C:\Users\Tran Tai\Downloads\prompts-thit-tu-158.txt")
FILE_RE = re.compile(r"^(\d{3})_(\d{2,3})-.*\.(jfif|jpe?g|png|webp)$", re.IGNORECASE)

# Visual audit of Downloads/rau: filename is source of truth; only publish chắc chắn.
DUNG_STTS = frozenset(
    {
        10,
        26,
        31,
        37,
        38,
        53,
        56,
        57,
        58,
        59,
        60,
        64,
        74,
        83,
        84,
        87,
        88,
        89,
        90,
        92,
        94,
        97,
        101,
        105,
        116,
        125,
        137,
        139,
        141,
        142,
        144,
        147,
        157,
    }
)

# Sai / hơi sai / chưa có file — regenerate.
SAI_ITEMS: list[tuple[int, str, str, str]] = [
    (4, "Rau đay đỏ", "Rau Mùa Hè", "RED-STEMMED Vietnamese jute mallow (Corchorus), reddish petioles and leaf veins, NOT regular green jute, NOT amaranth/rau dền."),
    (11, "Mướp khía", "Rau Mùa Hè", "Luffa acutangula / angled luffa: long green gourd with SHARP prominent longitudinal RIDGES (8–10 ridges), NOT leafy greens, NOT smooth sponge gourd/mướp hương, NOT bitter melon."),
    (13, "Mướp đắng / Khổ qua", "Rau Mùa Hè", "Bitter melon (Momordica charantia): oblong green fruit with densely WARTY bumpy blistered skin, NOT smooth luffa, NOT ridge gourd."),
    (14, "Bầu sao", "Rau Mùa Hè", "Vietnamese star bottle gourd (bầu sao): pale green bottle/calabash gourd; cut must show STAR-shaped cross-section, NOT luffa, NOT pumpkin."),
    (16, "Bí đỏ non / Bí bao tử", "Rau Mùa Hè", "Baby pumpkin / immature winter squash: small round or slightly flattened pumpkin, green-to-orange skin, orange flesh if cut. NOT a long green luffa."),
    (21, "Rau càng cua", "Rau Mùa Hè", "Peperomia pellucida (rau càng cua): small shiny succulent heart-shaped leaves on juicy stems, sold as a fresh herb bunch. ONLY the raw herb — NO salad, NO peanuts, NO chili, NO onion, NO dressing."),
    (40, "Cải bẹ xanh / Cải cay", "Rau Mùa ĐôngXuân", "Vietnamese mustard greens (Brassica juncea): elongated slightly wrinkled/ruffled mustard leaves, thin petioles, NOT bok choy/cải thìa with swollen white spoon stems."),
    (52, "Cần nước ta", "Rau Mùa ĐôngXuân", "Vietnamese water celery (Oenanthe javanica / cần nước): thin hollow stems, small pinnate herb leaflets, sold as a leafy bunch. NOT thick Western celery stalks (cần tây)."),
    (54, "Rau mầm đá", "Rau Mùa ĐôngXuân", "Ice plant (Mesembryanthemum / rau mầm đá): succulent leaves covered with glistening ice-like bladder cells. NOT a leafy cabbage rosette, NOT kale."),
    (77, "Nấm rơm", "Rau Quanh Năm", "Vietnamese straw mushroom (Volvariella volvacea / nấm rơm): small egg-shaped gray-brown mushrooms, often still in the volva/egg stage or a small cluster. NOT king oyster, NOT cremini, NOT large single button mushrooms."),
    (98, "Củ dong riềng", "Củ Tinh Bột", "Arrowroot / Canna edulis rhizome: elongated segmented rhizome with distinct RING-like nodes/scales, white starchy flesh. NOT a round taro, NOT cassava."),
    (99, "Củ sắn / Khoai mì", "Củ Tinh Bột", "Cassava / manioc: LONG cylindrical woody root with thick rough brown bark-like peel and white fibrous flesh. NOT a short round taro corm."),
    (100, "Củ mài / Hoài sơn", "Củ Tinh Bột", "Chinese yam (Dioscorea / củ mài): LONG slender hairy cylindrical tuber, white slightly slimy flesh. NOT a round taro, NOT a short fat yam."),
    (104, "Hành tím khô", "Củ Gia Vị", "Vietnamese shallot (hành tím): SMALL elongated teardrop purple-red shallots, often in a cluster, papery purple skin. NOT a large round red onion (hành tây đỏ)."),
    (106, "Tỏi cô đơn", "Củ Gia Vị", "Solo / single-clove garlic (tỏi cô đơn): round bulb that is ONE single clove with no internal clove segments when cut. NOT a normal multi-clove garlic bulb."),
    (108, "Củ kiệu", "Củ Gia Vị", "Kiệu (Allium chinense): small elongated white-lavender allium bulbs with green shoots, sold in a bunch like tiny scallion bulbs. NOT a large onion, NOT garlic."),
    (111, "Hành tăm / Củ nén", "Củ Gia Vị", "Củ nén / hành tăm: very small elongated pinkish-white allium bulbs, much smaller than shallots. NOT yellow storage onions (hành tây)."),
    (114, "Gừng gió", "Củ Gia Vị", "Wild/shampoo ginger (Zingiber zerumbet / gừng gió): paler smoother rhizome than common ginger, often more yellow-cream inside, distinct from knobby supermarket ginger (gừng thường)."),
    (119, "Địa liền", "Củ Gia Vị", "Sand ginger / Kaempferia galanga (địa liền): small roundish flattened aromatic rhizomes. NOT long finger galangal (riềng / Alpinia)."),
    (158, "Bơ sáp", "Quả Béo Tốt", "Vietnamese bơ sáp avocado: LARGE smooth thin GREEN skin (not bumpy dark Hass), creamy pale yellow-green flesh, large seed. NOT Hass avocado with thick pebbled black-green skin."),
]


def collect_dung(catalog: list[dict]) -> list[tuple[int, Path, str, str]]:
    rows: list[tuple[int, Path, str, str]] = []
    seen: set[int] = set()
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
        if stt < 1 or stt > len(catalog):
            raise SystemExit(f"STT {stt} out of catalog range")
        slug = str(catalog[stt - 1]["slug"])
        seen.add(stt)
        rows.append((stt, path, slug, f"foods/{slug}.jpg"))
    missing = sorted(DUNG_STTS - seen)
    if missing:
        raise SystemExit(f"correct STTs have no file: {missing}")
    return rows


def build_sai_prompt(stt: int, name: str, group: str, identity: str) -> str:
    food = {"name": name, "group": group, "sheet": "1_Rau_Cu_Qua"}
    p2_front, p1_back = part_desc(food)
    return (
        f"[{stt}] {name} ({group})\n"
        f'Create a professional realistic product photo of Vietnamese food item "{name}". {BASE} '
        f"IDENTITY CRITICAL — previous images were WRONG: {identity} "
        f"{p2_front} {p1_back} "
        "The two food objects must stand closely next to each other in one continuous scene, "
        "with Part 2 clearly closer to the camera than Part 1. "
        "Use the most suitable 3/4 (or best clarifying) camera angle so shape and structure are obvious. "
        "Photorealistic commercial catalog look suitable for a fitness/nutrition website food database."
    )


def append_sai_prompts() -> int:
    prompts = [build_sai_prompt(stt, name, group, ident) for stt, name, group, ident in SAI_ITEMS]
    existing = PROMPT_FILE.read_text(encoding="utf-8").rstrip() if PROMPT_FILE.is_file() else ""
    block = "\n\n".join(prompts)
    PROMPT_FILE.write_text(existing + "\n\n" + block + "\n", encoding="utf-8")
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
    MEDIA_FOODS.mkdir(parents=True, exist_ok=True)
    for stt, src, slug, rel in rows:
        save_as_jpeg(src, MEDIA_FOODS / f"{slug}.jpg")
        mapping[slug] = rel
        print(f"  {stt:3d} → {rel}")
    write_merged_map(catalog, mapping)
    print(f"wrote {MAP_PATH.relative_to(ROOT)} ({old} → {len(mapping)} slugs)")
    updated = update_db(mapping)
    print(f"updated {updated} foods.image_url rows")
    missing_n = write_missing_list(catalog, mapping, MISSING_OUT)
    print(f"wrote {MISSING_OUT} ({missing_n} foods without photo)")
    n_prompts = append_sai_prompts()
    print(f"appended {n_prompts} sai/hơi-sai prompts → {PROMPT_FILE}")


if __name__ == "__main__":
    main()
