from __future__ import annotations

import json
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

SUCCESS_STORY_COUNT = 7
DEFAULT_SUCCESS_LOGO = "/brand/taptot-logo-vuong.png"
_STORY_PHOTOS = ("/brand/taptot-bia-vuong.png", "/brand/taptot-logo-vuong.png")
_SAMPLE_PEOPLE = (
    ("Lan Phương", "Nhân viên văn phòng", "Lịch vừa sức nên tôi đi hết 100 ngày."),
    ("Minh Khoa", "Kỹ sư", "Tập ở nhà vẫn thấy người chắc hơn từng tuần."),
    ("Hà My", "Giáo viên", "Vẫn ăn món quen mà cân nặng giảm đều."),
    ("Quốc Bảo", "Tài xế", "Đau lưng đỡ hẳn sau khi tập đúng cách."),
    ("Thu Trang", "Mẹ bỉm sữa", "Mỗi buổi khoảng 30 phút, tôi vẫn theo được."),
    ("Đức Anh", "Sinh viên", "Nhìn nhật ký mới thấy mình tiến bộ rõ."),
    ("Ngọc Anh", "Chủ quán", "Không cần phòng gym vẫn hoàn thành lịch."),
)

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


def _blank_story() -> dict[str, str]:
    return {"image_url": "", "logo_url": "", "name": "", "occupation": "", "quote": ""}


def default_success_stories() -> list[dict[str, str]]:
    return [
        {
            "image_url": _STORY_PHOTOS[i % len(_STORY_PHOTOS)],
            "logo_url": DEFAULT_SUCCESS_LOGO,
            "name": name,
            "occupation": occupation,
            "quote": quote,
        }
        for i, (name, occupation, quote) in enumerate(_SAMPLE_PEOPLE)
    ]


def normalize_success_stories(raw: Any, *, fill_when_missing: bool) -> list[dict[str, str]]:
    if not isinstance(raw, list):
        return default_success_stories() if fill_when_missing else []
    stories: list[dict[str, str]] = []
    for item in raw[:SUCCESS_STORY_COUNT]:
        src = item if isinstance(item, dict) else {}
        stories.append(
            {
                "image_url": str(src.get("image_url") or "").strip()[:500],
                "logo_url": str(src.get("logo_url") or "").strip()[:500],
                "name": str(src.get("name") or "").strip()[:80],
                "occupation": str(src.get("occupation") or "").strip()[:80],
                "quote": str(src.get("quote") or "").strip()[:280],
            }
        )
    if fill_when_missing:
        while len(stories) < SUCCESS_STORY_COUNT:
            stories.append(_blank_story())
    return stories


def _with_sample_copy(stories: list[dict[str, str]]) -> list[dict[str, str]]:
    if any(story["name"] or story["occupation"] or story["quote"] for story in stories):
        return stories
    samples = default_success_stories()
    for story, sample in zip(stories, samples):
        if story["image_url"]:
            sample["image_url"] = story["image_url"]
        if story["logo_url"]:
            sample["logo_url"] = story["logo_url"]
    return samples


def _stored_stories(row: SitePageMedia | None) -> list[dict[str, str]]:
    if row is None or not (row.success_stories or "").strip():
        return default_success_stories()
    try:
        parsed = json.loads(row.success_stories or "")
    except json.JSONDecodeError:
        return default_success_stories()
    return _with_sample_copy(normalize_success_stories(parsed, fill_when_missing=True))


def stories_are_visible(raw: str | None) -> bool:
    if raw is None or not str(raw).strip():
        return True
    return str(raw).strip().lower() not in {"0", "false", "no", "off"}


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
        if "success_stories" in payload and payload["success_stories"] is not None:
            stories = normalize_success_stories(payload["success_stories"], fill_when_missing=True)
            row.success_stories = json.dumps(stories, ensure_ascii=False)
        if "success_stories_visible" in payload and payload["success_stories_visible"] is not None:
            row.success_stories_visible = "1" if payload["success_stories_visible"] else "0"
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
        data["success_stories"] = _stored_stories(row)
        data["success_stories_visible"] = stories_are_visible(
            row.success_stories_visible if row else None
        )
        return data
