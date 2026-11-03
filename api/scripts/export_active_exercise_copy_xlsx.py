"""Export active exercises: name, steps, mistakes, tips."""

from __future__ import annotations

import shutil
import sys
from datetime import datetime
from pathlib import Path

API_DIR = Path(__file__).resolve().parents[1]
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from app.core.database import SessionLocal
from app.models.entities import Exercise
from scripts.export_exercises_xlsx import _steps_text

HEADER = ["Tên bài", "Cách thực hiện", "Lỗi thường gặp", "Mẹo"]
HEADER_FILL = PatternFill("FF1F4E3D", fill_type="solid")
HEADER_FONT = Font(bold=True, color="FFFFFFFF")


def _how_to(ex: Exercise) -> str:
    steps = _steps_text(ex.instruction_steps_vi).strip()
    if steps:
        return steps
    return (ex.instruction_vi or "").strip()


def main() -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    out_dir = API_DIR / "exports"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"bai_tap_dang_dung_{stamp}.xlsx"

    db = SessionLocal()
    try:
        rows = (
            db.query(Exercise)
            .filter(Exercise.is_active.is_(True))
            .order_by(Exercise.name_vi, Exercise.id)
            .all()
        )
        wb = Workbook()
        ws = wb.active
        assert ws is not None
        ws.title = "Bai_tap_dang_dung"
        ws.append(HEADER)
        for col in range(1, 5):
            cell = ws.cell(1, col)
            cell.fill = HEADER_FILL
            cell.font = HEADER_FONT
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = "A1:D1"
        for ex in rows:
            ws.append(
                [
                    (ex.name_vi or ex.name_en or "").strip(),
                    _how_to(ex),
                    (ex.common_mistakes_vi or "").strip(),
                    (ex.tips_vi or "").strip(),
                ]
            )
        widths = [36, 64, 48, 48]
        for col, width in enumerate(widths, start=1):
            ws.column_dimensions[get_column_letter(col)].width = width
        for row_idx in range(2, ws.max_row + 1):
            for col in range(1, 5):
                ws.cell(row_idx, col).alignment = Alignment(wrap_text=True, vertical="top")
            ws.row_dimensions[row_idx].height = 72
        wb.save(out)
    finally:
        db.close()

    desktop = Path.home() / "Desktop" / out.name
    shutil.copy2(out, desktop)
    print(f"Exported {len(rows)} active exercises")
    print(out)
    print(desktop)
    return out


if __name__ == "__main__":
    main()
