"""List cooking posts that likely miss a sub-recipe."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COOKING = ROOT / "seeds" / "cooking_posts"
WATCH = {
    "cha-lua",
    "bi-heo",
    "pate-gan",
    "cha-trung",
    "gio-lua",
}
HINTS = ("hấp nóng chả", "chả thái", "thái chả", "trộn chút muối")

rows = []
for path in sorted(COOKING.glob("*.json")):
    payload = json.loads(path.read_text(encoding="utf-8"))
    posts = payload if isinstance(payload, list) else []
    for post in posts:
        slugs = [i.get("food_slug") for i in post.get("ingredients") or []]
        md = (post.get("content_md") or "").lower()
        hit_watch = sorted(set(slugs) & WATCH)
        hint = [h for h in HINTS if h in md]
        title = post.get("title_vi") or ""
        named = any(w in title.lower() for w in ("chả", "bì", "pate", "giò"))
        if hit_watch or hint or named:
            rows.append(
                f"{post.get('slug')}\t{path.name}\twatch={hit_watch}\thint={hint}\tnamed={named}"
            )
(ROOT / "seeds" / "_cook_audit.txt").write_text("\n".join(rows), encoding="utf-8")
print(len(rows))
