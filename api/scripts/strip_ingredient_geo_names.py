"""Strip province/region suffixes from ingredient display names (keep dish names)."""

from __future__ import annotations

import sys
from pathlib import Path

API_DIR = Path(__file__).resolve().parents[1]
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.entities import Food, FoodAlias

# slug → (old_name_for_alias, new_name_vi)
RENAMES: dict[str, tuple[str, str]] = {
    "can-tay-da-lat": ("Cần tây Đà Lạt", "Cần tây"),
    "dau-tay-da-lat": ("Dâu tây Đà Lạt", "Dâu tây"),
    "ca-tam-da-lat-sa-pa": ("Cá tầm (Đà Lạt / Sa Pa)", "Cá tầm"),
    "cua-bien-ca-mau-thit": ("Cua biển Cà Mau (thịt)", "Cua biển (thịt)"),
    "cua-gach-ca-mau": ("Cua gạch Cà Mau", "Cua gạch"),
}


def run() -> None:
    db = SessionLocal()
    try:
        for slug, (old_name, new_name) in RENAMES.items():
            row = db.scalar(
                select(Food).where(Food.slug == slug, Food.food_kind == "ingredient")
            )
            if row is None:
                print(f"SKIP missing {slug}")
                continue
            prev = row.name_vi
            row.name_vi = new_name
            alias_text = old_name if prev == old_name or prev == new_name else prev
            if alias_text and alias_text != new_name:
                exists = db.scalar(
                    select(FoodAlias).where(
                        FoodAlias.food_id == row.id, FoodAlias.alias == alias_text
                    )
                )
                if exists is None:
                    db.add(FoodAlias(food_id=row.id, alias=alias_text))
                    print(f"alias +{alias_text!r} → {slug}")
            print(f"rename {slug}: {prev!r} → {new_name!r}")
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run()
