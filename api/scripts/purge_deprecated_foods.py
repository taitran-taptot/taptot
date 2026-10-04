"""Hard-delete public catalog foods with status != active.

Does not touch user-owned custom foods (owner_user_id set).
Merges deleted slugs into seeds/purged_food_slugs.json so startup seeds skip them.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

API_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = API_DIR.parent
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.entities import (
    Food,
    FoodAlias,
    FoodPortion,
    MealPlanItem,
    UserDailyPlanMeal,
)

PURGED_JSON = PROJECT_ROOT / "seeds" / "purged_food_slugs.json"


def _load_purged_slugs() -> set[str]:
    if not PURGED_JSON.is_file():
        return set()
    raw = json.loads(PURGED_JSON.read_text(encoding="utf-8"))
    if isinstance(raw, dict):
        raw = raw.get("slugs") or []
    if not isinstance(raw, list):
        return set()
    return {str(s).strip().lower() for s in raw if str(s).strip()}


def _save_purged_slugs(slugs: set[str]) -> None:
    PURGED_JSON.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(s for s in slugs if s)
    PURGED_JSON.write_text(
        json.dumps({"slugs": ordered}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def purge_deprecated(db: Session) -> list[dict]:
    rows = (
        db.query(Food)
        .filter(Food.owner_user_id.is_(None), Food.status != "active")
        .all()
    )
    snapshot = [
        {
            "id": r.id,
            "slug": r.slug,
            "status": r.status,
            "food_kind": r.food_kind,
            "name_vi": r.name_vi,
        }
        for r in rows
    ]
    if not snapshot:
        return []

    ids = [r["id"] for r in snapshot]
    slugs = [r["slug"] for r in snapshot]

    db.query(Food).filter(Food.merged_into_id.in_(ids)).update(
        {Food.merged_into_id: None},
        synchronize_session=False,
    )
    db.query(MealPlanItem).filter(MealPlanItem.food_id.in_(ids)).delete(
        synchronize_session=False
    )
    db.query(UserDailyPlanMeal).filter(UserDailyPlanMeal.food_id.in_(ids)).delete(
        synchronize_session=False
    )
    db.query(FoodAlias).filter(FoodAlias.food_id.in_(ids)).delete(synchronize_session=False)
    db.query(FoodPortion).filter(FoodPortion.food_id.in_(ids)).delete(
        synchronize_session=False
    )
    db.query(Food).filter(Food.id.in_(ids)).delete(synchronize_session=False)
    db.commit()

    merged = _load_purged_slugs()
    merged.update(s.strip().lower() for s in slugs)
    _save_purged_slugs(merged)
    try:
        from app.core.migrations.ensures import _purged_food_slugs_from_file

        _purged_food_slugs_from_file.cache_clear()
    except Exception:
        pass
    return snapshot


def main() -> None:
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    log_dir = API_DIR / "exports"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"purged_foods_{stamp}.txt"

    db = SessionLocal()
    try:
        rows = purge_deprecated(db)
    finally:
        db.close()

    lines = [f"purged {len(rows)} public foods with status != active", ""]
    for r in sorted(rows, key=lambda x: (x.get("slug") or "")):
        lines.append(
            f"{r['id']}\t{r['status']}\t{r['food_kind']}\t{r['slug']}\t{r['name_vi']}"
        )
    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:1]))
    print(log_path)
    print(PURGED_JSON)


if __name__ == "__main__":
    main()
