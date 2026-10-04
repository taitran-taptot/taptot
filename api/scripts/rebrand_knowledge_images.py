"""Reinstall knowledge images from Gemini folder, wipe logo corner, draw correct TAPTOT."""

from __future__ import annotations

import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from sqlalchemy import select

API_DIR = Path(__file__).resolve().parents[1]
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.entities import KnowledgeArticle

SRC = Path(r"C:/Users/Tran Tai/Downloads/gemini-folder-1")
MD_ROOT = API_DIR / "app" / "data" / "knowledge"
MEDIA = Path(get_settings().upload_dir).resolve() / "media" / "knowledge"

T1, T2, INK = (0x10, 0xB9, 0x81), (0x22, 0xC5, 0x5E), (0x0F, 0x17, 0x2A)
WHITE = (255, 255, 255)
SEGMENTS = (("T", T1), ("AP", INK), ("T", T2), ("OT", INK))
FONT = Path(r"C:\Windows\Fonts\arialbd.ttf")
VERSION = "brandfix3"

# (filename substring, slug, key, alt)
INSTALL = [
    ("infographic-duy-nhất-nền-trắng-Logo-góc-ch", "cach-doc-lich-tap-quy-uoc-buoi-tap", "set-decoder-card", "Giải mã 3×8–10"),
    ("3D-duy-nhất-nền-trắng-tinh-Logo-góc-TAPTOT", "ban-do-cac-nhom-co-chinh-co-che-chuyen-dong", "muscle-heat-map", "Bản đồ nhóm cơ"),
    ("3D-hít-đất-nhìn-ngang", "ky-thuat-tap-chuan-form-an-toan-co-xuong-khop", "pushup-force-vectors", "Hít đất — hướng lực"),
    ("chia-đôi-plank-nhìn-ngang", "ky-thuat-tap-chuan-form-an-toan-co-xuong-khop", "plank-do-dont", "Plank: đúng vs sai"),
    ("3-thẻ-ngang-bằn", "ba-nut-chinh-khoi-luong-volume-do-nang-intensity-tan-suat-frequency", "vif-three-dials", "Khối lượng · Độ nặng · Tần suất"),
    ("kim-tự-tháp-5-tầng", "nguyen-tac-qua-tai-luy-tien-progressive-overload-co-ban", "overload-pyramid", "Kim tự tháp overload"),
    ("chia-đôi-ngồi-xổm", "dau-moi-co-doms-va-chan-thuong-cach-phan-biet-va-xu-ly", "squat-do-dont", "Squat: đúng vs sai"),
    ("3-cán-cân-ngang", "nang-luong-va-can-nang-tham-hut-thang-du-va-can-bang-calo", "energy-balance-scale", "Cán cân năng lượng"),
    ("biểu-đồ-tròn-duy-nhất", "cach-tinh-tdee-theo-muc-van-dong-thuc-te", "tdee-pie", "Cấu trúc TDEE"),
    ("4-icon-bàn-tay", "dinh-duong-da-luong-chat-dam-protein-tinh-bot-carb-va-chat-beo-fat", "hand-portion-guide", "Định lượng bàn tay"),
    ("thang-nỗ-lực-nền-trắng-logic-đúng", "rpe-va-rir-trong-tung-set", "rpe-rir-card", "Thang RPE / RIR"),
    ("đẩy-ngực-", "mind-muscle-connection-nang-cao", "mmc-target-heat", "Cơ mục tiêu MMC"),
]


def find_src(substr: str) -> Path:
    matches = [p for p in SRC.iterdir() if substr in p.name]
    if not matches:
        raise FileNotFoundError(substr)
    return max(matches, key=lambda p: p.stat().st_mtime)


def brand_image(src: Path, dest: Path) -> tuple[int, int, int]:
    with Image.open(src) as raw:
        im = raw.convert("RGB")
    w, h = im.size
    draw = ImageDraw.Draw(im)

    # Measure original top-left ink to size wipe
    x2, y2 = int(w * 0.40), int(h * 0.18)
    xs, ys = [], []
    px = im.load()
    for y in range(0, y2):
        for x in range(0, x2):
            r, g, b = px[x, y]
            if r < 245 or g < 245 or b < 245:
                xs.append(x)
                ys.append(y)
    if xs:
        wipe_r = min(x2, max(xs) + 24)
        wipe_b = min(y2, max(ys) + 24)
    else:
        wipe_r, wipe_b = int(w * 0.32), int(h * 0.12)

    # Always wipe at least enough to kill tall AI logos
    wipe_b = max(wipe_b, int(h * 0.12))
    wipe_b = min(wipe_b, int(h * 0.145))
    wipe_r = min(max(wipe_r, int(w * 0.30)), int(w * 0.42))

    draw.rectangle([0, 0, wipe_r, wipe_b], fill=WHITE)

    font = ImageFont.truetype(str(FONT), max(36, int(h * 0.05)))
    x, y = 18, 14
    base = draw.textbbox((0, 0), "T", font=font)
    y_adj = -base[1]
    cursor = x
    word_bottom = y
    for text, color in SEGMENTS:
        draw.text((cursor, y + y_adj), text, font=font, fill=color)
        bb = draw.textbbox((cursor, y + y_adj), text, font=font)
        cursor = bb[2]
        word_bottom = max(word_bottom, bb[3])

    # Second pass: erase ANY leftover ink under the new wordmark inside wipe box
    ghost = 0
    for yy in range(word_bottom + 2, wipe_b + 1):
        for xx in range(0, wipe_r + 1):
            r, g, b = im.getpixel((xx, yy))
            if r < 250 or g < 250 or b < 250:
                im.putpixel((xx, yy), WHITE)
                ghost += 1

    dest.parent.mkdir(parents=True, exist_ok=True)
    im.save(dest, format="PNG", optimize=True)
    return wipe_r, wipe_b, ghost


def main() -> None:
    # clear old knowledge media pngs
    if MEDIA.exists():
        for p in MEDIA.rglob("*.png"):
            p.unlink()

    slug_files: dict[str, list[tuple[str, str]]] = {}
    for substr, slug, key, alt in INSTALL:
        src = find_src(substr)
        dest = MEDIA / slug / f"{key}-{VERSION}.png"
        wr, wb, ghost = brand_image(src, dest)
        print(f"OK {key}: wipe={wr}x{wb} cleared_ghost_px={ghost} <= {src.name[:50]}")
        url = f"/media/knowledge/{slug}/{dest.name}?v=3"
        slug_files.setdefault(slug, []).append((key, alt, url))

    # rewrite image markdown lines for each slug
    db = SessionLocal()
    try:
        for slug, figs in slug_files.items():
            md_path = MD_ROOT / f"{slug}.md"
            text = md_path.read_text(encoding="utf-8")
            # replace any existing /media/knowledge/{slug}/... figure for known keys
            for key, alt, url in figs:
                pattern = re.compile(
                    rf"!\[([^\]]*)\]\(/media/knowledge/{re.escape(slug)}/[^\)]*{re.escape(key)}[^\)]*\)"
                )
                if pattern.search(text):
                    text = pattern.sub(f"![{alt}]({url})", text)
                else:
                    # insert after first --- if missing
                    if f"{key}" not in text:
                        text = text.replace("\n---\n", f"\n---\n\n![{alt}]({url})\n", 1)
            md_path.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")
            row = db.scalar(select(KnowledgeArticle).where(KnowledgeArticle.slug == slug))
            if row:
                row.content_md = md_path.read_text(encoding="utf-8")
                print("db", slug)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    # final ghost audit
    print("--- ghost audit (ink under wordmark, y=50..wipe) ---")
    for p in sorted(MEDIA.rglob("*.png")):
        im = Image.open(p).convert("RGB")
        ghost = 0
        for y in range(50, int(im.size[1] * 0.14)):
            for x in range(0, int(im.size[0] * 0.35)):
                r, g, b = im.getpixel((x, y))
                if r < 250 or g < 250 or b < 250:
                    ghost += 1
        print(f"{'CLEAN' if ghost == 0 else 'GHOST '+str(ghost):12} {p.parent.name}/{p.name}")


if __name__ == "__main__":
    main()
