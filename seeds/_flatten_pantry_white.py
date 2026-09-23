"""Preview two white-background methods for published Gemini pantry JPEGs.

A) Pillow: flood-fill light low-chroma pixels connected to the border.
B) rembg: cut out the subject and paste onto #FFFFFF.

Writes uploads/media/_white_preview/{original,pillow,rembg}/ — not for commit.
"""
from __future__ import annotations

import shutil
from collections import deque
from pathlib import Path

from PIL import Image, ImageFilter

from _publish_cooking_gemini import SKIP, SLUGS

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "uploads" / "media" / "foods"
PREVIEW = ROOT / "uploads" / "media" / "_white_preview"
ORIG = PREVIEW / "original"
PILLOW_DIR = PREVIEW / "pillow"
REMBG_DIR = PREVIEW / "rembg"

TARGET = (1920, 1080)
WHITE = (255, 255, 255)


def published_slugs() -> list[str]:
    return [slug for slug in SLUGS if slug not in SKIP]


# Pale / glass / liquid: Pillow eats the subject or leaves holes.
FORCE_REMBG = {
    "nuoc-mam",
    "nuoc-tuong",
    "dau-an",
    "giam-gao",
    "muoi",
    "duong-cat",
    "bot-gao",
    "bot-nang",
    "banh-hoi",
    "banh-trang",
    "banh-mi",
    "hu-tieu",
    "mi-quang",
    "dau-xanh",
    "banh-da",
}


def subject_pixels(path: Path) -> int:
    with Image.open(path) as im:
        rgb = im.convert("RGB")
        count = 0
        for r, g, b in rgb.getdata():
            if min(r, g, b) < 248 or (max(r, g, b) - min(r, g, b)) > 6:
                count += 1
        return count


def pick_source(slug: str) -> Path:
    pillow = PILLOW_DIR / f"{slug}.jpg"
    rembg = REMBG_DIR / f"{slug}.jpg"
    if slug in FORCE_REMBG:
        return rembg
    p_n = subject_pixels(pillow)
    r_n = subject_pixels(rembg) or 1
    if p_n >= 0.78 * r_n:
        return pillow
    return rembg


def apply_winners() -> None:
    dest_dir = SRC_DIR
    for slug in published_slugs():
        chosen = pick_source(slug)
        if not chosen.is_file():
            print(f"skip {slug}: missing {chosen}")
            continue
        method = chosen.parent.name
        shutil.copy2(chosen, dest_dir / f"{slug}.jpg")
        print(f"{slug}\t{method}")


def flatten_pillow(im: Image.Image) -> Image.Image:
    rgb = im.convert("RGB")
    w, h = rgb.size
    px = rgb.load()
    bg = bytearray(w * h)  # 1 = background candidate
    visited = bytearray(w * h)

    def idx(x: int, y: int) -> int:
        return y * w + x

    def is_bg(x: int, y: int) -> bool:
        r, g, b = px[x, y]
        chroma = max(r, g, b) - min(r, g, b)
        luma = (r + g + b) / 3.0
        # Light gray / off-white studio + soft contact shadows.
        return luma >= 168 and chroma <= 28

    q: deque[tuple[int, int]] = deque()
    for x in range(w):
        q.append((x, 0))
        q.append((x, h - 1))
    for y in range(h):
        q.append((0, y))
        q.append((w - 1, y))

    while q:
        x, y = q.popleft()
        i = idx(x, y)
        if visited[i]:
            continue
        visited[i] = 1
        if not is_bg(x, y):
            continue
        bg[i] = 1
        if x > 0:
            q.append((x - 1, y))
        if x + 1 < w:
            q.append((x + 1, y))
        if y > 0:
            q.append((x, y - 1))
        if y + 1 < h:
            q.append((x, y + 1))

    mask = Image.new("L", (w, h))
    mask_px = mask.load()
    for y in range(h):
        row = y * w
        for x in range(w):
            mask_px[x, y] = 255 if bg[row + x] else 0
    # Soften the cut so shadows fade instead of leaving a halo.
    mask = mask.filter(ImageFilter.GaussianBlur(radius=2.4))
    white = Image.new("RGB", (w, h), WHITE)
    return Image.composite(white, rgb, mask)


def flatten_rembg(im: Image.Image, session) -> Image.Image:
    from rembg import remove

    cut = remove(im.convert("RGBA"), session=session)
    canvas = Image.new("RGBA", cut.size, (*WHITE, 255))
    canvas.alpha_composite(cut)
    return canvas.convert("RGB")


def save_jpeg(im: Image.Image, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if im.size != TARGET:
        im = im.resize(TARGET, Image.Resampling.LANCZOS)
    im.save(dest, "JPEG", quality=92, optimize=True)


def main() -> None:
    slugs = published_slugs()
    for folder in (ORIG, PILLOW_DIR, REMBG_DIR):
        folder.mkdir(parents=True, exist_ok=True)

    session = None
    try:
        from rembg import new_session

        session = new_session("u2net")
    except Exception as exc:  # noqa: BLE001
        print(f"rembg unavailable: {exc}")

    for slug in slugs:
        src = SRC_DIR / f"{slug}.jpg"
        if not src.is_file():
            print(f"missing {slug}")
            continue
        shutil.copy2(src, ORIG / src.name)
        with Image.open(src) as im:
            im = im.convert("RGB")
            save_jpeg(flatten_pillow(im), PILLOW_DIR / src.name)
            if session is not None:
                save_jpeg(flatten_rembg(im, session), REMBG_DIR / src.name)
        print(f"ok {slug}")


if __name__ == "__main__":
    import sys

    if "--apply" in sys.argv:
        apply_winners()
    else:
        main()
