"""Rename knowledge markdown files and rewrite slug/file in upsert catalog."""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

API_DIR = Path(__file__).resolve().parents[1]
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from app.services.slug import knowledge_slug_from_title

ROOT = API_DIR / "app" / "data" / "knowledge"
UPSERT = API_DIR / "scripts" / "upsert_knowledge_articles.py"


def _articles() -> list[dict]:
    mod = ast.parse(UPSERT.read_text(encoding="utf-8"))
    for node in mod.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == "ARTICLES":
                    return ast.literal_eval(node.value)
    raise SystemExit("ARTICLES not found")


def mapping() -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    seen: set[str] = set()
    for art in _articles():
        old = art["slug"]
        new = knowledge_slug_from_title(art["title_vi"])
        if new in seen:
            raise SystemExit(f"duplicate new slug {new}")
        seen.add(new)
        pairs.append((old, new))
    return pairs


def rewrite_upsert(pairs: list[tuple[str, str]]) -> None:
    text = UPSERT.read_text(encoding="utf-8")
    for old, new in pairs:
        text = text.replace(f"'slug': '{old}'", f"'slug': '{new}'")
        text = text.replace(f"'file': '{old}.md'", f"'file': '{new}.md'")
    UPSERT.write_text(text, encoding="utf-8")


def rename_markdown(pairs: list[tuple[str, str]]) -> None:
    # Two-phase: old -> tmp -> new, in case of collisions (none expected)
    for old, new in pairs:
        src = ROOT / f"{old}.md"
        if not src.is_file():
            print(f"missing {src.name}")
            continue
        body = src.read_text(encoding="utf-8")
        body = body.replace(f"/media/knowledge/{old}/", f"/media/knowledge/{new}/")
        tmp = ROOT / f"{old}.__renaming__.md"
        tmp.write_text(body, encoding="utf-8")
        src.unlink()
    for old, new in pairs:
        tmp = ROOT / f"{old}.__renaming__.md"
        dest = ROOT / f"{new}.md"
        if tmp.is_file():
            if dest.exists():
                raise SystemExit(f"dest exists {dest.name}")
            tmp.rename(dest)
            print(f"renamed {old}.md -> {new}.md")


def main() -> None:
    pairs = mapping()
    for old, new in pairs:
        print(f"{old} -> {new}")
    rewrite_upsert(pairs)
    rename_markdown(pairs)
    print("done")


if __name__ == "__main__":
    main()
