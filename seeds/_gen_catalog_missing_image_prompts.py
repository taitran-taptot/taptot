# -*- coding: utf-8 -*-
"""Generate 16:9 catalog image prompts for active foods missing image_url."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "seeds" / "FOODS_CATALOG_IMAGE_PROMPTS_MISSING.md"

BOILER = (
    'Create a professional realistic product photo of Vietnamese food item "{title}". '
    "Professional realistic food product photography for a nutrition/fitness website. "
    "Format: WebP or JPEG, 1920x1080 pixels, 16:9 aspect ratio. "
    "Pure clean solid white background, minimal studio setup. "
    "Soft even natural studio lighting, sharp focus, true-to-life colors and textures. "
    "No people, no human hands, no plates, bowls, knives, cutting boards, or extra props. "
    "{prop_exception}"
    "No text, labels, logos, watermarks, or nutrition info. "
    "Single unified composition (NOT a split-panel, NOT a collage, NOT two separate frames). "
    "Show TWO states of the SAME food standing very close together side by side in one shot, "
    "almost touching, visually similar size and scale, balanced and easy to recognize. "
    "CRITICAL depth order: Part 2 (prepared/edible state) must stand in the FRONT / foreground; "
    "Part 1 (original/whole state) must stand slightly BEHIND Part 2. "
    "Subject group centered, overall food content fills about 80% of the frame. "
    "Consistent catalog style across the food dataset — prioritize realism, clarity, and recognizability over artistic effects. "
    "FRONT (Part 2 – prepared, must be in front): {front} "
    "BACK (Part 1 – original, slightly behind): {back} "
    "The two food objects must stand closely next to each other in one continuous scene, "
    "with Part 2 clearly closer to the camera than Part 1. "
    "Use the most suitable 3/4 (or best clarifying) camera angle so shape and structure are obvious. "
    "Photorealistic commercial catalog look suitable for a fitness/nutrition website food database."
)

GLASS_EXCEPTION = (
    "Exception allowed: one clear drinking glass only as Part 2. "
)

# id, name_vi, category, title (with EN clarify), front, back, use_glass_exception
ITEMS: list[tuple[int, str, str, str, str, str, bool]] = [
]


def main() -> None:
    blocks: list[str] = []
    for _food_id, _name_vi, _category, title, front, back, glass in ITEMS:
        prop = GLASS_EXCEPTION if glass else ""
        body = BOILER.format(
            title=title,
            prop_exception=prop,
            front=front,
            back=back,
        )
        blocks.append(body)

    OUT.write_text("\n\n".join(blocks) + "\n", encoding="utf-8")
    print(f"Wrote {len(ITEMS)} prompts -> {OUT}")


if __name__ == "__main__":
    main()
