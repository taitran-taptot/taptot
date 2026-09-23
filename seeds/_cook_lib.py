"""Helpers + dump for Vietnamese cooking post seeds."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "seeds" / "cooking_posts"


def ing(food_slug: str, grams: float, amount_label: str, note: str | None = None) -> dict:
    row = {"food_slug": food_slug, "grams": grams, "amount_label": amount_label}
    if note:
        row["note"] = note
    return row


def md(
    origin: str,
    prep: list[str],
    steps: list[str],
    seasoning: str,
    tips: list[str],
    mistakes: list[str],
    plating: str,
    subs: list[str],
) -> str:
    def ol(items: list[str]) -> str:
        return "\n".join(f"{i}. {x}" for i, x in enumerate(items, 1))

    def ul(items: list[str]) -> str:
        return "\n".join(f"- {x}" for x in items)

    return "\n\n".join(
        [
            f"## Nguồn gốc / vùng miền\n{origin}",
            f"## Sơ chế\n{ol(prep)}",
            f"## Cách nấu\n{ol(steps)}",
            f"## Nêm nếm\n{seasoning}",
            f"## Mẹo bếp trưởng\n{ul(tips)}",
            f"## Lỗi thường gặp\n{ul(mistakes)}",
            f"## Trình bày\n{plating}",
            f"## Thay thế nguyên liệu\n{ul(subs)}",
        ]
    )


def post(
    slug: str,
    name: str,
    excerpt: str,
    servings: int,
    yield_grams: float,
    sort_order: int,
    origin: str,
    ingredients: list[dict],
    prep: list[str],
    steps: list[str],
    seasoning: str,
    tips: list[str],
    mistakes: list[str],
    plating: str,
    subs: list[str],
) -> dict:
    return {
        "slug": slug,
        "dish_slug": slug,
        "title_vi": f"Cách nấu {name}",
        "excerpt": excerpt,
        "cover_image_url": f"foods/{slug}.jpg",
        "content_md": md(origin, prep, steps, seasoning, tips, mistakes, plating, subs),
        "is_published": True,
        "sort_order": sort_order,
        "servings": servings,
        "yield_grams": yield_grams,
        "ingredients": ingredients,
    }


def dump(filename: str, posts: list[dict]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / filename
    path.write_text(json.dumps(posts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {path.name} ({len(posts)} posts)")
