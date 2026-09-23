"""Convert Gemini pantry photos (001-056) to uploads/media/foods/{slug}.jpg."""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SRC = Path(r"C:\Users\Tran Tai\Downloads\gemini-folder-1")
DEST = ROOT / "uploads" / "media" / "foods"
IMAGES_JSON = ROOT / "seeds" / "food_images.json"

SLUGS = [
    "nuoc-mam",
    "nuoc-tuong",
    "mam-tom",
    "mam-ruoc",
    "dau-an",
    "duong-cat",
    "muoi",
    "tieu-den",
    "ot-hiem",
    "giam-gao",
    "toi",
    "hanh-tim",
    "sa",
    "gung",
    "rieng",
    "nghe",
    "la-lot",
    "la-chanh",
    "ngo-om",
    "bac-ha-rau",
    "thi-la",
    "kinh-gioi",
    "toi-tay",
    "can-tay",
    "chanh-ta",
    "sau-xanh",
    "ngo-gai",
    "cua-dong",
    "hen",
    "luon",
    "ca-linh",
    "thit-trau",
    "chan-gio-heo",
    "xuong-ong-bo",
    "canh-ga",
    "long-heo",
    "gan-heo",
    "gau-bo",
    "gio-bo",
    "bi-heo",
    "cha-trung",
    "pate-gan",
    "cha-lua",
    "trung-muoi",
    "banh-mi",
    "banh-trang",
    "hu-tieu",
    "bot-gao",
    "bot-nang",
    "dau-xanh",
    "dau-phong",
    "nuoc-dua-tuoi",
    "banh-hoi",
    "banh-da",
    "soi-banh-canh",
    "mi-quang",
]

SKIP = {
    "ngo-om",
    "chanh-ta",
    "cha-trung",
    "nuoc-dua-tuoi",
    "soi-banh-canh",
    # Live catalog already has these ingredients — do not publish Gemini as a second Food.
    "toi",
    "toi-tay",
    "hanh-tim",
    "gung",
    "rieng",
    "nghe",
    "can-tay",
    "hen",
    "luon",
    "ca-linh",
    "chan-gio-heo",
    "canh-ga",
    "bac-ha-rau",
    "ngo-gai",
    "gau-bo",
    "gio-bo",
}


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
    if len(files) != 56:
        raise SystemExit(f"expected 56 jfif, found {len(files)}")
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
