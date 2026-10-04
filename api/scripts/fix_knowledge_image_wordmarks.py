"""Wipe ALL top-left TAPTOT remnants, then draw one correct wordmark."""

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

# frontend/src/lib/brand.ts
T1 = (0x10, 0xB9, 0x81)
T2 = (0x22, 0xC5, 0x5E)
INK = (0x0F, 0x17, 0x2A)
WHITE = (255, 255, 255)
SEGMENTS = (("T", T1), ("AP", INK), ("T", T2), ("OT", INK))
FONT = Path(r"C:\Windows\Fonts\arialbd.ttf")
OUT_SUFFIX = "-brandfix2"
MD_ROOT = API_DIR / "app" / "data" / "knowledge"


def draw_wordmark(draw: ImageDraw.ImageDraw, origin: tuple[int, int], font: ImageFont.ImageFont) -> tuple[int, int]:
    x, y = origin
    base = draw.textbbox((0, 0), "T", font=font)
    y_adj = -base[1]
    cursor = x
    max_bottom = y
    for text, color in SEGMENTS:
        draw.text((cursor, y + y_adj), text, font=font, fill=color)
        bb = draw.textbbox((cursor, y + y_adj), text, font=font)
        cursor = bb[2]
        max_bottom = max(max_bottom, bb[3])
    return cursor - x, max_bottom - y


def hard_wipe_and_brand(path: Path, dest: Path) -> str:
    im = Image.open(path).convert("RGB")
    w, h = im.size
    draw = ImageDraw.Draw(im)

    # Aggressive corner wipe — covers old AI logos + previous leftover fragments
    wipe_right = int(w * 0.42)
    wipe_bottom = int(h * 0.155)  # ~119px on 768 — below ghost fragments
    draw.rectangle([0, 0, wipe_right, wipe_bottom], fill=WHITE)

    font_size = max(36, int(h * 0.05))
    font = ImageFont.truetype(str(FONT), font_size)
    tw, th = draw_wordmark(draw, (18, 14), font)

    dest.parent.mkdir(parents=True, exist_ok=True)
    im.save(dest, format="PNG", optimize=True)

    # verify: no ink in band under wordmark inside wipe (ghost check)
    ghost = 0
    y0 = 14 + th + 4
    for y in range(y0, wipe_bottom):
        for x in range(0, wipe_right):
            r, g, b = im.getpixel((x, y))
            if r < 250 or g < 250 or b < 250:
                ghost += 1
    return f"{dest.parent.name}/{dest.name} wipe={wipe_right}x{wipe_bottom} word={tw}x{th} ghost_below={ghost}"


def update_markdown_and_db(url_map: dict[str, str]) -> None:
    """url_map: old path fragment -> new full /media/... path"""
    changed: dict[str, str] = {}
    for md in MD_ROOT.glob("*.md"):
        text = md.read_text(encoding="utf-8")
        new = text
        for old_frag, new_url in url_map.items():
            new = re.sub(
                rf"/media/knowledge/{re.escape(old_frag)}(?:\?[^)\s]*)?",
                new_url,
                new,
            )
        if new != text:
            md.write_text(new if new.endswith("\n") else new + "\n", encoding="utf-8")
            changed[md.stem] = new

    db = SessionLocal()
    try:
        for slug, content in changed.items():
            row = db.scalar(select(KnowledgeArticle).where(KnowledgeArticle.slug == slug))
            if row:
                row.content_md = content
                print("db", slug)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    # Prefer reinstall from gemini then brand — call install first externally,
    # or operate on current *-brandfix.png / originals.
    media = Path(get_settings().upload_dir).resolve() / "media" / "knowledge"
    url_map: dict[str, str] = {}

    sources = sorted(media.rglob("*.png"))
    if not sources:
        raise SystemExit("No knowledge PNGs found")

    for src in sources:
        # normalize to brandfix2
        stem = src.stem
        for s in ("-brandfix2", "-brandfix"):
            if stem.endswith(s):
                stem = stem[: -len(s)]
        dest = src.with_name(stem + OUT_SUFFIX + ".png")
        # work from current pixels (already has content); wipe corner again
        msg = hard_wipe_and_brand(src, dest)
        print("fix", msg)
        if src != dest and src.exists():
            src.unlink()
        old_keys = [
            f"{src.parent.name}/{stem}.png",
            f"{src.parent.name}/{stem}-brandfix.png",
            f"{src.parent.name}/{stem}-brandfix2.png",
        ]
        new_url = f"/media/knowledge/{dest.parent.name}/{dest.name}?v=2"
        for k in old_keys:
            url_map[k] = new_url

    update_markdown_and_db(url_map)
    print("Done. Wordmark T=#10B981 AP=#0F172A T=#22C55E OT=#0F172A")


if __name__ == "__main__":
    main()
