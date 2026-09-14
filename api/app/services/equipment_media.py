"""List local equipment images stored under uploads/media/equipment/<slug>/."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from app.core.config import get_settings

_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif"}
_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _safe_slug(slug: str) -> str | None:
    slug = (slug or "").strip().lower()
    return slug if _SLUG_RE.match(slug) else None


def _image_files(folder: Path) -> list[Path]:
    if not folder.is_dir():
        return []
    return sorted(
        (p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in _IMAGE_EXTS),
        key=lambda p: p.name.lower(),
    )


def _equipment_root() -> Path:
    settings = get_settings()
    return Path(settings.upload_dir) / "media" / "equipment"


_BAND_IMAGE_FOLDERS = ("resistance-band-2", "resistance-band-1")


def _folder_slugs_for(slug: str) -> tuple[str, ...]:
    if slug == "resistance-band":
        return _BAND_IMAGE_FOLDERS
    return (slug,)


def local_image_relpath(slug: str) -> str | None:
    """First photo in equipment/<slug>/, used as thumbnail."""
    safe = _safe_slug(slug)
    if not safe:
        return None
    root = _equipment_root()
    for folder in _folder_slugs_for(safe):
        files = _image_files(root / folder)
        if files:
            return f"equipment/{folder}/{files[0].name}"
    return None


def list_equipment_images(slug: str) -> list[dict[str, Any]]:
    """Every image in uploads/media/equipment/<slug>/.

    URL shape: {media_base_url}/equipment/<slug>/<filename>
    Public 'resistance-band' merges loop and tube folders.
    """
    safe = _safe_slug(slug)
    if not safe:
        return []

    settings = get_settings()
    base = settings.media_base_url.rstrip("/")
    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    for folder in _folder_slugs_for(safe):
        for file in _image_files(_equipment_root() / folder):
            key = file.name.lower()
            if key in seen:
                continue
            seen.add(key)
            url = f"{base}/equipment/{folder}/{file.name}"
            items.append({"url": url, "thumb": url, "alt": safe.replace("-", " ")})
    return items
