"""Sync traditional dish macros from cooking-post BOMs (not Perfect Master)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "seeds"))

import _sync_dish_macros_from_recipes as dish_macros  # noqa: E402


def main() -> None:
    dishes = dish_macros.sync_dishes()
    print(f"updated {len(dishes)} dishes from recipe BOM → {dish_macros.DISHES_PATH}")


if __name__ == "__main__":
    main()
