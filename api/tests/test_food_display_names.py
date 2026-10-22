from app.core.migrations.ensures import clean_food_name_vi


def test_english_gloss_is_removed_from_food_name():
    assert clean_food_name_vi("Thăn nội bò (Tenderloin / Thăn chuột)") == "Thăn nội bò"
    assert clean_food_name_vi("Sườn bò có xương (T-Bone / Tomahawk)") == "Sườn bò có xương"
    assert clean_food_name_vi("Thịt nọng bò / Ức bò (Brisket)") == "Thịt nọng bò / Ức bò"


def test_vietnamese_only_parentheses_stay():
    assert clean_food_name_vi("Ba chỉ (Ba rọi thường)") == "Ba chỉ (Ba rọi thường)"
    assert clean_food_name_vi("Cánh gà nguyên chiếc (Cánh tiên)") == "Cánh gà nguyên chiếc (Cánh tiên)"
    assert clean_food_name_vi("Khổ qua (mướp đắng)") == "Khổ qua (mướp đắng)"
    assert clean_food_name_vi("Ức gà không da (sống)") == "Ức gà không da (sống)"
