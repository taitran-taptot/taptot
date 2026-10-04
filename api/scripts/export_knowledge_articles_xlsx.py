"""Export all knowledge articles from DB to Excel (api/exports/)."""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Any

API_DIR = Path(__file__).resolve().parents[1]
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.entities import KnowledgeArticle

HEADER = [
    "id",
    "slug",
    "title_vi",
    "level",
    "level_vi",
    "sort_order",
    "read_time_min",
    "is_published",
    "published_at",
    "seo_title",
    "seo_description",
    "content_md",
    "url_path",
]

LEVEL_ORDER = {
    "beginner": 0,
    "basic": 0,
    "intermediate": 1,
    "advanced": 2,
}

LEVEL_VI = {
    "beginner": "Cơ bản",
    "basic": "Cơ bản",
    "intermediate": "Trung cấp",
    "advanced": "Nâng cao",
}

HEADER_FILL = PatternFill("FF1F4E3D", fill_type="solid")
HEADER_FONT = Font(bold=True, color="FFFFFFFF")


def _iso(value: Any) -> str:
    if value is None:
        return ""
    if hasattr(value, "isoformat"):
        return value.isoformat(timespec="seconds")
    return str(value)


def _write_header(ws) -> None:
    ws.append(HEADER)
    for col, _ in enumerate(HEADER, start=1):
        cell = ws.cell(1, col)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
    ws.freeze_panes = "A2"


def _set_widths(ws) -> None:
    for col, title in enumerate(HEADER, start=1):
        letter = get_column_letter(col)
        if title == "content_md":
            width = 80
        elif title in {"title_vi", "seo_description", "seo_title"}:
            width = 40
        elif title in {"slug", "url_path"}:
            width = 32
        else:
            width = max(12, min(18, len(title) + 2))
        ws.column_dimensions[letter].width = width


def _wrap_content_column(ws) -> None:
    """Make full markdown readable in Excel (wrap + taller rows)."""
    content_col = HEADER.index("content_md") + 1
    for row_idx in range(2, ws.max_row + 1):
        cell = ws.cell(row_idx, content_col)
        cell.alignment = Alignment(wrap_text=True, vertical="top")
        ws.row_dimensions[row_idx].height = 80


def _row_for(article: KnowledgeArticle) -> list[Any]:
    level = (article.level or "").strip().lower()
    return [
        article.id,
        article.slug,
        article.title_vi,
        article.level,
        LEVEL_VI.get(level, article.level or ""),
        article.sort_order,
        article.read_time_min,
        bool(article.is_published),
        _iso(article.published_at),
        article.seo_title or "",
        article.seo_description or "",
        article.content_md or "",
        f"/kien-thuc/{article.slug}",
    ]


def _write_markdown_files(articles: list[KnowledgeArticle], md_dir: Path) -> None:
    """One .md file per article so full content is easy to open outside Excel."""
    md_dir.mkdir(parents=True, exist_ok=True)
    index_lines = [
        "# Kho kiến thức TAPTOT",
        "",
        f"Xuất {len(articles)} bài.",
        "",
    ]
    for article in articles:
        level = (article.level or "").strip().lower()
        level_vi = LEVEL_VI.get(level, article.level or "")
        title = (article.title_vi or article.slug).strip()
        body = (article.content_md or "").strip()
        if not body.startswith("#"):
            body = f"# {title}\n\n{body}"
        header = (
            f"slug: {article.slug}\n"
            f"level: {level_vi}\n"
            f"url: /kien-thuc/{article.slug}\n"
            f"read_time_min: {article.read_time_min or ''}\n"
            f"published: {bool(article.is_published)}\n\n"
        )
        (md_dir / f"{article.slug}.md").write_text(header + body + "\n", encoding="utf-8")
        index_lines.append(f"- [{title}]({article.slug}.md) — {level_vi}")
    index_lines.append("")
    (md_dir / "00-index.md").write_text("\n".join(index_lines), encoding="utf-8")


def export_articles(db: Session, out: Path) -> int:
    rows = list(db.query(KnowledgeArticle).all())
    rows.sort(
        key=lambda a: (
            LEVEL_ORDER.get((a.level or "").strip().lower(), 99),
            a.sort_order or 0,
            a.id or 0,
        )
    )

    wb = Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "articles"
    _write_header(ws)
    for article in rows:
        ws.append(_row_for(article))
    _set_widths(ws)
    _wrap_content_column(ws)
    out.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out)

    md_dir = out.with_suffix("")  # knowledge_articles_YYYYMMDD_HHMM/
    _write_markdown_files(rows, md_dir)
    return len(rows)


def main() -> Path:
    import shutil

    out_dir = Path(__file__).resolve().parents[1] / "exports"
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    out = out_dir / f"knowledge_articles_{stamp}.xlsx"
    db = SessionLocal()
    try:
        n = export_articles(db, out)
        md_dir = out.with_suffix("")
        desktop = Path.home() / "Desktop"
        desktop.mkdir(parents=True, exist_ok=True)
        xlsx_copy = desktop / out.name
        md_copy = desktop / md_dir.name
        shutil.copy2(out, xlsx_copy)
        if md_copy.exists():
            shutil.rmtree(md_copy)
        shutil.copytree(md_dir, md_copy)
        print(f"Exported {n} knowledge articles (full content_md in Excel + .md files)")
        print(out)
        print(md_dir)
        print(xlsx_copy)
        print(md_copy)
        return out
    finally:
        db.close()


if __name__ == "__main__":
    main()
