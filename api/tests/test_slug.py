from app.services.slug import slugify


def test_slugify_vietnamese():
    assert slugify("Cách nấu thịt kho tàu") == "cach-nau-thit-kho-tau"
    assert slugify("  Tạ tay 10kg  ") == "ta-tay-10kg"
    assert slugify("") == "muc"
