"""One-shot: import seeds/foods_catalog_perfect_v1.xlsx into the live DB."""

from __future__ import annotations

import sys
from pathlib import Path

API_DIR = Path(__file__).resolve().parents[1]
ROOT = API_DIR.parent
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from app.core.database import SessionLocal, engine
from app.core.migrations.ensures import ensure_deprecated_foods
from app.services.food_catalog_perfect_import import (
    apply_perfect_catalog,
    default_perfect_xlsx_path,
    load_perfect_master_rows,
)


def main() -> None:
    xlsx = default_perfect_xlsx_path(ROOT)
    if not xlsx.is_file():
        raise SystemExit(f"missing {xlsx}")
    rows = load_perfect_master_rows(xlsx)
    print(f"loaded {len(rows)} master rows from {xlsx}")
    with SessionLocal() as db:
        stats = apply_perfect_catalog(db, rows)
    ensure_deprecated_foods(engine)
    print(
        f"updated={stats.updated} skipped_missing={stats.skipped_missing} "
        f"aliases_added={stats.aliases_added}"
    )
    if stats.missing_slugs:
        print("missing slugs:", ", ".join(stats.missing_slugs[:30]))


if __name__ == "__main__":
    main()
