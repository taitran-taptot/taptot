from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any
from urllib.parse import parse_qs, urlparse

from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError
from app.models.entities import SitePageMedia

DEFAULT_YOUTUBE_ID = "EngW7tLk6R8"
DEFAULT_IMAGES = {
    "service_lo_trinh_image_url": "/home-lo-trinh.png",
    "service_dung_cu_image_url": "/home-dung-cu.jpg",
    "service_hlv_image_url": "/home-hlv.png",
    "about_hero_image_url": "/hero-gym.jpg",
    "about_founder_image_url": "/tran-tai.jpg",
    "about_trainer_image_url": "",
    "contact_trainer_image_url": "/hlv-nguyen-van-tien.jpg",
}

_YOUTUBE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
_ID_IN_PATH = re.compile(r"(?:embed|shorts|live)/([A-Za-z0-9_-]{11})")


def parse_youtube_id(raw: str | None) -> str:
    text = (raw or "").strip()
    if not text:
        raise BadRequestError("Thiếu link YouTube")
    if _YOUTUBE_ID_RE.fullmatch(text):
        return text
    parsed = urlparse(text)
    host = (parsed.netloc or "").lower().replace("www.", "")
    query = parse_qs(parsed.query)
    vid = (query.get("v") or [None])[0]
    if vid and _YOUTUBE_ID_RE.fullmatch(vid):
        return vid
    if host in {"youtu.be", "youtube.com", "youtube-nocookie.com", "m.youtube.com"}:
        path = parsed.path or ""
        if host == "youtu.be":
            slug = path.strip("/").split("/")[0]
            if _YOUTUBE_ID_RE.fullmatch(slug):
                return slug
        match = _ID_IN_PATH.search(path)
        if match:
            return match.group(1)
    raise BadRequestError("Link YouTube không hợp lệ")


def _now() -> datetime:
    return datetime.now(UTC)


class SitePageMediaService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_public(self) -> dict[str, Any]:
        row = self.db.get(SitePageMedia, 1)
        return self.to_dict(row)

    def upsert(self, payload: dict[str, Any]) -> dict[str, Any]:
        row = self.db.get(SitePageMedia, 1)
        if row is None:
            row = SitePageMedia(id=1)
            self.db.add(row)
            self.db.flush()
        if "home_challenge_youtube" in payload or "home_challenge_youtube_id" in payload:
            raw = payload.get("home_challenge_youtube_id") or payload.get("home_challenge_youtube")
            row.home_challenge_youtube_id = parse_youtube_id(raw)
        if "shop_guide_youtube" in payload or "shop_guide_youtube_id" in payload:
            raw = payload.get("shop_guide_youtube_id") or payload.get("shop_guide_youtube")
            row.shop_guide_youtube_id = parse_youtube_id(raw)
        for key in DEFAULT_IMAGES:
            if key in payload and payload[key] is not None:
                url = str(payload[key]).strip()
                setattr(row, key, url or None)
        row.updated_at = _now()
        self.db.commit()
        self.db.refresh(row)
        return self.to_dict(row)

    def to_dict(self, row: SitePageMedia | None) -> dict[str, Any]:
        data: dict[str, Any] = {
            "home_challenge_youtube_id": (row.home_challenge_youtube_id if row else None)
            or DEFAULT_YOUTUBE_ID,
            "shop_guide_youtube_id": (row.shop_guide_youtube_id if row else None) or DEFAULT_YOUTUBE_ID,
        }
        for key, fallback in DEFAULT_IMAGES.items():
            raw = getattr(row, key, None) if row else None
            data[key] = (raw or None) or fallback
        return data
