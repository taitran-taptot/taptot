"""Real PDF workout-plan export with a repeating TAPTOT watermark."""

from __future__ import annotations

import base64
import re
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
    "snack": "Phụ 1",
    "snack_2": "Phụ 2",
    "flex": "Linh hoạt",
}
ALWAYS_SECTIONS = ("warmup", "main", "cooldown", "cardio")
EMPTY_SECTION_TEXT = "Không có"
DAYS_PER_WEEK = 7
WEEKS_PER_MONTH = 4
_WEEK_TITLE = re.compile(r"Tuần\s+(\d+)", re.IGNORECASE)


def _exercises_by_section(exercises: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {sec: [] for sec in ALWAYS_SECTIONS}
    for ex in exercises or []:
        sec = ex.get("section") or "main"
        grouped.setdefault(sec, []).append(ex)
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
    for key in snack_keys:
        note = (meal_notes or {}).get(key)
        if note and str(note).strip():
            label = "Phụ 1" if key in {"snack", "snack_0"} else "Phụ 2"
            out.append((label, str(note).strip()))
    return out


def _txt(value: Any, fallback: str = "") -> str:
    if value is None:
        return fallback
    return str(value)


_GRAM_SIZE = re.compile(r"^\s*(\d+(?:[.,]\d+)?)\s*g\s*$", re.IGNORECASE)


def _portion_grams(meal: dict[str, Any]) -> int | None:
    """Portion weight in grams, rounded to 5 g the same way the plan view does."""
    kind = str(meal.get("food_kind") or "").lower()
    prepared = bool(meal.get("is_complete_meal")) or kind == "dish"
    raw_qty = 1 if prepared else meal.get("servings")
    try:
        qty = float(raw_qty) if raw_qty not in (None, "") else 1.0
    except (TypeError, ValueError):
        qty = 1.0
    if qty <= 0:
        qty = 1.0
    base = meal.get("serving_grams")
    if base in (None, ""):
        match = _GRAM_SIZE.match(str(meal.get("serving_size") or ""))
        base = match.group(1).replace(",", ".") if match else None
    try:
        base_g = float(base) if base not in (None, "") else 0.0
    except (TypeError, ValueError):
        base_g = 0.0
    if base_g <= 0:
        return None
    total = qty * base_g
    if total <= 0:
        return None
    rounded = int(round(total / 5.0) * 5)
    return rounded if rounded > 0 else int(round(total))


def _meal_line(meal: dict[str, Any]) -> str:
    parts = [f"• {_txt(meal.get('name_vi'))}"]
    grams = _portion_grams(meal)
    if grams is not None:
        parts.append(f"{grams} g")
    else:
        servings = meal.get("servings")
        if servings not in (None, ""):
            parts.append(f"×{servings}")
    kcal = meal.get("calories")
    if kcal not in (None, ""):
        parts.append(f"{kcal} kcal")
    if len(parts) == 1:
        return parts[0]
    return f"{parts[0]} — {' — '.join(parts[1:])}"


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


def _write_cells(
    pdf: PlanPDF,
    cells: list[tuple[float, str, str]],
    *,
    fill: bool = False,
    bold: bool = False,
) -> None:
    """Draw one table row, wrapping every cell so no text is clipped."""
    pdf.set_font("NotoSans", "B" if bold else "", 9)
    line_h = 4.6
    wrapped: list[list[str]] = []
    for width, text, _align in cells:
        lines = pdf.multi_cell(
            width,
            line_h,
            text or " ",
            dry_run=True,
            output="LINES",
            wrapmode="WORD",
        )
        wrapped.append(list(lines) if lines else [" "])
    row_h = max(7.2, max(len(lines) for lines in wrapped) * line_h + 2.2)
    _ensure_space(pdf, row_h)
    if fill:
        pdf.set_fill_color(236, 253, 245)
    x = pdf.l_margin
    y = pdf.get_y()
    for (width, text, align), lines in zip(cells, wrapped):
        pdf.rect(x, y, width, row_h, style="DF" if fill else "D")
        block_h = len(lines) * line_h
        pdf.set_xy(x, y + (row_h - block_h) / 2)
        pdf.multi_cell(width, line_h, text or " ", align=align, border=0, wrapmode="WORD")
        x += width
    pdf.set_xy(pdf.l_margin, y + row_h)


def _group_weeks(days: list[dict[str, Any]]) -> list[tuple[int, list[dict[str, Any]]]]:
    if not days:
        return []
    titled = all(_WEEK_TITLE.search(str(day.get("title_vi") or "")) for day in days)
    buckets: dict[int, list[dict[str, Any]]] = {}
    for day in days:
        if titled:
            match = _WEEK_TITLE.search(str(day.get("title_vi") or ""))
            week = int(match.group(1)) if match else 1
        else:
            number = int(day.get("day_number") or 1)
            week = max(1, (number + DAYS_PER_WEEK - 1) // DAYS_PER_WEEK)
        buckets.setdefault(week, []).append(day)
    return [(week, buckets[week]) for week in sorted(buckets)]


def _week_fingerprint(days: list[dict[str, Any]]) -> tuple:
    rows = []
    ordered = sorted(days, key=lambda day: int(day.get("day_number") or 0))
    for day in ordered:
        exercises = []
        for ex in day.get("exercises") or []:
            prescriptions = ex.get("set_prescriptions") or []
            if prescriptions:
                reps = tuple(
                    str(p.get("reps") or "").strip()
                    for p in prescriptions
                    if isinstance(p, dict)
                )
            else:
                reps = (str(ex.get("reps") or ""),)
            exercises.append(
                (
                    str(ex.get("section") or "main"),
                    str(ex.get("name_vi") or ""),
                    str(ex.get("sets") if ex.get("sets") is not None else ""),
                    reps,
                )
            )
        rows.append(tuple(exercises))
    return tuple(rows)


def _repeat_label(week: int) -> str:
    month = max(1, (week + WEEKS_PER_MONTH - 1) // WEEKS_PER_MONTH)
    index = ((week - 1) % WEEKS_PER_MONTH) + 1
    return f"Tập giống tuần {index} tháng {month}"


def _aggregate_meals(days: list[dict[str, Any]]) -> list[dict[str, Any]]:
    order: list[str] = []
    bucket: dict[str, dict[str, Any]] = {}
    for day in days:
        for meal in day.get("meals") or []:
            key = str(meal.get("food_id") if meal.get("food_id") is not None else meal.get("name_vi") or "")
            grams = _portion_grams(meal)
            try:
                kcal = float(meal.get("calories")) if meal.get("calories") not in (None, "") else 0.0
            except (TypeError, ValueError):
                kcal = 0.0
            if key not in bucket:
                order.append(key)
                bucket[key] = {
                    "name_vi": meal.get("name_vi"),
                    "grams": 0,
                    "calories": 0.0,
                    "has_grams": False,
                    "servings": 0.0,
                }
            row = bucket[key]
            if grams:
                row["grams"] += grams
                row["has_grams"] = True
            else:
                try:
                    row["servings"] += float(meal.get("servings") or 0)
                except (TypeError, ValueError):
                    pass
            row["calories"] += kcal
    meals: list[dict[str, Any]] = []
    for key in order:
        row = bucket[key]
        meal: dict[str, Any] = {"name_vi": row["name_vi"]}
        if row["calories"]:
            meal["calories"] = int(round(row["calories"]))
        if row["has_grams"]:
            meal["servings"] = 1
            meal["serving_grams"] = row["grams"]
        elif row["servings"]:
            meal["servings"] = row["servings"]
        meals.append(meal)
    return meals


def _meal_notes(days: list[dict[str, Any]]) -> list[str]:
    seen: set[str] = set()
    notes: list[str] = []
    for day in days:
        for label, text in _note_rows_for_meals(day.get("meal_notes") or {}):
            line = f"{label}: {text}"
            if line in seen:
                continue
            seen.add(line)
            notes.append(line)
    return notes


def _write_meal_summary(pdf: PlanPDF, days: list[dict[str, Any]]) -> None:
    meals = _aggregate_meals(days)
    notes = _meal_notes(days)
    pdf.ln(1)
    pdf.set_x(pdf.l_margin)
    pdf.set_font("NotoSans", "B", 11)
    pdf.set_text_color(*GREEN)
    pdf.cell(0, 7, "Thực đơn", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(*INK)
    if meals:
        for meal in meals:
            _body(pdf, _meal_line(meal), size=9)
    else:
        _muted(pdf, EMPTY_SECTION_TEXT)
    for note in notes:
        _note(pdf, note)
    pdf.ln(2)


def _write_day(pdf: PlanPDF, day: dict[str, Any]) -> None:
    label = _txt(day.get("title_vi"), f"Ngày {day.get('day_number')}")
    _heading(pdf, label, size=13)
    section_notes = day.get("section_notes") or {}
    by_sec = _exercises_by_section(day.get("exercises") or [])

    usable = pdf.w - pdf.l_margin - pdf.r_margin
    col_sec, col_sets, col_reps = 30, 14, 52
    col_name = usable - col_sec - col_sets - col_reps
    pdf.set_text_color(*INK)
    _write_cells(
        pdf,
        [
            (col_sec, "Phần", "C"),
            (col_name, "Bài tập", "C"),
            (col_sets, "Set", "C"),
            (col_reps, "Rep", "C"),
        ],
        fill=True,
        bold=True,
    )

    for sec in ALWAYS_SECTIONS:
        items = by_sec.get(sec) or []
        sec_label = SECTION_LABEL.get(sec, sec)
        if not items:
            _write_cells(
                pdf,
                [
                    (col_sec, sec_label, "L"),
                    (col_name + col_sets + col_reps, EMPTY_SECTION_TEXT, "C"),
                ],
            )
        else:
            for ex in items:
                name = _txt(ex.get("name_vi"), "—")
                bits: list[str] = []
                prescriptions = ex.get("set_prescriptions") or []
                if ex.get("technique") == "super_set":
                    bits.append("SS")
                if ex.get("technique") == "drop_set" or any(
                    isinstance(p, dict) and p.get("technique") == "drop_set" for p in prescriptions
                ):
                    bits.append("Dropset")
                rpe = ex.get("rpe")
                rir = ex.get("rir")
                if rpe is not None and rpe != "":
                    bits.append(f"RPE {rpe}")
                if rir is not None and rir != "":
                    bits.append(f"RIR {rir}")
                if bits:
                    name = f"{name} ({', '.join(bits)})"
                if prescriptions:
                    reps_txt = " / ".join(
                        str(p.get("reps") or "").strip()
                        for p in prescriptions
                        if isinstance(p, dict)
                    )
                else:
                    reps_txt = ""
                _write_cells(
                    pdf,
                    [
                        (col_sec, sec_label, "L"),
                        (col_name, name, "L"),
                        (col_sets, _txt(ex.get("sets"), ""), "C"),
                        (col_reps, reps_txt or _txt(ex.get("reps"), ""), "C"),
                    ],
                )
        note = section_notes.get(sec)
        if note and str(note).strip():
            _note(pdf, str(note).strip())

    _write_meal_summary(pdf, [day])

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
        weeks = _group_weeks(days)
        seen: dict[tuple, int] = {}
        show_week_heading = len(weeks) > 1
        last_month = 0
        for week, week_days in weeks:
            month = max(1, (week + WEEKS_PER_MONTH - 1) // WEEKS_PER_MONTH)
            index = ((week - 1) % WEEKS_PER_MONTH) + 1
            if show_week_heading and month != last_month:
                _heading(pdf, f"Tháng {month}", size=16)
                last_month = month
            fingerprint = _week_fingerprint(week_days)
            earlier = seen.get(fingerprint)
            if show_week_heading:
                _heading(pdf, f"Tuần {index}", size=14)
            if earlier is not None:
                _body(pdf, _repeat_label(earlier), bold=True)
                continue
            seen[fingerprint] = week
            for day in sorted(week_days, key=lambda item: int(item.get("day_number") or 0)):
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
