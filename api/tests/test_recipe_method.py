"""Cook steps that name a water volume must list nước lọc on the BOM."""

import json
from pathlib import Path

from app.services.recipe_method import method_liquid_gaps, with_stated_water

ROOT = Path(__file__).resolve().parents[2]


def test_plain_water_in_the_method_is_a_gap_until_it_is_on_the_bom():
    post = {
        "content_md": "## Cách nấu\n1. Cho gạo và 400ml nước lạnh vào nồi.\n",
        "ingredients": [{"food_slug": "gao-te", "grams": 320}],
    }
    assert method_liquid_gaps(post)
    fixed = with_stated_water(post)
    assert method_liquid_gaps(fixed) == []
    water = next(i for i in fixed["ingredients"] if i["food_slug"] == "nuoc-loc")
    assert water["grams"] == 400


def test_published_recipes_include_stated_plain_water():
    gaps: list[tuple[str, list[str]]] = []
    folder = ROOT / "seeds" / "cooking_posts"
    for path in sorted(folder.glob("*.json")):
        for post in json.loads(path.read_text(encoding="utf-8")):
            found = method_liquid_gaps(post)
            if found:
                gaps.append((str(post.get("slug")), found))
    assert gaps == []


def test_fish_sauce_and_troubleshooting_water_are_not_plain_water():
    post = {
        "content_md": (
            "## Cách nấu\n1. Thêm 30ml nước mắm.\n\n"
            "## Lỗi thường gặp\n- Khô: thêm 50ml nước.\n"
        ),
        "ingredients": [{"food_slug": "nuoc-mam", "grams": 30}],
    }
    assert method_liquid_gaps(post) == []
