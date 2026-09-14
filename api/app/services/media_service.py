import uuid
from pathlib import Path

from fastapi import UploadFile

from app.core.config import get_settings
from app.core.exceptions import BadRequestError

settings = get_settings()
ALLOWED = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".pdf"}


class MediaService:
    def __init__(self) -> None:
        self.upload_dir = Path(settings.upload_dir).resolve()
        self.media_root = (self.upload_dir / "media").resolve()
        self.media_root.mkdir(parents=True, exist_ok=True)

    def _safe_target_dir(self, subdir: str) -> Path:
        """Resolve subdir under media_root only (blocks path traversal)."""
        cleaned = Path(subdir.replace("\\", "/")).as_posix().strip("/")
        parts = [p for p in cleaned.split("/") if p and p not in {".", ".."}]
        # Drop leading "media" to avoid media/media/...
        if parts and parts[0] == "media":
            parts = parts[1:]
        target = self.media_root.joinpath(*parts).resolve() if parts else self.media_root
        if not str(target).startswith(str(self.media_root)):
            raise BadRequestError("Invalid upload path")
        return target

    async def save(self, file: UploadFile, subdir: str = "media") -> dict:
        if not file.filename:
            raise BadRequestError("Missing filename")
        ext = Path(file.filename).suffix.lower()
        if ext not in ALLOWED:
            raise BadRequestError(f"File type not allowed: {ext}")

        content = await file.read()
        max_bytes = settings.max_upload_mb * 1024 * 1024
        if len(content) > max_bytes:
            raise BadRequestError(f"File too large (max {settings.max_upload_mb}MB)")

        target_dir = self._safe_target_dir(subdir)
        target_dir.mkdir(parents=True, exist_ok=True)
        name = f"{uuid.uuid4().hex}{ext}"
        path = target_dir / name
        path.write_bytes(content)

        rel = path.relative_to(self.media_root).as_posix()
        return {
            "filename": name,
            "url": f"{settings.media_base_url.rstrip('/')}/{rel}",
            "size_bytes": len(content),
            "content_type": file.content_type,
        }
