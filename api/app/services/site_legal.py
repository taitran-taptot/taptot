from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, NotFoundError
from app.models.entities import SiteLegalDocument

LEGAL_SLUGS = (
    "dieu-khoan",
    "chinh-sach-bao-mat",
    "chinh-sach-ban-hang",
    "chinh-sach-thanh-toan",
    "khieu-nai",
    "thong-tin-don-vi",
)

_MAX_SECTIONS = 40
_MAX_PARAGRAPHS = 20
_MAX_BULLETS = 30
_MAX_LABEL = 200
_MAX_INTRO = 4000
_MAX_AGREEMENT = 4000
_MAX_TITLE = 300
_MAX_PARAGRAPH = 4000
_MAX_BULLET = 1000
_ID_RE = re.compile(r"[^A-Za-z0-9_-]")


def require_legal_slug(slug: str) -> str:
    if slug not in LEGAL_SLUGS:
        raise NotFoundError("Legal document", slug)
    return slug


def _bound(value: Any, limit: int, label: str) -> str:
    text = str(value or "").strip()
    if len(text) > limit:
        raise BadRequestError(f"{label} tối đa {limit} ký tự")
    return text


def _lines(raw: Any, *, limit: int, item_limit: int, label: str) -> list[str]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise BadRequestError(f"{label} phải là danh sách")
    if len(raw) > limit:
        raise BadRequestError(f"Tối đa {limit} {label.lower()}")
    lines: list[str] = []
    for item in raw:
        text = _bound(item, item_limit, label)
        if text:
            lines.append(text)
    return lines


def _section_id(raw: Any, used: set[str], index: int) -> str:
    text = _ID_RE.sub("", _bound(raw, 40, "Mã mục"))
    if not text or text in used:
        number = index + 1
        text = str(number)
        while text in used:
            number += 1
            text = str(number)
    used.add(text)
    return text


def normalize_legal_document(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise BadRequestError("Nội dung chính sách không hợp lệ")
    sections_in = raw.get("sections")
    if not isinstance(sections_in, list) or not sections_in:
        raise BadRequestError("Cần ít nhất một mục")
    if len(sections_in) > _MAX_SECTIONS:
        raise BadRequestError(f"Tối đa {_MAX_SECTIONS} mục")
    used: set[str] = set()
    sections: list[dict[str, Any]] = []
    for index, item in enumerate(sections_in):
        if not isinstance(item, dict):
            raise BadRequestError("Mỗi mục cần tiêu đề và nội dung")
        title = _bound(item.get("title"), _MAX_TITLE, "Tiêu đề mục")
        if not title:
            raise BadRequestError("Mỗi mục cần tiêu đề")
        paragraphs = _lines(
            item.get("paragraphs"),
            limit=_MAX_PARAGRAPHS,
            item_limit=_MAX_PARAGRAPH,
            label="Đoạn văn",
        )
        bullets = _lines(
            item.get("bullets"),
            limit=_MAX_BULLETS,
            item_limit=_MAX_BULLET,
            label="Gạch đầu dòng",
        )
        if not paragraphs and not bullets:
            raise BadRequestError("Mỗi mục cần ít nhất một đoạn hoặc một gạch đầu dòng")
        sections.append(
            {
                "id": _section_id(item.get("id"), used, index),
                "title": title,
                "paragraphs": paragraphs,
                "bullets": bullets,
            }
        )
    return {
        "updated_label": _bound(raw.get("updated_label"), _MAX_LABEL, "Dòng cập nhật"),
        "intro": _bound(raw.get("intro"), _MAX_INTRO, "Đoạn mở đầu"),
        "agreement": _bound(raw.get("agreement"), _MAX_AGREEMENT, "Đoạn đồng ý"),
        "sections": sections,
    }


class SiteLegalService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_public(self, slug: str) -> dict[str, Any]:
        require_legal_slug(slug)
        row = self.db.get(SiteLegalDocument, slug)
        document = self._read_body(row)
        if document is None:
            return {"slug": slug, "source": "default", "document": None}
        return {"slug": slug, "source": "saved", "document": document}

    def upsert(self, slug: str, raw: Any) -> dict[str, Any]:
        require_legal_slug(slug)
        document = normalize_legal_document(raw)
        row = self.db.get(SiteLegalDocument, slug)
        if row is None:
            row = SiteLegalDocument(slug=slug, body="{}")
            self.db.add(row)
        row.body = json.dumps(document, ensure_ascii=False)
        row.updated_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(row)
        return {"slug": slug, "source": "saved", "document": document}

    def reset(self, slug: str) -> dict[str, Any]:
        require_legal_slug(slug)
        row = self.db.get(SiteLegalDocument, slug)
        if row is not None:
            self.db.delete(row)
            self.db.commit()
        return {"slug": slug, "source": "default", "document": None}

    def _read_body(self, row: SiteLegalDocument | None) -> dict[str, Any] | None:
        if row is None or not (row.body or "").strip():
            return None
        try:
            parsed = json.loads(row.body)
        except json.JSONDecodeError:
            return None
        try:
            return normalize_legal_document(parsed)
        except BadRequestError:
            return None
