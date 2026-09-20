#!/usr/bin/env python3
"""Publish wall-pushup + 13-pullup videos; rename scapular row to Kéo xà 1/3.

Usage:
    python scripts/publish_wall_and_partial_pull_videos.py          # dry-run
    python scripts/publish_wall_and_partial_pull_videos.py --apply
"""

from __future__ import annotations

import argparse
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
POSTER_DIR = (
    ROOT / "uploads" / "media" / "complete-exercise-library-posters" / "posters"
)
VIDEO_REL = "complete-exercise-library"
POSTER_REL = "complete-exercise-library-posters/posters"

sys.path.insert(0, str(API_DIR))
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from app.core.database import engine  # noqa: E402

SCAN_FPS = 5
SCAN_WIDTH = 160
SCAN_HEIGHT = 90

# exercise_id, canonical slug, source filename on disk, optional rename fields
PUBLISH: tuple[tuple[int, str, str, dict[str, str] | None], ...] = (
    (846, "wall-push-up", "wall-pushup.mp4", None),
    (
        861,
        "pull-up-1-3",
        "13-pullup.mp4",
        {"name_vi": "Kéo xà 1/3", "name_en": "1/3 Pull-up"},
    ),
)


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


def _move_to_name(source: Path, dest_name: str) -> Path:
    target = VIDEO_DIR / dest_name
    if source.resolve() == target.resolve():
        return target
    if target.exists() and target.resolve() != source.resolve():
        target.unlink()
    shutil.move(str(source), str(target))
    return target


def _find_source(token: str, slug: str) -> Path | None:
    for name in (token, f"{slug}.mp4"):
        path = VIDEO_DIR / name
        if path.exists():
            return path
    matches = [
        path
        for path in VIDEO_DIR.glob("*.mp4")
        if path.name.endswith(token) or token in path.name
    ]
    if len(matches) == 1:
        return matches[0]
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    apply = args.apply

    resolved: list[tuple[int, str, Path, dict[str, str] | None]] = []
    print("=== publish map ===")
    for exercise_id, slug, source_name, rename in PUBLISH:
        source = _find_source(source_name, slug)
        print(
            f"  #{exercise_id} {slug} <- "
            f"{source.name if source else 'MISSING'} ({source_name})"
            + (f" rename={rename}" if rename else "")
        )
        if source is None:
            raise SystemExit(f"Missing video for {slug}")
        resolved.append((exercise_id, slug, source, rename))

    ctx = engine.begin() if apply else engine.connect()
    with ctx as conn:
        for exercise_id, slug, source, rename in resolved:
            row = (
                conn.execute(
                    text(
                        "SELECT id, name_vi, name_en, video_url, gif_url "
                        "FROM exercises WHERE id = :id"
                    ),
                    {"id": exercise_id},
                )
                .mappings()
                .first()
            )
            if not row:
                raise SystemExit(f"Missing exercise id={exercise_id}")
            print(
                f"  DB #{row['id']} {row['name_vi']} | {row['name_en']} "
                f"video={row['video_url']}"
            )
            if not apply:
                continue

            web_video = _move_to_name(source, f"{slug}.mp4")
            timestamp = _scan_best_red_frame(web_video)
            poster = POSTER_DIR / f"{slug}.webp"
            _make_poster(web_video, poster, timestamp)
            poster_url = f"{POSTER_REL}/{poster.name}"
            video_url = f"{VIDEO_REL}/{web_video.name}"

            params: dict[str, Any] = {
                "poster_url": poster_url,
                "video_url": video_url,
                "id": exercise_id,
            }
            set_rename = ""
            if rename:
                set_rename = ", name_vi = :name_vi, name_en = :name_en"
                params["name_vi"] = rename["name_vi"]
                params["name_en"] = rename["name_en"]

            conn.execute(
                text(
                    f"""
                    UPDATE exercises
                    SET gif_url = :poster_url,
                        image_url = :poster_url,
                        video_url = :video_url,
                        is_active = TRUE,
                        updated_at = CURRENT_TIMESTAMP
                        {set_rename}
                    WHERE id = :id
                    """
                ),
                params,
            )
            print(f"    PUBLISHED @{timestamp:.2f}s {video_url}")

    print(f"{'APPLIED' if apply else 'DRY-RUN (re-run with --apply)'} items={len(resolved)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
