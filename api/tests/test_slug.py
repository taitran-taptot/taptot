from app.services.knowledge_slug_aliases import KNOWLEDGE_SLUG_ALIASES
from app.services.slug import knowledge_slug_from_title, slugify


def test_slugify_vietnamese():
    assert slugify("Cách nấu thịt kho tàu") == "cach-nau-thit-kho-tau"
    assert slugify("  Tạ tay 10kg  ") == "ta-tay-10kg"
    assert slugify("") == "muc"


def test_knowledge_slug_from_title_strips_chapter_and_diacritics():
    assert (
        knowledge_slug_from_title("1.0 — Xác định mục tiêu tập luyện")
        == "xac-dinh-muc-tieu-tap-luyen"
    )
    assert (
        knowledge_slug_from_title("1.10 — Cách tính TDEE theo mức vận động thực tế")
        == "cach-tinh-tdee-theo-muc-van-dong-thuc-te"
    )
    assert knowledge_slug_from_title("2.4 — Carb cycling cơ bản") == "carb-cycling-co-ban"


def test_knowledge_slug_aliases_include_user_example():
    assert KNOWLEDGE_SLUG_ALIASES["10-xc-nh-mc-tiu-tp-luyn"] == "xac-dinh-muc-tieu-tap-luyen"
    assert len(KNOWLEDGE_SLUG_ALIASES) == len(set(KNOWLEDGE_SLUG_ALIASES.values()))
