from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import PROJECT_ROOT
from app.core.exceptions import BadRequestError


def _sanitize_export_options(options: dict[str, Any] | None) -> dict[str, Any]:
    opts = options or {}
    position = opts.get("image_position") or "header"
    if position not in {"header", "before_days", "footer"}:
        position = "header"
    images: list[str] = []
    for raw in opts.get("image_data_urls") or []:
        if not isinstance(raw, str):
            continue
        s = raw.strip()
        if not s.startswith("data:image/") or ";base64," not in s:
            continue
        if len(s) > 2_100_000:
            continue
        images.append(s)
        if len(images) >= 2:
            break
    customer = (opts.get("customer_name") or "").strip() or None
    header = (opts.get("header_text") or "").strip() or None
    footer = (opts.get("footer_text") or "").strip() or None
    return {
        "customer_name": customer[:200] if customer else None,
        "header_text": header[:2000] if header else None,
        "footer_text": footer[:2000] if footer else None,
        "image_data_urls": images,
        "image_position": position,
    }


class ExportService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.export_dir = PROJECT_ROOT / "data" / "exports"
        self.export_dir.mkdir(parents=True, exist_ok=True)

    def render_detail_file(
        self,
        detail: dict[str, Any],
        fmt: str,
        options: dict[str, Any] | None = None,
    ) -> tuple[Path, str, str]:
        """Write export file without persisting Export row (for public share)."""
        content, ext, mime = self._render_detail(detail, fmt, options)
        plan_id = detail.get("id") or "shared"
        filename = f"daily_plan_{plan_id}_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}.{ext}"
        filepath = self.export_dir / filename
        filepath.write_bytes(content)
        return filepath, filename, mime

    def _render_detail(
        self,
        detail: dict[str, Any],
        fmt: str,
        options: dict[str, Any] | None = None,
    ) -> tuple[bytes, str, str]:
        if (fmt or "").lower() != "pdf":
            raise BadRequestError("Unsupported export format. Use pdf.")
        from app.services.pdf_plan_export import PDF_MIME, build_plan_pdf

        opts = _sanitize_export_options(options)
        return build_plan_pdf(detail, opts), "pdf", PDF_MIME
