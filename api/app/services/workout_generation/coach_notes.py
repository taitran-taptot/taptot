"""One short Vietnamese coaching note per exercise — gym vs bodyweight."""

from __future__ import annotations

import re
from typing import Any, Literal

LOADED_NAME_KEYS = (
    "barbell",
    "dumbbell",
    "kettlebell",
    "machine",
    "cable",
    "tạ đòn",
    "ta don",
    "tạ đơn",
    "tạ ",
    "máy ",
    "cáp ",
)

BAND_NAME_KEYS = (
    "band",
    "resistance band",
    "dây kháng",
    "day khang",
    "dây thun",
    "day thun",
    "tube",
    "loop band",
)

LOAD_CUE_GYM_VI = "Làm hết mà vẫn dễ thì buổi sau tăng khoảng 2.5 kg."
LOAD_CUE_BW_VI = "Làm hết mà vẫn dễ thì buổi sau thêm 1–2 cái hoặc chọn kiểu khó hơn."
LOAD_CUE_BAND_VI = "Dễ quá thì dùng dây nặng hơn hoặc bước xa thêm."
FALLBACK_WORKING_NOTE_VI = "Làm số cái trên lịch rồi dừng, đừng làm đến lúc hết sức."
FOCUS_PHASE_TIP_VI = "Ưu tiên nhóm mục tiêu."
# Plan-level insight (gym or home).
LOAD_CUE_VI = (
    "Làm hết số cái trên lịch mà vẫn dễ thì buổi sau tăng nhẹ: "
    "có tạ thì khoảng 2.5 kg, không dụng cụ thì thêm 1–2 cái."
)
HOME_LOAD_INSIGHT_VI = (
    "Số cái đã tính theo thể lực; với tạ và dây hãy tự chọn mức tải phù hợp số rep trên lịch."
)
HOLD_NOTE_VI = "dừng trước khi lưng võng hoặc vai rũ."
CARDIO_NOTE_VI = (
    "Nhịp vừa phải, vẫn nói chuyện được. "
    "Mệt thì chậm lại hoặc nghỉ 30–60 giây rồi tiếp; chóng mặt / đau ngực thì dừng."
)
WARMUP_NOTE_VI = "Thở đều, đừng gồng hết sức."
COOLDOWN_NOTE_VI = "Giãn nhẹ, không ép đau. Nghỉ ngắn giữa hiệp."
PRIMER_NOTE_LOADED_VI = "Tạ nhẹ, 4 cái chậm."
PRIMER_NOTE_BW_VI = "Làm chậm số cái trên lịch, đừng đến hết sức."
PRIMER_TIMED_NOTE_VI = (
    "Giữ form, thời gian ngắn hơn bài chính — khởi động pattern, không tới thất bại."
)
RAMP_NOTE_VI = "Làm 2–4 hiệp khởi động, tăng tạ dần trước các hiệp chính."

LoadKind = Literal["loaded", "band", "bw"]


def _names(item: Any = None, *, name_vi: str | None = None, name_en: str | None = None) -> str:
    if item is not None:
        if isinstance(item, dict):
            name_vi = name_vi or item.get("name_vi")
            name_en = name_en or item.get("name_en")
        else:
            name_vi = name_vi or getattr(item, "name_vi", None)
            name_en = name_en or getattr(item, "name_en", None)
    return f"{name_vi or ''} {name_en or ''}".strip().lower()


def looks_band(
    item: Any = None,
    *,
    name_vi: str | None = None,
    name_en: str | None = None,
) -> bool:
    blob = _names(item, name_vi=name_vi, name_en=name_en)
    return any(key in blob for key in BAND_NAME_KEYS)


def looks_loaded(
    item: Any = None,
    *,
    name_vi: str | None = None,
    name_en: str | None = None,
    no_equipment: bool = False,
) -> bool:
    """True for free-weight / machine loads — not resistance bands."""
    if no_equipment:
        return False
    if looks_band(item, name_vi=name_vi, name_en=name_en):
        return False
    blob = _names(item, name_vi=name_vi, name_en=name_en)
    return any(key in blob for key in LOADED_NAME_KEYS)


def load_kind_for_item(
    item: Any = None,
    *,
    name_vi: str | None = None,
    name_en: str | None = None,
    no_equipment: bool = False,
) -> LoadKind:
    if looks_band(item, name_vi=name_vi, name_en=name_en):
        return "band"
    if looks_loaded(item, name_vi=name_vi, name_en=name_en, no_equipment=no_equipment):
        return "loaded"
    return "bw"


def _target_reps(reps: str | int | None) -> str:
    values = [int(x) for x in re.findall(r"\d+", str(reps or ""))]
    if not values:
        return "số cái trên lịch"
    lo, hi = values[0], values[-1]
    return f"{lo}–{hi}" if lo != hi else str(lo)


def _max_if_all_out(reps: str | int | None, rpe: int) -> int:
    values = [int(x) for x in re.findall(r"\d+", str(reps or ""))]
    hi = values[-1] if values else 8
    extra = 2 if int(rpe) >= 8 else 3
    return hi + extra


def working_note_vi(
    reps: str | int | None,
    *,
    loaded: bool = False,
    include_progress: bool = False,
    rpe: int = 7,
    kind: LoadKind | None = None,
) -> str:
    """Coaching cue for working sets.

    ``kind`` preferred when set; else ``loaded=True`` → free-weight cue.
    """
    resolved: LoadKind = kind or ("loaded" if loaded else "bw")
    target = _target_reps(reps)
    if resolved == "loaded":
        effort = (
            f"Chọn mức tạ để làm đúng {target} cái mỗi hiệp (còn dư khoảng 1–2 cái). "
            f"Hết mà vẫn dễ thì buổi sau tăng nhẹ tạ."
        )
        progress = LOAD_CUE_GYM_VI
        if include_progress:
            return f"{effort} {progress}"
        return effort
    if resolved == "band":
        effort = (
            f"Chọn độ căng dây / bước đứng để làm đúng {target} cái mỗi hiệp "
            f"(còn dư 1–2 cái)."
        )
        progress = LOAD_CUE_BAND_VI
        if include_progress:
            return f"{effort} {progress}"
        return effort
    effort = f"Làm {target} cái rồi dừng, đừng làm đến lúc hết sức."
    progress = LOAD_CUE_BW_VI
    if include_progress:
        return f"{effort} {progress}"
    return effort


def hold_note_vi(reps: str | int | None, *, include_progress: bool = False) -> str:
    values = [int(x) for x in re.findall(r"\d+", str(reps or ""))]
    seconds = values[0] if values else 20
    effort = f"Giữ {seconds} giây, {HOLD_NOTE_VI}"
    if include_progress:
        return f"{effort} Giữ hết giờ mà vẫn dễ thì buổi sau thêm 5 giây."
    return effort


def beginner_effort_cue(rpe: int, reps: str | int, *, loaded: bool = True) -> str:
    """Backward-compatible alias used by fill / older callers."""
    return working_note_vi(reps, loaded=loaded, include_progress=False, rpe=rpe)
