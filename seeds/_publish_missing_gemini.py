"""Convert Gemini missing-food photos (001-020) to uploads/media/foods/{slug}.jpg."""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SRC = Path(r"C:\Users\Tran Tai\Downloads\gemini-folder-1")
DEST = ROOT / "uploads" / "media" / "foods"
IMAGES_JSON = ROOT / "seeds" / "food_images.json"

# Order matches FOODS_COOKING_IMAGE_PROMPTS_MISSING.md
SLUGS = [
    "bun-tuoi",
    "xa-lach",
    "thit-lon-xay-song",
    "nuoc-dua-tuoi",
    "suon-lon-song",
    "me-chin",
    "banh-pho-tuoi",
    "dau-phu-chac",
    "dui-ga-khong-da-song",
    "ngo-om",
    "moc-nhi-ngam-nuoc",
    "soi-banh-canh",
    "rau-day",
    "thit-vit-co-da",
    "cha-trung",
    "bap-ngot-luoc",
    "com-trang",
    "he",
    "mang-tuoi",
    "thit-de-nac-song",
]

# Gemini still generated a solid jelly/glass disc, not liquid coconut water.
SKIP = {"nuoc-dua-tuoi"}


def convert(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(src) as im:
        im = im.convert("RGB")
        w, h = im.size
        target_w, target_h = 1920, 1080
        scale = max(target_w / w, target_h / h)
        nw, nh = int(w * scale), int(h * scale)
        im = im.resize((nw, nh), Image.Resampling.LANCZOS)
        left = (nw - target_w) // 2
        top = (nh - target_h) // 2
        im = im.crop((left, top, left + target_w, top + target_h))
        im.save(dest, "JPEG", quality=90, optimize=True)


def main() -> None:
    files = sorted(SRC.glob("*.jfif"))
    if len(files) != len(SLUGS):
        raise SystemExit(f"expected {len(SLUGS)} jfif, found {len(files)}")
    written = 0
    for idx, (src, slug) in enumerate(zip(files, SLUGS, strict=True), start=1):
        if slug in SKIP:
            print(f"skip {idx:03d} {slug}")
            continue
        dest = DEST / f"{slug}.jpg"
        convert(src, dest)
        written += 1
        print(f"ok {idx:03d} {slug} -> {dest.name}")

    mapping = json.loads(IMAGES_JSON.read_text(encoding="utf-8"))
    for slug in SLUGS:
        if slug in SKIP:
            continue
        mapping[slug] = f"foods/{slug}.jpg"
    IMAGES_JSON.write_text(json.dumps(mapping, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {written} jpgs, updated {IMAGES_JSON.name}")


if __name__ == "__main__":
    main()
