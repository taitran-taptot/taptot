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
        print(f"OK {key} <= {src.name[:70]}")
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
