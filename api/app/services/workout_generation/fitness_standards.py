"""Gender-aware fitness standards for the familiarization programmes.

This module is deliberately deterministic.  It is the single backend source
for the public standards, route recommendation, and generation starting tier.
"""

from __future__ import annotations

from typing import Any

FAMILIARIZATION_PATHS = frozenset(
    {"first_push_pull", "basic_foundation", "advanced_foundation"}
)

PATH_META: tuple[dict[str, Any], ...] = (
    {
        "key": "first_push_pull",
        "label_vi": "Nhập môn & gia cố khớp",
        "description_vi": (
            "60 ngày · 3 buổi/tuần · 40–45 phút. Tạo nếp thần kinh, thích ứng gân khớp, "
            "sửa form đẩy ngực và kéo lưng. Dụng cụ: tường, ghế/bàn, balo sách, xà cửa."
        ),
        "target_level": "first_rep",
        "duration_days": 60,
        "duration_weeks": 9,
    },
    {
        "key": "basic_foundation",
        "label_vi": "Xây sức mạnh nền",
        "description_vi": (
            "60 ngày · 3 buổi/tuần · 45–50 phút. Tăng lực đẩy/kéo, tăng cơ và "
            "hoàn thiện chuỗi cơ sau. Cần xà đơn, balo 5–8 kg, bàn/ghế chắc."
        ),
        "target_level": "basic",
        "duration_days": 60,
        "duration_weeks": 9,
    },
    {
        "key": "advanced_foundation",
        "label_vi": "Nền tảng nâng cao",
        "description_vi": (
            "60 ngày · 3 buổi/tuần · khoảng 50 phút. Sức mạnh tương đối, sức bền cơ "
            "và tim mạch — sẵn sàng chơi thể thao. Xà đơn, ghế, balo 8–10 kg, dây band nếu có."
        ),
        "target_level": "advanced",
        "duration_days": 60,
        "duration_weeks": 9,
    },
)

_EXIT_GOALS: dict[str, tuple[dict[str, Any], ...]] = {
    "male": (
        {
            "key": "push",
            "label_vi": "Chống đẩy chuẩn sàn",
            "display_vi": "3–8 lần sàn (hoặc kê ghế)",
        },
        {
            "key": "pull",
            "label_vi": "Kéo xà hoặc kéo người nằm (bàn/xà)",
            "display_vi": "1–2 kéo xà hoặc 6–10 kéo người nằm (bàn/xà)",
        },
        {"key": "squat", "label_vi": "Squat thể trọng", "display_vi": "12–25 lần"},
        {"key": "plank", "label_vi": "Plank", "display_vi": "20–50 giây"},
        {"key": "run", "label_vi": "Đi bộ/chạy 10 phút", "display_vi": "0,8–1,2 km"},
    ),
    "female": (
        {"key": "push", "label_vi": "Chống đẩy quỳ gối", "display_vi": "4–10 lần"},
        {"key": "pull", "label_vi": "Treo người trên xà", "display_vi": "20–45 giây"},
        {"key": "squat", "label_vi": "Squat thể trọng", "display_vi": "10–20 reps"},
        {"key": "plank", "label_vi": "Plank", "display_vi": "15–40 giây"},
        {"key": "run", "label_vi": "Đi bộ/chạy 10 phút", "display_vi": "0,7–1,0 km"},
    ),
}

_STANDARD_ROWS: dict[str, dict[str, tuple[dict[str, Any], ...]]] = {
    "male": {
        "basic": (
            {"key": "push", "label_vi": "Chống đẩy", "display_vi": "8–15 lần sàn"},
            {
                "key": "pull",
                "label_vi": "Kéo",
                "display_vi": "2–6 kéo xà hoặc kéo người nằm (bàn/xà)",
            },
            {"key": "squat", "label_vi": "Squat thể trọng", "display_vi": "20–35 lần"},
            {"key": "plank", "label_vi": "Plank", "display_vi": "45–75 giây"},
            {"key": "run", "label_vi": "Đi bộ/chạy 10 phút", "display_vi": "1,1–1,5 km"},
        ),
        "advanced": (
            {"key": "push", "label_vi": "Chống đẩy", "display_vi": "12–25 lần sàn"},
            {
                "key": "pull",
                "label_vi": "Kéo",
                "display_vi": "4–10 kéo xà hoặc kéo người nằm thấp",
            },
            {"key": "squat", "label_vi": "Squat thể trọng", "display_vi": "25–45 lần"},
            {"key": "plank", "label_vi": "Plank", "display_vi": "60–90 giây"},
            {
                "key": "run",
                "label_vi": "Đi bộ dốc/chạy 10 phút",
                "display_vi": "1,3–1,8 km",
            },
        ),
    },
    "female": {
        "basic": (
            {
                "key": "push",
                "label_vi": "Chống đẩy",
                "display_vi": "1–6 lần sàn hoặc 6–12 kê bục 20 cm",
            },
            {
                "key": "pull",
                "label_vi": "Kéo",
                "display_vi": "4–8 kéo người nằm (bàn/xà) hoặc 2–4 kéo xà trợ lực dây",
            },
            {"key": "squat", "label_vi": "Squat thể trọng", "display_vi": "18–28 lần"},
            {"key": "plank", "label_vi": "Plank", "display_vi": "30–60 giây"},
            {"key": "run", "label_vi": "Đi bộ/chạy 10 phút", "display_vi": "0,9–1,3 km"},
        ),
        "advanced": (
            {"key": "push", "label_vi": "Chống đẩy", "display_vi": "3–8 lần sàn"},
            {
                "key": "pull",
                "label_vi": "Kéo",
                "display_vi": "1–2 kéo xà hoặc 6 kéo người nằm/dây",
            },
            {"key": "squat", "label_vi": "Squat thể trọng", "display_vi": "20–35 lần"},
            {"key": "plank", "label_vi": "Plank", "display_vi": "45–90 giây"},
            {"key": "run", "label_vi": "Đi bộ/chạy 10 phút", "display_vi": "1,1–1,5 km"},
        ),
    },
}

NUTRITION_PRINCIPLES_VI = (
    "Đạm 1,6–2,0 g/kg cân nặng mỗi ngày từ món quen (trứng, thịt nạc, cá, đậu). "
    "Uống khoảng 40–45 ml nước/kg, ngủ 7–8,5 tiếng trước 23h. "
    "Ngày nghỉ đi bộ nhẹ 15–20 phút — cơ lớn lên khi nghỉ, không tập dồn."
)

_MISSION: dict[str, str] = {
    "first_push_pull": (
        "Bạn đang ở cấp 1 — nhập môn và gia cố khớp. Mỗi tuần 3 buổi xen kẽ: "
        "đẩy + thân dưới, kéo + chuỗi sau, rồi toàn thân. "
        "Tuần 1–2 học form với chống đẩy kê tay và chèo balo; tuần 3+ kéo người nằm "
        "(bàn hoặc xà); tuần 5+ treo xà siết bả vai. Còn dư 3–4 cái lúc đầu, 2–3 khi đã quen. "
        "Ngày nghỉ là bắt buộc để gân khớp hồi phục."
    ),
    "basic_foundation": (
        "Bạn đang ở cấp 2 — xây sức mạnh nền. Ba buổi/tuần: đẩy + chân, kéo + chuỗi sau, "
        "toàn thân. Tập chống đẩy sàn, kéo xà trợ lực hoặc kéo người nằm thấp, lunge và "
        "đẩy hông. Còn dư 2 cái, buổi khoảng 45–50 phút. Xà đơn và balo 5–8 kg dùng từ buổi 1."
    ),
    "advanced_foundation": (
        "Bạn đang ở cấp 3 — nền tảng nâng cao. Ba buổi/tuần mật độ cao hơn (còn dư 1–2 cái), "
        "khoảng 50 phút: chống đẩy sàn hoặc ghế thấp, kéo xà / kéo người nằm (bàn/xà), "
        "lunge hoặc lunge chân sau kê ghế, giữ thân rỗng và đi bộ/chạy bền. Chuẩn bị thể lực để chơi thể thao."
    ),
}

_OUTCOMES: dict[str, dict[str, str]] = {
    "first_push_pull": {
        "male": (
            "Ngày 59 kiểm tra khoảng: 3–8 chống đẩy sàn (hoặc kê ghế), "
            "1–2 kéo xà (hoặc 6–10 kéo người nằm), squat 12–25, plank 20–50 giây, "
            "đi/chạy 10 phút 0,8–1,2 km. "
            "Tập xong bạn có lực đẩy thân trên, vai ổn định hơn và gân khớp sẵn sàng lên cấp 2."
        ),
        "female": (
            "Ngày 59 kiểm tra khoảng: 4–10 chống đẩy quỳ, treo xà 20–45 giây, squat 10–20, "
            "plank 15–40 giây, đi/chạy 10 phút 0,7–1,0 km. "
            "Tập xong lực nắm tay và lưng trên khỏe hơn, khớp vai được bảo vệ để tiến cấp 2."
        ),
    },
    "basic_foundation": {
        "male": (
            "Ngày 59 kiểm tra khoảng: 8–15 chống đẩy sàn, 2–6 kéo xà hoặc kéo người nằm, "
            "squat 20–35, plank 45–75 giây, đi/chạy 10 phút 1,1–1,5 km. "
            "Cơ ngực–lưng dày hơn, chuỗi sau cân bằng hơn."
        ),
        "female": (
            "Ngày 59 kiểm tra khoảng: 1–6 chống đẩy sàn (hoặc 6–12 kê bục 20 cm), "
            "4–8 kéo người nằm (hoặc 2–4 kéo xà dây), squat 18–28, plank 30–60 giây, "
            "đi/chạy 10 phút 0,9–1,3 km. Bạn thoát khỏi quỳ gối và bắt đầu kéo ngang/kéo xà."
        ),
    },
    "advanced_foundation": {
        "male": (
            "Ngày 59 kiểm tra khoảng: 12–25 chống đẩy sàn, 4–10 kéo xà hoặc kéo người nằm thấp, "
            "squat 25–45, plank 60–90 giây, đi bộ dốc/chạy 10 phút 1,3–1,8 km. "
            "Sức mạnh tương đối và tim mạch đủ để chuyển sang chơi thể thao."
        ),
        "female": (
            "Ngày 59 kiểm tra khoảng: 3–8 chống đẩy sàn, 1–2 kéo xà (hoặc 6 kéo người nằm/dây), "
            "squat 20–35, plank 45–90 giây, đi/chạy 10 phút 1,1–1,5 km. "
            "Hoàn thành 180 ngày nền tảng tại nhà."
        ),
    },
}

_PERIODIZATION: dict[str, str] = {
    "first_push_pull": (
        "Tuần 1–2 làm quen form (còn dư 3–4 cái). Tuần 3–4 kéo người nằm và chống đẩy quỳ. "
        "Tuần 5–7 tích lũy: Nam chống đẩy sàn + treo xà siết bả vai; Nữ quỳ/kê tay cao + treo xà. "
        "Ngày 57 giảm tải 50%, ngày 59 kiểm tra 5 hạng mục, ngày 60 nghỉ tốt nghiệp."
    ),
    "basic_foundation": (
        "Cả 8 tuần tăng khối lượng sát chuẩn cấp 2 (còn dư 2 cái): chống đẩy sàn hoặc ghế, "
        "kéo xà trợ lực hoặc kéo người nằm, lunge, đẩy hông, đi bộ/chạy nhịp vừa (nói chuyện được). "
        "Ngày 57 giảm tải, ngày 59 kiểm tra cấp 2, ngày 60 hồi phục."
    ),
    "advanced_foundation": (
        "Tuần 1–7 mật độ cao (còn dư 1–2 cái): sàn hoặc ghế thấp, kéo xà / kéo người nằm, "
        "lunge hoặc lunge chân sau kê ghế, giữ thân rỗng, đi bộ/chạy bền. Ngày 57 buổi tập nhẹ, ngày 59 kiểm tra "
        "tốt nghiệp cấp 3, ngày 60 nghỉ."
    ),
}


def normalize_familiarization_path(raw: Any) -> str:
    key = str(raw or "").strip().lower()
    return key if key in FAMILIARIZATION_PATHS else "basic_foundation"


def familiarization_overview_copy(path: str, gender: str) -> dict[str, str]:
    key = normalize_familiarization_path(path)
    sex = "female" if str(gender).strip().lower() == "female" else "male"
    meta = next((item for item in PATH_META if item["key"] == key), PATH_META[1])
    minutes = "50" if key == "advanced_foundation" else "45"
    goal = _OUTCOMES[key][sex]
    return {
        "label_vi": str(meta["label_vi"]),
        "summary_vi": (
            f"{meta['label_vi']} · 60 ngày · 3 buổi/tuần · khoảng {minutes} phút/buổi. {goal}"
        ),
        "mission_vi": _MISSION[key],
        "outcome_vi": goal,
        "periodization_vi": _PERIODIZATION[key],
        "nutrition_vi": NUTRITION_PRINCIPLES_VI,
        "schedule_vi": (
            f"60 ngày · 3 buổi/tuần · khoảng {minutes} phút/buổi · "
            "xen ngày nghỉ đi bộ nhẹ 15–20 phút"
        ),
    }


def familiarization_catalog() -> dict[str, Any]:
    return {
        "duration_weeks": 9,
        "duration_days": 60,
        "paths": [dict(item) for item in PATH_META],
        "standards": {
            gender: {
                level: [dict(row) for row in rows]
                for level, rows in levels.items()
            }
            for gender, levels in _STANDARD_ROWS.items()
        },
        "exit_goals": {
            gender: [dict(row) for row in rows]
            for gender, rows in _EXIT_GOALS.items()
        },
    }


def _number(raw: Any) -> float | None:
    if raw is None or raw == "":
        return None
    try:
        return max(0.0, float(raw))
    except (TypeError, ValueError):
        return None


def _baseline_dict(raw: Any) -> dict[str, Any]:
    if raw is None:
        return {}
    if hasattr(raw, "model_dump"):
        return dict(raw.model_dump())
    return dict(raw) if isinstance(raw, dict) else {}


def _push_pass(base: dict[str, Any], gender: str, level: str) -> bool | None:
    reps = _number(base.get("pushups_max"))
    if reps is None:
        return None
    variant = str(base.get("pushup_variant") or "standard").strip().lower()
    if gender == "male":
        if variant == "standard":
            return reps >= (12 if level == "advanced" else 8)
        if variant in {"incline_low", "incline_high", "knee"}:
            return level != "advanced" and reps >= 8
        return False
    if variant == "standard":
        return reps >= (3 if level == "advanced" else 1)
    if variant in {"incline_low", "incline_high"}:
        return level != "advanced" and reps >= 6
    return False


def _pull_pass(base: dict[str, Any], gender: str, level: str) -> bool | None:
    variant = str(base.get("pull_test_variant") or "strict").strip().lower()
    if variant == "hang":
        value = _number(base.get("pull_hold_seconds"))
        if value is None:
            return None
        return False
    if variant in {"inverted_row", "inverted_row_low"}:
        value = _number(base.get("inverted_rows_max"))
        if value is None:
            return None
        if gender != "female":
            if level == "advanced":
                return variant == "inverted_row_low" and value >= 6
            return value >= 6
        if level == "advanced":
            return variant == "inverted_row_low" and value >= 6
        return value >= 4
    value = _number(base.get("pullups_max"))
    if value is None:
        return None
    if gender == "female":
        return value >= 1
    return value >= (4 if level == "advanced" else 2)


def _simple_pass(value: Any, threshold: float, *, strict: bool = False) -> bool | None:
    number = _number(value)
    if number is None:
        return None
    return number > threshold if strict else number >= threshold


def _checks(base: dict[str, Any], gender: str, level: str) -> dict[str, bool | None]:
    female = gender == "female"
    advanced = level == "advanced"
    return {
        "push": _push_pass(base, gender, level),
        "pull": _pull_pass(base, gender, level),
        "squat": _simple_pass(
            base.get("squats_max"),
            20 if female and advanced else 18 if female else 25 if advanced else 20,
        ),
        "plank": _simple_pass(
            base.get("plank_seconds"),
            45 if female and advanced else 30 if female else 60 if advanced else 45,
        ),
        "run": _simple_pass(
            base.get("run_10min_meters"),
            1100 if female and advanced else 900 if female else 1300 if advanced else 1100,
        ),
    }


def evaluate_fitness_baseline(gender: Any, raw: Any) -> dict[str, Any]:
    normalized_gender = "female" if str(gender).strip().lower() == "female" else "male"
    base = _baseline_dict(raw)
    basic = _checks(base, normalized_gender, "basic")
    advanced = _checks(base, normalized_gender, "advanced")
    complete = all(value is not None for value in basic.values())
    if complete and all(value is True for value in advanced.values()):
        level = "advanced"
    elif complete and all(value is True for value in basic.values()):
        level = "basic"
    else:
        measured = [
            _number(base.get("pushups_max")),
            _number(base.get("pullups_max")),
            _number(base.get("pull_hold_seconds")),
            _number(base.get("inverted_rows_max")),
            _number(base.get("squats_max")),
            _number(base.get("plank_seconds")),
            _number(base.get("run_10min_meters")),
        ]
        level = (
            "zero"
            if measured and all((v or 0) == 0 for v in measured if v is not None)
            else "below_basic"
        )

    push = _number(base.get("pushups_max"))
    pull_values = (
        _number(base.get("pullups_max")),
        _number(base.get("pull_hold_seconds")),
        _number(base.get("inverted_rows_max")),
    )
    no_push_or_pull = (push or 0) == 0 or max((v or 0) for v in pull_values) == 0
    recommended = (
        "first_push_pull"
        if no_push_or_pull
        else "advanced_foundation"
        if level in {"basic", "advanced"}
        else "basic_foundation"
    )
    return {
        "gender": normalized_gender,
        "level": level,
        "complete": complete,
        "recommended_path": recommended,
        "basic": basic,
        "advanced": advanced,
        "missing_tests": [key for key, value in basic.items() if value is None],
        "basic_not_met": [key for key, value in basic.items() if value is not True],
        "advanced_not_met": [key for key, value in advanced.items() if value is not True],
    }
