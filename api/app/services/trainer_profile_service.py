"""Trainer public profile + awards/certificates."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, NotFoundError
from app.models.entities import TrainerCredential, TrainerProfile, User


class TrainerProfileService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _ensure_profile(self, trainer_id: str) -> TrainerProfile:
        profile = self.db.query(TrainerProfile).filter(TrainerProfile.user_id == trainer_id).first()
        if profile:
            if not profile.share_token:
                profile.share_token = secrets.token_urlsafe(12)
                self.db.commit()
                self.db.refresh(profile)
            return profile
        user = self.db.get(User, trainer_id)
        profile = TrainerProfile(
            user_id=trainer_id,
            business_name=user.display_name if user else None,
            full_name=user.display_name if user else None,
            brand_color="#22c55e",
            is_verified=False,
            max_clients=50,
            share_token=secrets.token_urlsafe(12),
            created_at=datetime.now(UTC),
        )
        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)
        return profile

    def get_mine(self, trainer_id: str) -> dict[str, Any]:
        profile = self._ensure_profile(trainer_id)
        user = self.db.get(User, trainer_id)
        return self._detail(profile, user)

    def update_mine(
        self,
        trainer_id: str,
        *,
        full_name: str | None = None,
        age: int | None = None,
        years_experience: int | None = None,
        bio_vi: str | None = None,
        business_name: str | None = None,
        gym_name: str | None = None,
    ) -> dict[str, Any]:
        profile = self._ensure_profile(trainer_id)
        if full_name is not None:
            profile.full_name = full_name.strip() or None
        if age is not None:
            profile.age = age
        if years_experience is not None:
            profile.years_experience = years_experience
        if bio_vi is not None:
            profile.bio_vi = bio_vi.strip() or None
        if business_name is not None:
            profile.business_name = business_name.strip() or None
        if gym_name is not None:
            profile.gym_name = gym_name.strip() or None
        self.db.commit()
        self.db.refresh(profile)
        return self._detail(profile, self.db.get(User, trainer_id))

    def add_credential(
        self,
        trainer_id: str,
        *,
        kind: str,
        title: str,
        description: str | None,
        image_urls: list[str],
    ) -> dict[str, Any]:
        kind_norm = (kind or "").strip().lower()
        if kind_norm not in {"award", "certificate"}:
            raise BadRequestError("Loại phải là award hoặc certificate")
        title_clean = (title or "").strip()
        if not title_clean:
            raise BadRequestError("Thiếu tiêu đề")
        urls = [u.strip() for u in (image_urls or []) if u and str(u).strip()]
        if not urls:
            raise BadRequestError("Cần ít nhất 1 ảnh minh chứng")
        self._ensure_profile(trainer_id)
        row = TrainerCredential(
            trainer_id=trainer_id,
            kind=kind_norm,
            title=title_clean,
            description=(description or "").strip() or None,
            image_urls=urls,
            created_at=datetime.now(UTC),
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self._cred_dict(row)

    def delete_credential(self, trainer_id: str, credential_id: int) -> None:
        row = (
            self.db.query(TrainerCredential)
            .filter(
                TrainerCredential.id == credential_id,
                TrainerCredential.trainer_id == trainer_id,
            )
            .first()
        )
        if not row:
            raise NotFoundError("TrainerCredential", credential_id)
        self.db.delete(row)
        self.db.commit()

    def get_public(self, share_token: str) -> dict[str, Any]:
        token = (share_token or "").strip()
        if not token:
            raise NotFoundError("TrainerProfile", share_token)
        profile = self.db.query(TrainerProfile).filter(TrainerProfile.share_token == token).first()
        if not profile:
            raise NotFoundError("TrainerProfile", share_token)
        user = self.db.get(User, profile.user_id)
        return self._detail(profile, user, public=True)

    def _credentials(self, trainer_id: str) -> list[dict[str, Any]]:
        rows = (
            self.db.query(TrainerCredential)
            .filter(TrainerCredential.trainer_id == trainer_id)
            .order_by(TrainerCredential.created_at.desc())
            .all()
        )
        return [self._cred_dict(r) for r in rows]

    def _cred_dict(self, row: TrainerCredential) -> dict[str, Any]:
        urls = row.image_urls if isinstance(row.image_urls, list) else []
        return {
            "id": row.id,
            "kind": row.kind,
            "title": row.title,
            "description": row.description,
            "image_urls": urls,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }

    def _detail(
        self,
        profile: TrainerProfile,
        user: User | None,
        *,
        public: bool = False,
    ) -> dict[str, Any]:
        token = profile.share_token
        creds = self._credentials(str(profile.user_id))
        data: dict[str, Any] = {
            "full_name": profile.full_name or (user.display_name if user else None),
            "age": profile.age,
            "years_experience": profile.years_experience,
            "bio_vi": profile.bio_vi,
            "business_name": profile.business_name,
            "gym_name": profile.gym_name,
            "is_verified": bool(profile.is_verified),
            "awards": [c for c in creds if c["kind"] == "award"],
            "certificates": [c for c in creds if c["kind"] == "certificate"],
            "share_token": token,
            "share_url_path": f"/hlv/p/{token}" if token else None,
        }
        if not public and user:
            data["email"] = user.email
            data["display_name"] = user.display_name
        return data
