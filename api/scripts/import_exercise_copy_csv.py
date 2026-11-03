"""Apply reviewed exercise copy from CSV onto the DB and exercise_copy_vi.json.

The API rewrites instruction fields from seeds/exercise_copy_vi.json on startup,
so the JSON must change together with the database.
"""

from __future__ import annotations

import csv
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

API_DIR = Path(__file__).resolve().parents[1]
ROOT = API_DIR.parent
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from app.core.database import SessionLocal
from app.models.entities import Exercise
from scripts.export_exercises_xlsx import _steps_text

SEED_PATH = ROOT / "seeds" / "exercise_copy_vi.json"
CSV_PATH = Path(r"C:\Users\Tran Tai\Downloads\bai_tap_export.csv")


def _lines(value: str) -> list[str]:
    return [line.strip() for line in (value or "").splitlines() if line.strip()]


def _load_csv() -> list[dict[str, str]]:
    with CSV_PATH.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    required = {"Tên bài", "Cách thực hiện", "Lỗi thường gặp", "Mẹo"}
    if not rows or not required.issubset(rows[0]):
        missing = required - set(rows[0] if rows else ())
        raise SystemExit(f"CSV thiếu cột: {', '.join(sorted(missing))}")
    return rows


def main() -> None:
    csv_rows = _load_csv()
    by_name: dict[str, dict[str, str]] = {}
    duplicate_csv: list[str] = []
    for row in csv_rows:
        name = (row.get("Tên bài") or "").strip()
        if not name:
            continue
        if name in by_name:
            duplicate_csv.append(name)
        by_name[name] = row

    now = datetime.now(UTC).replace(tzinfo=None)
    updated_ids: list[int] = []
    missing: list[str] = []
    db = SessionLocal()
    try:
        active = db.query(Exercise).filter(Exercise.is_active.is_(True)).all()
        active_names = {(ex.name_vi or "").strip() for ex in active}
        for name in by_name:
            if name not in active_names:
                missing.append(name)
        for ex in active:
            name = (ex.name_vi or "").strip()
            row = by_name.get(name)
            if row is None:
                continue
            had_steps = bool(_steps_text(ex.instruction_steps_vi).strip())
            steps = _lines(row.get("Cách thực hiện") or "")
            mistakes = (row.get("Lỗi thường gặp") or "").strip()
            tips = (row.get("Mẹo") or "").strip()
            ex.instruction_steps_vi = steps or None
            ex.common_mistakes_vi = mistakes or None
            ex.tips_vi = tips or None
            if not had_steps:
                ex.instruction_vi = (row.get("Cách thực hiện") or "").strip() or None
            ex.updated_at = now
            updated_ids.append(int(ex.id))
        db.commit()
    finally:
        db.close()

    seed = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    seed_hits = 0
    seed_miss: list[str] = []
    for item in seed:
        name = str(item.get("name_vi") or "").strip()
        row = by_name.get(name)
        if row is None:
            continue
        steps = _lines(row.get("Cách thực hiện") or "")
        mistakes = _lines(row.get("Lỗi thường gặp") or "")
        tips = (row.get("Mẹo") or "").strip()
        item["instruction_steps_vi"] = steps
        item["common_mistakes_vi"] = mistakes
        item["tips_vi"] = tips
        if not str(item.get("instruction_vi") or "").strip():
            item["instruction_vi"] = (row.get("Cách thực hiện") or "").strip()
        seed_hits += 1
    matched_seed_names = {
        str(item.get("name_vi") or "").strip()
        for item in seed
        if str(item.get("name_vi") or "").strip() in by_name
    }
    for name in by_name:
        if name not in matched_seed_names:
            seed_miss.append(name)
    SEED_PATH.write_text(json.dumps(seed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"csv_rows={len(csv_rows)} unique_names={len(by_name)}")
    print(f"db_updated={len(updated_ids)} db_missing={len(missing)}")
    print(f"seed_updated={seed_hits} seed_missing={len(seed_miss)}")
    if duplicate_csv:
        print("duplicate_csv:", ", ".join(duplicate_csv[:20]))
    if missing:
        print("missing_in_db:")
        for name in missing:
            print(f"  - {name}")
    if seed_miss:
        print("missing_in_seed:")
        for name in seed_miss:
            print(f"  - {name}")


if __name__ == "__main__":
    main()
