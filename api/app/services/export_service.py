import csv
import json
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import PROJECT_ROOT, get_settings
from app.core.exceptions import BadRequestError, NotFoundError
from app.models.entities import Export, UserDailyPlan, UserWorkoutPlan

settings = get_settings()

SECTION_LABEL = {
    "warmup": "Khởi động",
    "main": "Tập chính",
    "cooldown": "Giãn cơ",
    "cardio": "Cardio",
}
MEAL_LABEL = {
    "breakfast": "Sáng",
    "lunch": "Trưa",
    "dinner": "Tối",
    "snack": "Phụ",
}

FORMAT_ALIAS = {
    "excel": "xlsx",
    "xlsx": "xlsx",
    "word": "doc",
    "docx": "doc",
}

# Phần luôn xuất hiện trong file xuất; để trống thì ghi rõ "Không có".
ALWAYS_LISTED_SECTIONS = ("warmup", "main", "cooldown", "cardio")
EMPTY_SECTION_TEXT = "Không có"


def _exercises_by_section(exercises: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {sec: [] for sec in ALWAYS_LISTED_SECTIONS}
    for ex in exercises:
        sec = ex.get("section") or "main"
        if sec not in grouped:
            grouped[sec] = []
        grouped[sec].append(ex)
    return grouped


def _meals_by_type(meals: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {
        "breakfast": [],
        "lunch": [],
        "dinner": [],
        "snack": [],
    }
    for meal in meals:
        mt = meal.get("meal_type") or "snack"
        if mt not in grouped:
            grouped[mt] = []
        grouped[mt].append(meal)
    return grouped


def _note_rows_for_meals(meal_notes: dict[str, Any]) -> list[tuple[str, str]]:
    """Return (label, note) for meal slot notes, including snack_N."""
    out: list[tuple[str, str]] = []
    for key in ("breakfast", "lunch", "dinner"):
        note = (meal_notes or {}).get(key)
        if note and str(note).strip():
            out.append((MEAL_LABEL.get(key, key), str(note).strip()))
    snack_keys = sorted(
        (k for k in (meal_notes or {}) if str(k).startswith("snack")),
        key=lambda k: int(str(k).split("_")[-1]) if "_" in str(k) and str(k).split("_")[-1].isdigit() else 0,
    )
    if not snack_keys and (meal_notes or {}).get("snack"):
        snack_keys = ["snack"]
    for i, key in enumerate(snack_keys):
        note = (meal_notes or {}).get(key)
        if note and str(note).strip():
            label = "Phụ" if key == "snack" else f"Phụ {i + 1}"
            out.append((label, str(note).strip()))
    return out


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
        # Cap ~1.5MB base64 payload roughly
        if len(s) > 2_100_000:
            continue
        images.append(s)
        if len(images) >= 2:
            break
    customer = (opts.get("customer_name") or "").strip() or None
    header = (opts.get("header_text") or "").strip() or None
    footer = (opts.get("footer_text") or "").strip() or None
    start_date = opts.get("start_date")
    return {
        "customer_name": customer[:200] if customer else None,
        "header_text": header[:2000] if header else None,
        "footer_text": footer[:2000] if footer else None,
        "image_data_urls": images,
        "image_position": position,
        "start_date": start_date,
    }


def _escape_html(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


class ExportService:
    def __init__(self, db: Session) -> None:
        self.db = db
        # Private dir — NOT under /media static mount
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
        normalized = FORMAT_ALIAS.get(fmt, fmt)
        if normalized not in {"csv", "xlsx", "doc", "pdf", "json"}:
            raise BadRequestError("Unsupported export format. Use csv, excel, word, pdf, or json.")
        content, ext, _mime = self._render_detail(detail, normalized, options)
        filename = f"daily_plan_{detail['id']}_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}.{ext}"
        filepath = self.export_dir / filename
        if isinstance(content, bytes):
            filepath.write_bytes(content)
        else:
            filepath.write_text(content, encoding="utf-8-sig" if ext == "csv" else "utf-8")

        record = Export(
            user_id=user_id,
            export_type="daily_plan",
            source_id=int(detail["id"]),
            format=normalized,
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
        normalized = FORMAT_ALIAS.get(fmt, fmt)
        if normalized not in {"csv", "xlsx", "doc", "pdf", "json"}:
            raise BadRequestError("Unsupported export format. Use csv, excel, word, pdf, or json.")
        content, ext, mime = self._render_detail(detail, normalized, options)
        plan_id = detail.get("id") or "shared"
        filename = f"daily_plan_{plan_id}_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}.{ext}"
        filepath = self.export_dir / filename
        if isinstance(content, bytes):
            filepath.write_bytes(content)
        else:
            filepath.write_text(content, encoding="utf-8-sig" if ext == "csv" else "utf-8")
        return filepath, filename, mime

    def get_export(self, user_id: str, export_id: int) -> Export:
        record = self.db.get(Export, export_id)
        if not record or str(record.user_id) != user_id:
            raise NotFoundError("Export", export_id)
        return record

    def _write_record(self, user_id: str, export_type: str, source_id: int, fmt: str, data: dict) -> Export:
        normalized = FORMAT_ALIAS.get(fmt, fmt)
        filename = f"{export_type}_{source_id}_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}.{normalized}"
        filepath = self.export_dir / filename
        filepath.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

        record = Export(
            user_id=user_id,
            export_type=export_type,
            source_id=source_id,
            format=normalized,
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
        if export_type == "workout_plan":
            plan = self.db.get(UserWorkoutPlan, source_id)
            if not plan or str(plan.user_id) != user_id:
                raise NotFoundError("UserWorkoutPlan", source_id)
            return {"type": export_type, "title_vi": plan.title_vi}
        raise NotFoundError("ExportType", export_type)

    def _render_detail(
        self,
        detail: dict[str, Any],
        fmt: str,
        options: dict[str, Any] | None = None,
    ) -> tuple[str | bytes, str, str]:
        opts = _sanitize_export_options(options)
        if fmt == "json":
            payload = {**detail, "export_options": {k: v for k, v in opts.items() if k != "image_data_urls"}}
            return json.dumps(payload, ensure_ascii=False, indent=2, default=str), "json", "application/json"
        if fmt == "xlsx":
            from app.services.xlsx_plan_export import XLSX_MIME, build_plan_xlsx

            return build_plan_xlsx(detail, opts), "xlsx", XLSX_MIME
        if fmt == "csv":
            return self._to_csv(detail, opts), "csv", "text/csv"
        html = self._to_html(detail, opts)
        if fmt == "doc":
            return html, "doc", "application/msword"
        # pdf: simple printable HTML (client can print; file still useful)
        return html, "html", "text/html"

    def _to_csv(self, detail: dict[str, Any], options: dict[str, Any] | None = None) -> str:
        opts = options or {}
        buf = StringIO()
        writer = csv.writer(buf)
        if opts.get("customer_name"):
            writer.writerow(["Khách hàng", opts["customer_name"], "", "", "", "", ""])
        if opts.get("header_text"):
            writer.writerow(["Lời chào / Intro", opts["header_text"], "", "", "", "", ""])
        share = detail.get("share_token")
        share_path = detail.get("share_url_path") or (f"/lich/{share}" if share else "")
        if share_path:
            writer.writerow(["Link xem lại", share_path, "", "", "", "", ""])
        imgs = opts.get("image_data_urls") or []
        if imgs:
            writer.writerow(
                [
                    "Ảnh đính kèm",
                    f"Có {len(imgs)} ảnh — xem bản PDF/Word để hiển thị ảnh",
                    "",
                    "",
                    "",
                    "",
                    "",
                ]
            )
        if opts.get("customer_name") or opts.get("header_text") or share_path or imgs:
            writer.writerow([])
        writer.writerow(["Ngày", "Phần", "Bài tập / Món", "Set", "Rep", "Calo", "Loại"])
        for day in detail.get("days") or []:
            label = day.get("title_vi") or f"Ngày {day.get('day_number')}"
            section_notes = day.get("section_notes") or {}
            meal_notes = day.get("meal_notes") or {}
            exercises = day.get("exercises") or []
            by_sec = _exercises_by_section(exercises)
            for sec in ALWAYS_LISTED_SECTIONS:
                items = by_sec.get(sec) or []
                sec_label = SECTION_LABEL.get(sec, sec)
                if not items:
                    writer.writerow([label, sec_label, EMPTY_SECTION_TEXT, "", "", "", "exercise"])
                else:
                    for ex in items:
                        writer.writerow(
                            [
                                label,
                                sec_label,
                                ex.get("name_vi"),
                                ex.get("sets"),
                                ex.get("reps"),
                                "",
                                "exercise",
                            ]
                        )
                note = section_notes.get(sec)
                if note and str(note).strip():
                    writer.writerow([label, sec_label, f"**Lưu ý:** {str(note).strip()}", "", "", "", "note"])

            by_meal = _meals_by_type(day.get("meals") or [])
            for mt in ("breakfast", "lunch", "dinner", "snack"):
                items = by_meal.get(mt) or []
                mt_label = MEAL_LABEL.get(mt, mt)
                for meal in items:
                    writer.writerow(
                        [
                            label,
                            mt_label,
                            meal.get("name_vi"),
                            "",
                            meal.get("servings"),
                            meal.get("calories"),
                            "meal",
                        ]
                    )
                if mt != "snack":
                    note = meal_notes.get(mt)
                    if note and str(note).strip():
                        writer.writerow([label, mt_label, f"**Lưu ý:** {str(note).strip()}", "", "", "", "note"])
            for note_label, note_text in _note_rows_for_meals(meal_notes):
                if note_label in ("Sáng", "Trưa", "Tối"):
                    continue  # already written above
                writer.writerow([label, note_label, f"**Lưu ý:** {note_text}", "", "", "", "note"])
            free = day.get("notes_vi")
            if free and str(free).strip():
                writer.writerow([label, "Ngày", f"**Lưu ý:** {str(free).strip()}", "", "", "", "note"])
        if opts.get("footer_text"):
            writer.writerow([])
            writer.writerow(["Ghi chú cuối", opts["footer_text"], "", "", "", "", ""])
        return buf.getvalue()

    def _images_html(self, options: dict[str, Any]) -> str:
        imgs = options.get("image_data_urls") or []
        if not imgs:
            return ""
        parts = []
        for src in imgs:
            parts.append(
                f'<p style="margin:12px 0"><img src="{src}" alt="" '
                f'style="max-width:100%;max-height:280px;border-radius:8px"/></p>'
            )
        return "".join(parts)

    def _to_html(self, detail: dict[str, Any], options: dict[str, Any] | None = None) -> str:
        opts = options or {}
        day_blocks = []
        for day in detail.get("days") or []:
            label = day.get("title_vi") or f"Ngày {day.get('day_number')}"
            section_notes = day.get("section_notes") or {}
            meal_notes = day.get("meal_notes") or {}
            rows = []
            by_sec = _exercises_by_section(day.get("exercises") or [])
            for sec in ALWAYS_LISTED_SECTIONS:
                items = by_sec.get(sec) or []
                sec_label = SECTION_LABEL.get(sec, sec)
                if not items:
                    rows.append(
                        f"<tr><td>{sec_label}</td>"
                        f"<td colspan='3' align='center'>{EMPTY_SECTION_TEXT}</td></tr>"
                    )
                else:
                    for ex in items:
                        rows.append(
                            f"<tr><td>{sec_label}</td>"
                            f"<td>{ex.get('name_vi')}</td><td align='center'>{ex.get('sets')}</td>"
                            f"<td align='center'>{ex.get('reps')}</td></tr>"
                        )
                note = section_notes.get(sec)
                if note and str(note).strip():
                    rows.append(
                        f"<tr style='background:#fffbeb'><td><strong>{sec_label}</strong></td>"
                        f"<td colspan='3'><strong>Lưu ý:</strong> {_escape_html(str(note).strip())}</td></tr>"
                    )

            meal_blocks = []
            by_meal = _meals_by_type(day.get("meals") or [])
            for mt in ("breakfast", "lunch", "dinner", "snack"):
                items = by_meal.get(mt) or []
                mt_label = MEAL_LABEL.get(mt, mt)
                if not items and mt == "snack":
                    continue
                if not items and not (meal_notes.get(mt) if mt != "snack" else False):
                    continue
                lis = "".join(
                    f"<li>{m.get('name_vi')} ×{m.get('servings')} — {m.get('calories')} kcal</li>"
                    for m in items
                )
                note_html = ""
                if mt != "snack":
                    note = meal_notes.get(mt)
                    if note and str(note).strip():
                        note_html = (
                            f"<p style='margin:4px 0 0;background:#fffbeb;padding:6px 8px;border-radius:6px'>"
                            f"<strong>Lưu ý:</strong> {_escape_html(str(note).strip())}</p>"
                        )
                meal_blocks.append(f"<p><strong>{mt_label}</strong></p><ul>{lis or '<li>Không có</li>'}</ul>{note_html}")

            for note_label, note_text in _note_rows_for_meals(meal_notes):
                if note_label in ("Sáng", "Trưa", "Tối"):
                    continue
                meal_blocks.append(
                    f"<p><strong>{note_label}</strong></p>"
                    f"<p style='background:#fffbeb;padding:6px 8px;border-radius:6px'>"
                    f"<strong>Lưu ý:</strong> {_escape_html(note_text)}</p>"
                )

            table = (
                "<table border='1' cellpadding='8' cellspacing='0' "
                "style='border-collapse:collapse;width:100%;margin-bottom:12px'>"
                "<tr style='background:#ecfdf5'><th>Phần</th><th>Bài tập</th><th>Set</th><th>Rep</th></tr>"
                + "".join(rows)
                + "</table>"
            )
            meals_html = "".join(meal_blocks)
            free = day.get("notes_vi")
            free_html = (
                f"<p style='background:#fffbeb;padding:6px 8px;border-radius:6px'>"
                f"<strong>Lưu ý ngày:</strong> {_escape_html(str(free).strip())}</p>"
                if free and str(free).strip()
                else ""
            )
            day_blocks.append(f"<h2>{label}</h2>{table}<h3>Thực đơn</h3>{meals_html or '<p>Không có</p>'}{free_html}")

        kcal = detail.get("target_calories")
        kcal_txt = f" · <strong>{kcal} kcal/ngày</strong>" if kcal else ""
        share = detail.get("share_token")
        share_path = detail.get("share_url_path") or (f"/lich/{share}" if share else None)
        share_txt = (
            f'<p><strong>Link xem lại:</strong> {share_path}</p>'
            if share_path
            else ""
        )
        customer = opts.get("customer_name")
        customer_html = (
            f"<p><strong>Khách hàng:</strong> {_escape_html(customer)}</p>" if customer else ""
        )
        header = opts.get("header_text")
        header_html = (
            f"<p style='white-space:pre-wrap'>{_escape_html(header)}</p>" if header else ""
        )
        footer = opts.get("footer_text")
        footer_html = (
            f"<p style='margin-top:24px;white-space:pre-wrap'>{_escape_html(footer)}</p>"
            if footer
            else ""
        )
        images = self._images_html(opts)
        pos = opts.get("image_position") or "header"
        img_header = images if pos == "header" else ""
        img_before = images if pos == "before_days" else ""
        img_footer = images if pos == "footer" else ""

        return f"""<!DOCTYPE html><html lang="vi"><head><meta charset="utf-8">
<title>{_escape_html(str(detail.get('title_vi') or 'TAPTOT'))}</title>
<style>body{{font-family:Segoe UI,sans-serif;max-width:720px;margin:24px auto;color:#334155;line-height:1.5}}
h1{{color:#059669}}h2{{margin-top:24px;color:#047857}}h3{{color:#0f766e}}</style></head><body>
{img_header}
{customer_html}
<h1>{_escape_html(str(detail.get('title_vi') or ''))}</h1>
{header_html}
<p>{_escape_html(str(detail.get('description_vi') or ''))}{kcal_txt}</p>
{share_txt}
{img_before}
{''.join(day_blocks)}
{footer_html}
{img_footer}
<p style="margin-top:32px;font-size:12px;color:#94a3b8">Xuất từ TAPTOT · {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}</p>
</body></html>"""
