#!/usr/bin/env python3
"""Remap the 3 home no-equip back videos that were published onto stretch rows.

Sources (wrong stretch slugs after the previous publish, plus leftover inverted clip):
  video_inverted_no_red.mp4  -> Table Inverted Row
  biceps-stretch.mp4         -> Bent-Over Backpack Row  (was the bent-over clip)
  thread-the-needle.mp4      -> One-Arm Backpack Row    (was the backpack clip)

Also clears those stretch URLs, deactivates stretches without a real video,
and deactivates remaining home improvised rows that still have no video.
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

# id, canonical slug, source filename currently on disk
HOME_BACK_MAP: tuple[tuple[int, str, str], ...] = (
    (827, "table-inverted-row", "video_inverted_no_red.mp4"),
    (823, "bent-over-backpack-row", "biceps-stretch.mp4"),
    (824, "one-arm-backpack-row", "thread-the-needle.mp4"),
)
STRETCH_CLEAR_IDS = (793, 797)
KEEP_ACTIVE_IDS = {823, 824, 827}
SCAN_FPS = 5
SCAN_WIDTH = 160
SCAN_HEIGHT = 90


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


def _move_to_slug(source: Path, slug: str) -> Path:
    target = VIDEO_DIR / f"{slug}.mp4"
    if source.resolve() == target.resolve():
        return target
    if not source.exists():
        if target.exists():
            return target
        raise FileNotFoundError(source)
    if target.exists() and target.resolve() != source.resolve():
        target.unlink()
    shutil.move(str(source), str(target))
    return target


def _publish(conn, *, apply: bool) -> list[dict[str, Any]]:
    published: list[dict[str, Any]] = []
    for exercise_id, slug, source_name in HOME_BACK_MAP:
        source = VIDEO_DIR / source_name
        canonical = VIDEO_DIR / f"{slug}.mp4"
        chosen = source if source.exists() else canonical
        print(f"  {slug} <- {chosen.name if chosen.exists() else 'MISSING'} id={exercise_id}")
        if not chosen.exists():
            raise SystemExit(f"Missing video for {slug}: tried {source_name} and {canonical.name}")
        if not apply:
            published.append({"exercise_id": exercise_id, "slug": slug, "source": chosen.name})
            continue
        web_video = _move_to_slug(chosen, slug)
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
                    is_active = TRUE,
                    exercise_type = 'main',
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
                "poster_url": poster_url,
                "video_url": video_url,
                "timestamp": timestamp,
            }
        )
        print(f"    PUBLISHED @{timestamp:.2f}s {video_url}")
    return published


def _clear_wrong_stretch(conn, *, apply: bool) -> None:
    rows = conn.execute(
        text(
            """
            SELECT id, name_en, is_active, video_url
            FROM exercises WHERE id = ANY(:ids)
            """
        ),
        {"ids": list(STRETCH_CLEAR_IDS)},
    ).mappings().all()
    print("Clear stretch media (wrong back clips):")
    for row in rows:
        print(f"  #{row['id']} {row['name_en']} video={row['video_url']}")
    if not apply:
        return
    conn.execute(
        text(
            """
            UPDATE exercises
            SET gif_url = NULL,
                image_url = NULL,
                video_url = NULL,
                is_active = FALSE,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ANY(:ids)
            """
        ),
        {"ids": list(STRETCH_CLEAR_IDS)},
    )


def _deactivate_remaining_home_improvised(conn, *, apply: bool) -> None:
    rows = conn.execute(
        text(
            """
            SELECT e.id, e.name_en, e.name_vi
            FROM exercises e
            WHERE e.is_active IS TRUE
              AND COALESCE(TRIM(e.video_url), '') = ''
              AND e.venue = 'home'
              AND (
                lower(e.name_en) LIKE '%towel%'
                OR lower(e.name_en) LIKE '%backpack%'
                OR lower(e.name_en) LIKE '%table %'
                OR lower(e.name_vi) LIKE '%khăn%'
                OR lower(e.name_vi) LIKE '%ba lô%'
                OR lower(e.name_vi) LIKE '%dưới bàn%'
                OR lower(e.name_vi) LIKE '%mép bàn%'
              )
              AND e.id <> ALL(:keep)
            ORDER BY e.id
            """
        ),
        {"keep": list(KEEP_ACTIVE_IDS)},
    ).mappings().all()
    print(f"Home improvised still missing video: {len(rows)}")
    for row in rows:
        print(f"  #{row['id']} {row['name_vi']} ({row['name_en']})")
    if not apply or not rows:
        return
    ids = [int(row["id"]) for row in rows]
    result = conn.execute(
        text(
            """
            UPDATE exercises
            SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP
            WHERE id = ANY(:ids)
            """
        ),
        {"ids": ids},
    )
    print(f"Deactivated {result.rowcount}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    apply = args.apply
    ctx = engine.begin() if apply else engine.connect()
    with ctx as conn:
        print("=== remap 3 home back videos ===")
        _publish(conn, apply=apply)
        _clear_wrong_stretch(conn, apply=apply)
        _deactivate_remaining_home_improvised(conn, apply=apply)
    print("APPLIED" if apply else "DRY-RUN (re-run with --apply)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
