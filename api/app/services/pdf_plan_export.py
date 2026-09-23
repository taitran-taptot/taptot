"""Real PDF workout-plan export with a repeating TAPTOT watermark."""

from __future__ import annotations

import base64
import secrets
from io import BytesIO
from pathlib import Path
from typing import Any

from fpdf import FPDF
from fpdf.enums import AccessPermission, XPos, YPos
from PIL import Image

PDF_MIME = "application/pdf"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
FONT_REGULAR = DATA_DIR / "fonts" / "NotoSans-Regular.ttf"
FONT_BOLD = DATA_DIR / "fonts" / "NotoSans-Bold.ttf"
LOGO_PATH = DATA_DIR / "brand" / "taptot-logo.png"

GREEN = (5, 150, 105)
INK = (51, 65, 85)
MUTED = (100, 116, 139)
NOTE_BG = (255, 251, 235)

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
ALWAYS_SECTIONS = ("warmup", "main", "cooldown", "cardio")
EMPTY_SECTION_TEXT = "Không có"


def _exercises_by_section(exercises: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {sec: [] for sec in ALWAYS_SECTIONS}
    for ex in exercises or []:
        sec = ex.get("section") or "main"
        grouped.setdefault(sec, []).append(ex)
    return grouped


def _meals_by_type(meals: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {
        "breakfast": [],
        "lunch": [],
        "dinner": [],
        "snack": [],
    }
    for meal in meals or []:
        mt = meal.get("meal_type") or "snack"
        grouped.setdefault(mt, []).append(meal)
    return grouped


def _note_rows_for_meals(meal_notes: dict[str, Any]) -> list[tuple[str, str]]:
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


def _txt(value: Any, fallback: str = "") -> str:
    if value is None:
        return fallback
    return str(value)


def _decode_data_url(url: str) -> BytesIO | None:
    try:
        _header, b64 = url.split(",", 1)
        raw = base64.b64decode(b64)
        img = Image.open(BytesIO(raw))
        if img.mode not in {"RGB", "RGBA", "L"}:
            img = img.convert("RGBA") if "A" in img.getbands() else img.convert("RGB")
        buf = BytesIO()
        fmt = "PNG" if img.mode in {"RGBA", "P"} else "JPEG"
        save_img = img.convert("RGBA") if fmt == "PNG" and img.mode != "RGBA" else img
        if fmt == "JPEG" and save_img.mode not in {"RGB", "L"}:
            save_img = save_img.convert("RGB")
        save_img.save(buf, format=fmt)
        buf.seek(0)
        buf.name = "img.png" if fmt == "PNG" else "img.jpg"
        return buf
    except Exception:
        return None


class PlanPDF(FPDF):
    def __init__(self) -> None:
        super().__init__(format="A4", unit="mm")
        if not FONT_REGULAR.exists() or not FONT_BOLD.exists():
            raise FileNotFoundError("Missing Noto Sans TTF under app/data/fonts/")
        self.add_font("NotoSans", "", str(FONT_REGULAR))
        self.add_font("NotoSans", "B", str(FONT_BOLD))
        self.set_auto_page_break(auto=True, margin=18)
        self.set_margins(14, 24, 14)
        self.set_text_color(*INK)

    def header(self) -> None:
        self._draw_watermark()
        if LOGO_PATH.exists():
            try:
                self.image(str(LOGO_PATH), x=14, y=6.5, h=10)
            except Exception:
                pass
        self.set_xy(28, 8)
        self.set_font("NotoSans", "B", 12)
        self.set_text_color(*GREEN)
        self.cell(40, 8, "TAPTOT")
        self.set_draw_color(*GREEN)
        self.set_line_width(0.4)
        self.line(14, 18, self.w - 14, 18)
        self.set_text_color(*INK)
        self.set_xy(self.l_margin, self.t_margin)

    def footer(self) -> None:
        self.set_y(-14)
        self.set_font("NotoSans", "", 8)
        self.set_text_color(*MUTED)
        self.cell(0, 6, "taptot.vn  ·  lịch tập dành cho bạn", new_x=XPos.LEFT, new_y=YPos.TOP)
        self.cell(0, 6, f"Trang {self.page_no()}", align="R")
        self.set_text_color(*INK)
        self.set_x(self.l_margin)

    def _draw_watermark(self) -> None:
        saved = (self.get_x(), self.get_y())
        self.set_font("NotoSans", "B", 26)
        self.set_text_color(*GREEN)
        step_x, step_y = 64, 40
        with self.local_context(fill_opacity=0.09):
            y = -8.0
            while y < self.h + 16:
                x = -16.0
                while x < self.w + 16:
                    with self.rotation(45, x, y):
                        self.text(x, y, "TAPTOT")
                    x += step_x
                y += step_y
        self.set_text_color(*INK)
        self.set_xy(*saved)


def _ensure_space(pdf: PlanPDF, h: float) -> None:
    if pdf.get_y() + h > pdf.page_break_trigger:
        pdf.add_page()


def _heading(pdf: PlanPDF, text: str, size: int = 16) -> None:
    pdf.set_x(pdf.l_margin)
    _ensure_space(pdf, 12)
    pdf.set_x(pdf.l_margin)
    pdf.set_font("NotoSans", "B", size)
    pdf.set_text_color(*GREEN)
    pdf.multi_cell(0, 8, text)
    pdf.set_text_color(*INK)
    pdf.ln(1)


def _body(pdf: PlanPDF, text: str, size: int = 10, bold: bool = False) -> None:
    if not text:
        return
    pdf.set_x(pdf.l_margin)
    pdf.set_font("NotoSans", "B" if bold else "", size)
    pdf.set_text_color(*INK)
    pdf.multi_cell(0, 5.5, text)
    pdf.ln(0.5)


def _muted(pdf: PlanPDF, text: str) -> None:
    pdf.set_x(pdf.l_margin)
    pdf.set_font("NotoSans", "", 9)
    pdf.set_text_color(*MUTED)
    pdf.multi_cell(0, 5, text)
    pdf.set_text_color(*INK)


def _note(pdf: PlanPDF, text: str) -> None:
    pdf.set_x(pdf.l_margin)
    _ensure_space(pdf, 10)
    pdf.set_x(pdf.l_margin)
    pdf.set_fill_color(*NOTE_BG)
    pdf.set_font("NotoSans", "", 9)
    pdf.multi_cell(0, 5.5, f"Lưu ý: {text}", fill=True)
    pdf.ln(1)


def _embed_images(pdf: PlanPDF, images: list[str]) -> None:
    usable = pdf.w - pdf.l_margin - pdf.r_margin
    for raw in images:
        buf = _decode_data_url(raw)
        if not buf:
            continue
        _ensure_space(pdf, 42)
        pdf.image(buf, w=min(usable, 90), h=40)
        pdf.ln(4)


def _write_day(pdf: PlanPDF, day: dict[str, Any]) -> None:
    label = _txt(day.get("title_vi"), f"Ngày {day.get('day_number')}")
    _heading(pdf, label, size=13)
    section_notes = day.get("section_notes") or {}
    meal_notes = day.get("meal_notes") or {}
    by_sec = _exercises_by_section(day.get("exercises") or [])

    col_sec, col_name, col_sets, col_reps = 32, 88, 18, 28
    pdf.set_x(pdf.l_margin)
    pdf.set_font("NotoSans", "B", 9)
    pdf.set_fill_color(236, 253, 245)
    pdf.cell(col_sec, 7, "Phần", border=1, fill=True, align="C")
    pdf.cell(col_name, 7, "Bài tập", border=1, fill=True, align="C")
    pdf.cell(col_sets, 7, "Set", border=1, fill=True, align="C")
    pdf.cell(col_reps, 7, "Rep", border=1, fill=True, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font("NotoSans", "", 9)
    for sec in ALWAYS_SECTIONS:
        items = by_sec.get(sec) or []
        sec_label = SECTION_LABEL.get(sec, sec)
        if not items:
            _ensure_space(pdf, 8)
            pdf.set_x(pdf.l_margin)
            pdf.cell(col_sec, 7, sec_label, border=1)
            pdf.cell(col_name + col_sets + col_reps, 7, EMPTY_SECTION_TEXT, border=1, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        else:
            for ex in items:
                _ensure_space(pdf, 8)
                pdf.set_x(pdf.l_margin)
                pdf.cell(col_sec, 7, sec_label, border=1)
                name = _txt(ex.get("name_vi"), "—")
                if len(name) > 42:
                    name = name[:41] + "…"
                pdf.cell(col_name, 7, name, border=1)
                pdf.cell(col_sets, 7, _txt(ex.get("sets"), ""), border=1, align="C")
                pdf.cell(col_reps, 7, _txt(ex.get("reps"), ""), border=1, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        note = section_notes.get(sec)
        if note and str(note).strip():
            _note(pdf, str(note).strip())

    pdf.ln(2)
    pdf.set_x(pdf.l_margin)
    pdf.set_font("NotoSans", "B", 11)
    pdf.set_text_color(*GREEN)
    pdf.cell(0, 7, "Thực đơn", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(*INK)

    by_meal = _meals_by_type(day.get("meals") or [])
    wrote_meal = False
    for mt in ("breakfast", "lunch", "dinner", "snack"):
        items = by_meal.get(mt) or []
        slot_note = meal_notes.get(mt) if mt != "snack" else None
        if mt == "snack" and not items:
            continue
        if not items and not (slot_note and str(slot_note).strip()):
            continue
        wrote_meal = True
        _body(pdf, MEAL_LABEL.get(mt, mt), size=10, bold=True)
        if items:
            for meal in items:
                servings = meal.get("servings")
                kcal = meal.get("calories")
                extra = ""
                if servings not in (None, ""):
                    extra += f" ×{servings}"
                if kcal not in (None, ""):
                    extra += f" — {kcal} kcal"
                _body(pdf, f"• {_txt(meal.get('name_vi'))}{extra}", size=9)
        else:
            _muted(pdf, EMPTY_SECTION_TEXT)
        if slot_note and str(slot_note).strip():
            _note(pdf, str(slot_note).strip())

    for note_label, note_text in _note_rows_for_meals(meal_notes):
        if note_label in ("Sáng", "Trưa", "Tối"):
            continue
        wrote_meal = True
        _body(pdf, note_label, size=10, bold=True)
        _note(pdf, note_text)

    if not wrote_meal:
        _muted(pdf, EMPTY_SECTION_TEXT)

    free = day.get("notes_vi")
    if free and str(free).strip():
        _note(pdf, f"Lưu ý ngày: {str(free).strip()}")
    pdf.ln(3)


def build_plan_pdf(
    detail: dict[str, Any],
    options: dict[str, Any] | None = None,
    *,
    encrypt: bool = True,
) -> bytes:
    opts = options or {}
    images = [s for s in (opts.get("image_data_urls") or []) if isinstance(s, str)]
    pos = opts.get("image_position") or "header"
    if pos not in {"header", "before_days", "footer"}:
        pos = "header"

    pdf = PlanPDF()
    pdf.set_title(_txt(detail.get("title_vi"), "Lịch tập TAPTOT"))
    pdf.set_author("TAPTOT")
    pdf.add_page()

    if pos == "header":
        _embed_images(pdf, images)

    customer = (opts.get("customer_name") or "").strip()
    if customer:
        _body(pdf, f"Khách hàng: {customer}", bold=True)

    _heading(pdf, _txt(detail.get("title_vi"), "Lịch tập TAPTOT"), size=18)

    header_text = (opts.get("header_text") or "").strip()
    if header_text:
        _body(pdf, header_text)

    desc = _txt(detail.get("description_vi")).strip()
    kcal = detail.get("target_calories")
    if kcal:
        desc = f"{desc} · {kcal} kcal/ngày".strip(" ·")
    if desc:
        _body(pdf, desc)

    share = detail.get("share_token")
    share_path = detail.get("share_url_path") or (f"/lich/{share}" if share else None)
    if share_path:
        _muted(pdf, f"Link xem lại: {share_path}")

    if pos == "before_days":
        _embed_images(pdf, images)

    days = list(detail.get("days") or [])
    if not days:
        _muted(pdf, "Lịch này chưa có nội dung.")
    else:
        for day in days:
            _write_day(pdf, day)

    footer_text = (opts.get("footer_text") or "").strip()
    if footer_text:
        pdf.ln(2)
        _body(pdf, footer_text)

    if pos == "footer":
        _embed_images(pdf, images)

    if encrypt:
        pdf.set_encryption(
            owner_password=secrets.token_urlsafe(16),
            user_password="",
            permissions=AccessPermission.PRINT_LOW_RES | AccessPermission.PRINT_HIGH_RES,
        )
    return bytes(pdf.output())
