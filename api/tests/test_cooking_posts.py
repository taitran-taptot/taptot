"""Cooking posts: recipe fields, ingredient hydrate, pantry seed."""

from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models.base import Base
from app.models.entities import CookingPost, Food
from app.services.cooking_post_service import CookingPostService, post_to_dict, serialize_posts


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _now() -> datetime:
    return datetime.now(UTC)


def test_hydrate_ingredients_uses_food_catalog():
    db = _session()
    db.add(
        Food(
            slug="thit-lon-ba-chi-song",
            name_vi="Thịt lợn ba chỉ (sống)",
            serving_size="100g",
            serving_grams=100,
            calories=518,
            protein_g=9,
            carbs_g=0,
            fat_g=53,
            tags=[],
            vitamins_json={},
            image_url="foods/thit-lon-ba-chi-song.jpg",
            food_kind="ingredient",
            created_at=_now(),
        )
    )
    db.add(
        Food(
            slug="thit-kho-tau-nuoc-dua",
            name_vi="Thịt kho tàu nước dừa",
            serving_size="1 suất",
            serving_grams=200,
            calories=400,
            protein_g=20,
            carbs_g=10,
            fat_g=30,
            tags=["nhom:mon-com-gia-dinh", "nhom_vi:Món Cơm Gia Đình"],
            vitamins_json={},
            food_kind="dish",
            created_at=_now(),
        )
    )
    post = CookingPost(
        slug="thit-kho-tau-nuoc-dua",
        title_vi="Cách nấu thịt kho tàu nước dừa",
        excerpt="Kho vừa miệng.",
        content_md="## Cách nấu\n1. Kho lửa nhỏ.",
        cover_image_url="foods/thit-kho-tau-nuoc-dua.jpg",
        is_published=True,
        published_at=_now(),
        sort_order=10,
        dish_slug="thit-kho-tau-nuoc-dua",
        servings=4,
        yield_grams=800,
        ingredients=[
            {
                "food_slug": "thit-lon-ba-chi-song",
                "grams": 600,
                "amount_label": "600g ba chỉ",
                "note": "cắt miếng 3cm",
            }
        ],
        created_at=_now(),
        updated_at=_now(),
    )
    db.add(post)
    db.commit()

    payload = serialize_posts(db, [post], hydrate_ingredients=True)[0]
    assert payload["servings"] == 4
    assert payload["yield_grams"] == 800
    assert payload["grams_per_serving"] == 200.0
    assert payload["group_slug"] == "mon-com-gia-dinh"
    assert payload["group_vi"] == "Món Cơm Gia Đình"
    assert payload["dish_name_vi"] == "Thịt kho tàu nước dừa"
    assert payload["ingredients"][0]["name_vi"] == "Thịt lợn ba chỉ (sống)"
    assert payload["ingredients"][0]["image_url"] == "foods/thit-lon-ba-chi-song.jpg"
    assert payload["ingredients"][0]["grams"] == 600


def test_create_stores_recipe_fields():
    db = _session()
    created = CookingPostService(db).create(
        author_user_id="00000000-0000-0000-0000-000000000001",
        title_vi="Canh chua cá lóc Nam Bộ",
        content_md="## Cách nấu\n1. Nấu canh.",
        slug="canh-chua-ca-loc-nam-bo",
        is_published=True,
        dish_slug="canh-chua-ca-loc-nam-bo",
        servings=4,
        yield_grams=1200,
        ingredients=[{"food_slug": "ca-loc-ca-qua-song", "grams": 400, "amount_label": "400g"}],
    )
    assert created["dish_slug"] == "canh-chua-ca-loc-nam-bo"
    assert created["servings"] == 4
    assert created["ingredients"][0]["food_slug"] == "ca-loc-ca-qua-song"


def test_list_skips_full_ingredient_hydrate_names_without_catalog():
    db = _session()
    post = CookingPost(
        slug="rau-muong-xao-toi",
        title_vi="Rau muống xào tỏi",
        content_md="## Xào\n1. Xào lửa lớn.",
        is_published=True,
        published_at=_now(),
        sort_order=1,
        dish_slug="rau-muong-xao-toi",
        servings=2,
        yield_grams=350,
        ingredients=[{"food_slug": "toi", "grams": 15, "amount_label": "3 tép"}],
        created_at=_now(),
        updated_at=_now(),
    )
    db.add(post)
    db.commit()
    payload = post_to_dict(post, hydrate_ingredients=False)
    assert payload["ingredients"][0]["food_slug"] == "toi"
    assert "image_url" not in payload["ingredients"][0]


def test_seed_files_cover_all_traditional_dishes():
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    dishes = {
        d["slug"]
        for d in json.loads((root / "seeds" / "foods_traditional_dishes.json").read_text(encoding="utf-8"))
    }
    posts = []
    for path in (root / "seeds" / "cooking_posts").glob("*.json"):
        posts.extend(json.loads(path.read_text(encoding="utf-8")))
    slugs = {p["slug"] for p in posts}
    assert len(posts) == 95
    assert slugs == dishes
    pantry = json.loads((root / "seeds" / "foods_cooking_pantry.json").read_text(encoding="utf-8"))
    assert len(pantry["foods"]) >= 40
    merged = {
        "toi",
        "toi-tay",
        "hanh-tim",
        "gung",
        "rieng",
        "nghe",
        "can-tay",
        "hen",
        "luon",
        "ca-linh",
        "chan-gio-heo",
        "canh-ga",
        "bac-ha-rau",
        "ngo-gai",
        "gau-bo",
        "gio-bo",
        "ca-chua",
        "thit-lon-than-nac-song",
        "thit-lon-nac-vai-song",
        "thit-nac-dam-heo",
        "gia-do",
        "dua-leo",
        "ngo-ri",
        "dua-thom",
        "ca-rot-song",
        "hanh-tay",
        "kho-qua-muop-dang",
        "mong-toi",
        "dau-bap-luoc",
        "tom-su-song",
        "tom-the-song",
        "muc-ong-song",
        "cua-bien-thit",
        "ghe-thit",
        "ngao-ngheu",
        "ca-chep-song",
        "ca-dieu-hong-song",
        "ca-thu-song",
        "ca-basa-ca-tra-fillet-song",
        "thit-bo-than-song",
        "thit-bo-bap-song",
        "thit-bo-nam-song",
    }
    pantry_slugs = {item["slug"] for item in pantry["foods"]}
    assert not (merged & pantry_slugs)
    used = {ing["food_slug"] for post in posts for ing in post.get("ingredients") or []}
    assert not (merged & used)
