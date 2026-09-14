#!/usr/bin/env python3
"""Remap gymnastic-ring videos after visual review, skip Ring Chin-Up.

Usage:
    python scripts/publish_ring_and_band_videos.py          # dry-run
    python scripts/publish_ring_and_band_videos.py --apply
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import imageio_ffmpeg
from PIL import Image, ImageOps
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
API_DIR = ROOT / "api"
VIDEO_DIR = ROOT / "uploads" / "media" / "complete-exercise-library"
POSTER_DIR = ROOT / "uploads" / "media" / "complete-exercise-library-posters" / "posters"
VIDEO_REL = "complete-exercise-library"
POSTER_REL = "complete-exercise-library-posters/posters"

sys.path.insert(0, str(API_DIR))
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from app.core.database import engine  # noqa: E402
from app.core.migrations import ensure_gymnastic_rings_exercises  # noqa: E402

SCAN_FPS = 5
SCAN_WIDTH = 160
SCAN_HEIGHT = 90

# Unique token in the filename -> exercise slug. Chin-up is intentionally omitted.
PUBLISH_MAP: tuple[tuple[str, str], ...] = (
    ("20260912131228", "ring-push-up"),
    ("ring-support-hold.mp4", "ring-dip"),
    ("20260912135349", "ring-chest-fly"),
    ("20260912125420", "ring-row"),
    ("20260912151738", "ring-pull-up"),
    ("ring-biceps-curl.mp4", "ring-biceps-curl"),
    ("20260912131904", "ring-triceps-extension"),
    ("false-grip-ring-hang.mp4", "false-grip-ring-hang"),
    ("20260912122216", "ring-dead-hang"),
    ("20260912121602", "ring-pec-stretch"),
    ("20260912121854", "ring-lat-stretch"),
    ("archer-ring-row.mp4", "ring-face-pull"),
    ("ring-rear-delt-fly.mp4", "ring-rear-delt-fly"),
    ("ring-hold.mp4", "ring-hold"),
)

UNASSIGNED_KEEP_MAP: tuple[tuple[str, str], ...] = (
    ("20260912143258", "unassigned-ring-row-rear.mp4"),
    ("Human_model_performing_ring_fly", "unassigned-ring-side-lean.mp4"),
    ("unassigned-ring-hang-rear.mp4", "unassigned-ring-hang-rear.mp4"),
)

CHIN_UP_TOKENS = (
    "ring-chin-up",
    "unassigned-ring-chin-up",
    "20260912153120",
    "20260912153410",
)


def _file_digest(path: Path) -> str:
    hasher = hashlib.md5()
    with path.open("rb") as handle:
        hasher.update(handle.read(256 * 1024))
    return f"{path.stat().st_size}-{hasher.hexdigest()}"


def _find_source(token: str) -> Path | None:
    exact = VIDEO_DIR / token
    if exact.exists():
        return exact
    matches = [path for path in VIDEO_DIR.glob("*.mp4") if token in path.name]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        matches.sort(key=lambda p: (0 if p.name.startswith("ring-") or p.name.startswith("unassigned-") else 1, p.name))
        return matches[0]
    return None


def _red_score(frame: bytes) -> int:
    total = 0
    view = memoryview(frame)
    for index in range(0, len(view), 3):
        red = view[index]
        green = view[index + 1]
        blue = view[index + 2]
        dominance = (red * 2) - green - blue
        if red >= 125 and dominance >= 85 and red - green >= 25:
            total += dominance
    return total


def _scan_best_red_frame(video_path: Path) -> float:
    vf = (
        f"fps={SCAN_FPS},"
        f"scale={SCAN_WIDTH}:{SCAN_HEIGHT}:force_original_aspect_ratio=decrease,"
        f"pad={SCAN_WIDTH}:{SCAN_HEIGHT}:(ow-iw)/2:(oh-ih)/2:black"
    )
    reader = imageio_ffmpeg.read_frames(
        str(video_path), pix_fmt="rgb24", output_params=["-vf", vf]
    )
    metadata = next(reader)
    duration = float(metadata.get("duration") or 0)
    scores: list[tuple[int, int]] = []
    try:
        for frame_index, frame in enumerate(reader):
            scores.append((_red_score(frame), frame_index))
    finally:
        reader.close()
    if not scores:
        raise RuntimeError(f"Không đọc được frame: {video_path.name}")
    edge = max(1, int(len(scores) * 0.05))
    eligible = scores[edge:-edge] if len(scores) > edge * 2 else scores
    _best_score, best_index = max(eligible, key=lambda item: (item[0], -item[1]))
    timestamp = best_index / SCAN_FPS
    if duration > 0:
        timestamp = min(max(0.0, timestamp), max(0.0, duration - 0.04))
    return timestamp


def _make_poster(video_path: Path, poster_path: Path, timestamp: float) -> None:
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    poster_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="taptot-poster-") as temp_dir:
        frame_path = Path(temp_dir) / "frame.png"
        subprocess.run(
            [
                ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                str(video_path),
                "-ss",
                f"{timestamp:.3f}",
                "-frames:v",
                "1",
                "-y",
                str(frame_path),
            ],
            check=True,
        )
        with Image.open(frame_path) as source:
            image = ImageOps.pad(
                source.convert("RGB"),
                (1280, 720),
                method=Image.Resampling.LANCZOS,
                color=(0, 0, 0),
                centering=(0.5, 0.5),
            )
            image.save(poster_path, "WEBP", quality=88, method=6)


def _copy_to_name(source: Path, dest_name: str) -> Path:
    target = VIDEO_DIR / dest_name
    if source.resolve() == target.resolve():
        return target
    if target.exists() and target.resolve() != source.resolve():
        target.unlink()
    shutil.copy2(str(source), str(target))
    return target


def _exercise_row(conn, slug: str) -> tuple[int, Any]:
    marker = f"seed:gymnastic-rings:{slug}"
    row = conn.execute(
        text(
            "SELECT id, name_en, name_vi, video_url, is_active "
            "FROM exercises WHERE notes_vi = :marker LIMIT 1"
        ),
        {"marker": marker},
    ).mappings().first()
    if not row:
        raise SystemExit(f"Missing exercise for {slug} ({marker})")
    return int(row["id"]), row


def _is_ring_media_name(name: str) -> bool:
    lower = name.lower()
    if lower.startswith("band-front") or "against_band" in lower:
        return False
    return (
        lower.startswith("ring-")
        or lower.startswith("archer-ring")
        or lower.startswith("false-grip")
        or lower.startswith("unassigned-ring")
        or "20260912" in name
        or "vi_ph" in lower
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    apply = args.apply

    resolved: list[tuple[Path, str]] = []
    print("=== publish map ===")
    for token, slug in PUBLISH_MAP:
        source = _find_source(token)
        print(f"  {slug} <- {source.name if source else 'MISSING'} ({token})")
        if source is None:
            raise SystemExit(f"Missing video for {slug}")
        resolved.append((source, slug))

    used_digests = {_file_digest(source) for source, _slug in resolved}
    extras: list[Path] = []
    for path in VIDEO_DIR.glob("*.mp4"):
        if not _is_ring_media_name(path.name):
            continue
        if any(token in path.name for token in CHIN_UP_TOKENS):
            extras.append(path)
            continue
        if _file_digest(path) in used_digests:
            extras.append(path)
            continue
        extras.append(path)

    print("=== extras / duplicates / chin-up ===")
    for path in extras:
        print(f"  {path.name}")

    if apply:
        ensure_gymnastic_rings_exercises(engine)

    ctx = engine.begin() if apply else engine.connect()
    with ctx as conn:
        if apply:
            conn.execute(
                text(
                    """
                    UPDATE exercises
                    SET video_url = NULL,
                        gif_url = NULL,
                        image_url = NULL,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE notes_vi LIKE 'seed:gymnastic-rings:%'
                    """
                )
            )
            conn.execute(
                text(
                    """
                    UPDATE exercises
                    SET is_active = FALSE,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE notes_vi = 'seed:gymnastic-rings:ring-chin-up'
                    """
                )
            )

        published: list[dict[str, Any]] = []
        for source, slug in resolved:
            exercise_id, row = _exercise_row(conn, slug)
            print(f"  DB #{exercise_id} {row['name_vi']} active={row['is_active']} video={row['video_url']}")
            if not apply:
                published.append({"exercise_id": exercise_id, "slug": slug, "source": source.name})
                continue
            web_video = _copy_to_name(source, f"{slug}.mp4")
            timestamp = _scan_best_red_frame(web_video)
            poster = POSTER_DIR / f"{slug}.webp"
            _make_poster(web_video, poster, timestamp)
            poster_url = f"{POSTER_REL}/{poster.name}"
            video_url = f"{VIDEO_REL}/{web_video.name}"
            conn.execute(
                text(
                    """
                    UPDATE exercises
                    SET gif_url = :poster_url,
                        image_url = :poster_url,
                        video_url = :video_url,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = :id
                    """
                ),
                {
                    "poster_url": poster_url,
                    "video_url": video_url,
                    "id": exercise_id,
                },
            )
            published.append(
                {
                    "exercise_id": exercise_id,
                    "slug": slug,
                    "video_url": video_url,
                    "timestamp": timestamp,
                }
            )
            print(f"    PUBLISHED @{timestamp:.2f}s {video_url}")

        if apply:
            keep_names = {f"{slug}.mp4" for _source, slug in resolved}
            for token, dest_name in UNASSIGNED_KEEP_MAP:
                source = _find_source(token)
                if source is None:
                    print(f"    leftover missing {token}")
                    continue
                copied = _copy_to_name(source, dest_name)
                keep_names.add(copied.name)
                print(f"    leftover -> {copied.name}")
            for path in list(VIDEO_DIR.glob("*.mp4")):
                if not _is_ring_media_name(path.name):
                    continue
                if path.name in keep_names:
                    continue
                path.unlink()
                print(f"    deleted {path.name}")
            chin_poster = POSTER_DIR / "ring-chin-up.webp"
            if chin_poster.exists():
                chin_poster.unlink()
                print("    deleted ring-chin-up.webp")

    print(f"{'APPLIED' if apply else 'DRY-RUN (re-run with --apply)'} items={len(published)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
