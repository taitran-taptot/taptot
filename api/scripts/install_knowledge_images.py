"""Install knowledge article images from gemini-folder-1 and swap pending: markers."""

from __future__ import annotations

import re
import sys
from pathlib import Path

API_DIR = Path(__file__).resolve().parents[1]
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from PIL import Image
from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.entities import KnowledgeArticle

SRC = Path(r"C:/Users/Tran Tai/Downloads/gemini-folder-1")
MD_ROOT = API_DIR / "app" / "data" / "knowledge"
MEDIA_ROOT = Path(get_settings().upload_dir).resolve() / "media" / "knowledge"

# Prefer the corrected re-gens; skip superseded files by exact name stem prefixes.
INSTALL: list[tuple[str, str, str, str]] = [
    # (match_substring_in_filename, slug, key, alt)
    ("001_11-doc-lich", "cach-doc-lich-tap-quy-uoc-buoi-tap", "set-decoder-card", "3 × 8–10, nghỉ 90 giây, tempo 2-0-1"),
    ("002_113-rir", "tu-dien-thuat-ngu-tap-luyen-cho-nguoi-moi", "rir-scale", "Bắt đầu ở RIR 2. Khi đã giữ được kỹ thuật, có thể dùng khoảng RIR 1–3."),
    ("003_114-mau", "mau-van-dong-va-cach-tang-giam-do-kho-bai-tap", "movement-patterns", "Sáu mẫu: squat, hinge, lunge, push, pull, carry."),
    ("004.jfif", "ky-thuat-tap-chuan-form-an-toan-co-xuong-khop", "form-cues", "Gồng thân, hướng gối và khoảng khuỷu."),
    ("005_111-ban-tay", "dinh-duong-da-luong-chat-dam-protein-tinh-bot-carb-va-chat-beo-fat", "hand-portion", "Một bữa bắt đầu với lòng bàn tay."),
    ("006_19-nang-luong", "nang-luong-va-can-nang-tham-hut-thang-du-va-can-bang-calo", "energy-balance", "Thâm hụt, cân bằng và thặng dư."),
    ("007_17-doms", "dau-moi-co-doms-va-chan-thuong-cach-phan-biet-va-xu-ly", "doms-vs-stop", "Mỏi lan tỏa thường là DOMS. Đau nhói thì dừng."),
]


def find_src(substr: str) -> Path:
    matches = [p for p in SRC.iterdir() if substr in p.name]
    if not matches:
        raise FileNotFoundError(f"No image matching: {substr!r}")
    # newest if multiple
    matches.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return matches[0]


def save_png(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(src) as im:
        rgb = im.convert("RGB")
        rgb.save(dest, format="PNG", optimize=True)


def replace_pending(content: str, key: str, slug: str, alt: str) -> str:
    url = f"/media/knowledge/{slug}/{key}.png"
    pattern = re.compile(rf"!\[([^\]]*)\]\(pending:{re.escape(key)}\)")
    if pattern.search(content):
        return pattern.sub(lambda m: f"![{m.group(1) or alt}]({url})", content)
    # already real url?
    if url in content:
        return content
    raise ValueError(f"pending:{key} not found in {slug}")


def main() -> None:
    updated_slugs: set[str] = set()
    for substr, slug, key, alt in INSTALL:
        src = find_src(substr)
        dest = MEDIA_ROOT / slug / f"{key}.png"
        save_png(src, dest)
        print(f"OK {key} <= {src.name[:70].encode('ascii', 'replace').decode()}")
        print(f"   -> {dest}")

        md_path = MD_ROOT / f"{slug}.md"
        text = md_path.read_text(encoding="utf-8")
        text = replace_pending(text, key, slug, alt)
        # also refresh alt for vif if still English-ish caption
        if key == "vif-three-dials":
            text = text.replace(
                f"![Volume · Intensity · Frequency]({f'/media/knowledge/{slug}/{key}.png'})",
                f"![{alt}](/media/knowledge/{slug}/{key}.png)",
            )
        md_path.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")
        updated_slugs.add(slug)

    # Upsert DB from md files for touched slugs
    db = SessionLocal()
    try:
        for slug in sorted(updated_slugs):
            md_path = MD_ROOT / f"{slug}.md"
            content = md_path.read_text(encoding="utf-8").strip() + "\n"
            row = db.scalar(select(KnowledgeArticle).where(KnowledgeArticle.slug == slug))
            if row is None:
                raise SystemExit(f"Missing article slug={slug}")
            if "pending:" in content:
                raise SystemExit(f"Still has pending in {slug}")
            row.content_md = content
            print(f"DB upsert content {slug}")
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    # verify no pending left in any knowledge md
    left = []
    for p in MD_ROOT.glob("*.md"):
        if "pending:" in p.read_text(encoding="utf-8"):
            left.append(p.name)
    print("pending remaining:", left or "none")


if __name__ == "__main__":
    main()
