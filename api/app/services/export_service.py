import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import PROJECT_ROOT, get_settings
from app.core.exceptions import BadRequestError, NotFoundError
from app.models.entities import Export, UserDailyPlan

settings = get_settings()


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

    def export_plan(self, user_id: str, export_type: str, source_id: int, fmt: str = "json") -> Export:
        data = self._load_source(user_id, export_type, source_id)
        return self._write_record(user_id, export_type, source_id, fmt, data)

    def export_daily_plan_detail(
        self,
        user_id: str,
        detail: dict[str, Any],
        fmt: str,
        options: dict[str, Any] | None = None,
    ) -> Export:
        content, ext, _mime = self._render_detail(detail, fmt, options)
        filename = f"daily_plan_{detail['id']}_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}.{ext}"
        filepath = self.export_dir / filename
        filepath.write_bytes(content)

        record = Export(
            user_id=user_id,
            export_type="daily_plan",
            source_id=int(detail["id"]),
            format="pdf",
            template_id="default",
            file_url=f"private:exports/{filename}",
            created_at=datetime.now(UTC),
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

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

    def get_export(self, user_id: str, export_id: int) -> Export:
        record = self.db.get(Export, export_id)
        if not record or str(record.user_id) != user_id:
            raise NotFoundError("Export", export_id)
        return record

    def _write_record(self, user_id: str, export_type: str, source_id: int, fmt: str, data: dict) -> Export:
        filename = f"{export_type}_{source_id}_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}.{fmt}"
        filepath = self.export_dir / filename
        filepath.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

        record = Export(
            user_id=user_id,
            export_type=export_type,
            source_id=source_id,
            format=fmt,
            template_id="default",
            file_url=f"private:exports/{filename}",
            created_at=datetime.now(UTC),
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def _load_source(self, user_id: str, export_type: str, source_id: int) -> dict:
        if export_type == "daily_plan":
            plan = self.db.get(UserDailyPlan, source_id)
            if not plan or str(plan.user_id) != user_id:
                raise NotFoundError("UserDailyPlan", source_id)
            return {"type": export_type, "title_vi": plan.title_vi, "source": plan.source}
        raise NotFoundError("ExportType", export_type)

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
