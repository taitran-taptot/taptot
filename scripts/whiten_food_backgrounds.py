# -*- coding: utf-8 -*-
"""Flatten studio gray/shadow backgrounds on food catalog photos to solid white."""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
MEDIA = ROOT / "uploads" / "media" / "foods"


def corner_bg(rgb: np.ndarray) -> np.ndarray:
    h, w, _ = rgb.shape
    bh, bw = max(8, h // 20), max(8, w // 20)
    patches = np.concatenate(
        [
            rgb[:bh, :bw].reshape(-1, 3),
            rgb[:bh, -bw:].reshape(-1, 3),
            rgb[-bh:, :bw].reshape(-1, 3),
            rgb[-bh:, -bw:].reshape(-1, 3),
        ]
    )
    return np.median(patches, axis=0).astype(np.float32)


def composite_white(original: Image.Image, cut: Image.Image) -> Image.Image:
    rgb = np.asarray(original.convert("RGB"), dtype=np.float32)
    if cut.mode != "RGBA":
        cut = cut.convert("RGBA")
    alpha = np.asarray(cut)[..., 3].astype(np.float32)
    bg = corner_bg(rgb)
    paper = np.sqrt(((rgb - bg) ** 2).sum(axis=2)) < 18.0
    alpha = np.where(paper & (alpha < 250), 0.0, alpha)
    mask = Image.fromarray(np.clip(alpha, 0, 255).astype(np.uint8), "L")
    mask = mask.filter(ImageFilter.MinFilter(3))
    mask = mask.filter(ImageFilter.GaussianBlur(radius=0.7))
    a = np.asarray(mask, dtype=np.float32) / 255.0
    a = np.clip((a - 0.08) / 0.84, 0.0, 1.0)[..., None]
    fg = np.clip((rgb - (1.0 - a) * bg) / np.clip(a, 1e-4, 1.0), 0, 255)
    out = fg * a + 255.0 * (1.0 - a)
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGB")


def process_file(src: Path, dest: Path, session) -> None:
    from rembg import remove

    with Image.open(src) as im:
        original = im.convert("RGB")
        cut = remove(original, session=session)
        out = composite_white(original, cut)
    dest.parent.mkdir(parents=True, exist_ok=True)
    out.save(dest, "JPEG", quality=93, optimize=True, subsampling=1)


def main() -> None:
    import argparse

    from rembg import new_session

    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", action="store_true")
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()

    session = new_session("u2net")
    sample = [
        "gao-nep.jpg",
        "gao-te.jpg",
        "gao-lut.jpg",
        "yen-mach.jpg",
        "hat-dieu.jpg",
        "hat-huong-duong.jpg",
        "bap-gio-heo-chan-gio-truoc.jpg",
        "toi-co-don.jpg",
        "nam-rom.jpg",
        "cai-thia-cai-chip.jpg",
        "tao-tay-envy-fuji.jpg",
        "hanh-tim-kho.jpg",
    ]
    if args.sample:
        dest_dir = ROOT / "tmp" / "food-bg-white"
        for name in sample:
            src = MEDIA / name
            if src.exists():
                process_file(src, dest_dir / name, session)
                print("sample", name)
        return
    if not args.all:
        raise SystemExit("use --sample or --all")
    files = sorted(MEDIA.glob("*.jpg"))
    for i, src in enumerate(files, 1):
        process_file(src, src, session)
        if i % 10 == 0 or i == len(files):
            print(f"{i}/{len(files)} {src.name}", flush=True)


if __name__ == "__main__":
    main()
