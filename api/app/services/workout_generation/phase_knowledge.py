"""Overview knowledge playbook for the 100-day challenge (mirrors frontend phaseKnowledge)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.services.exercise_prescription import clamp_experience_level

PhaseRef = dict[str, str]

_R: dict[str, PhaseRef] = {
    "readPlan": {"slug": "cach-doc-lich-tap", "label": "Cách đọc lịch tập"},
    "goals": {"slug": "10-xc-nh-mc-tiu-tp-luyn", "label": "1.0 — Xác định mục tiêu tập luyện"},
    "muscles": {"slug": "11-hiu-cc-nhm-c-chnh", "label": "1.1 — Hiểu các nhóm cơ chính"},
    "calories": {
        "slug": "12-calories-thng-d-thm-ht-cn-bng",
        "label": "1.2 — Calories: thặng dư, thâm hụt, cân bằng",
    },
    "tdee": {"slug": "13-tnh-tdee-theo-mc-vn-ng", "label": "1.3 — Tính TDEE theo mức vận động"},
    "macros": {
        "slug": "14-macronutrients-protein-carb-fat",
        "label": "1.4 — Macronutrients: Protein, Carb, Fat",
    },
    "warmup": {"slug": "15-warm-up-v-mobility", "label": "1.5 — Warm-up và Mobility"},
    "form": {"slug": "16-k-thut-tp-chun-form", "label": "1.6 — Kỹ thuật tập chuẩn (Form)"},
    "vif": {
        "slug": "17-volume-intensity-frequency",
        "label": "1.7 — Volume, Intensity, Frequency",
    },
    "recovery": {"slug": "18-phc-hi-v-gic-ng", "label": "1.8 — Phục hồi và giấc ngủ"},
    "overload": {
        "slug": "19-progressive-overload-c-bn",
        "label": "1.9 — Progressive Overload cơ bản",
    },
    "beginnerDeload": {"slug": "tuan-nhe-cho-nguoi-moi", "label": "Tuần nhẹ cho người mới"},
    "soreVsInjury": {"slug": "dau-nhuc-va-chan-thuong", "label": "Đau nhức và chấn thương"},
    "overloadAdv": {
        "slug": "20-ti-u-progressive-overload-nng-cao",
        "label": "2.0 — Tối ưu Progressive Overload nâng cao",
    },
    "rpe": {"slug": "21-rpe-v-rir-trong-tng-set", "label": "2.1 — RPE và RIR trong từng set"},
    "volumeMuscle": {
        "slug": "22-qun-l-volume-theo-nhm-c",
        "label": "2.2 — Quản lý Volume theo nhóm cơ",
    },
    "deload": {"slug": "23-deload-ng-thi-im", "label": "2.3 — Deload đúng thời điểm"},
    "carbCycle": {"slug": "24-carb-cycling-c-bn", "label": "2.4 — Carb cycling cơ bản"},
    "refeed": {"slug": "25-refeed-v-diet-break", "label": "2.5 — Refeed và diet break"},
    "mmc": {
        "slug": "26-mind-muscle-connection-nng-cao",
        "label": "2.6 — Mind-Muscle Connection nâng cao",
    },
    "intensityTech": {
        "slug": "27-k-thut-drop-set-superset-rest-pause",
        "label": "2.7 — Kỹ thuật Drop set, Superset, Rest-pause",
    },
    "periodization": {"slug": "28-periodization-c-bn", "label": "2.8 — Periodization cơ bản"},
}

PHASE_KNOWLEDGE: dict[int, dict[int, tuple[str, ...]]] = {
    1: {
        1: ("readPlan", "goals", "form", "warmup", "calories", "soreVsInjury"),
        2: ("tdee", "macros", "recovery", "muscles"),
        3: ("vif", "overload", "beginnerDeload"),
    },
    2: {
        1: ("tdee", "recovery", "vif", "form"),
        2: ("overload", "rpe", "deload"),
        3: ("volumeMuscle", "periodization", "carbCycle"),
    },
    3: {
        1: ("periodization", "volumeMuscle", "rpe"),
        2: ("overloadAdv", "carbCycle", "intensityTech"),
        3: ("deload", "refeed", "mmc"),
    },
}

_BRIEFS: dict[str, str] = {
    "readPlan": "Đọc số hiệp/cái/nghỉ trên lịch; không tự thêm bài ngoài pool.",
    "goals": "Bám mục tiêu user (giảm/giữ/tăng) khi chọn volume và ăn.",
    "muscles": "Mỗi buổi phủ đúng nhóm split; không nhồi hai compound cùng pattern.",
    "calories": "Ngày tập ăn theo target ngày tập; không cắt sâu hơn lịch.",
    "tdee": "Calo trung bình bám TDEE ± mục tiêu; không bịa kcal.",
    "macros": "Neo đạm; tinh bột và béo theo target — L1 giữ macro ổn định.",
    "warmup": "Giữ warmup/mobility trong slot; không biến thành HIIT.",
    "form": "Ưu tiên form: RPE vừa, không tăng hiệp pha 1 người mới.",
    "vif": "Tăng cái trong band test trước khi tăng hiệp; tần suất giữ nguyên.",
    "recovery": "Nghỉ giữa hiệp đủ; tuần nhẹ không cắt ngủ/ăn.",
    "overload": "Tuần chẵn trong pha: +1 cái trong working band nếu còn form.",
    "beginnerDeload": "Tuần 4/8/14 giảm tải, vẫn đi buổi; không cắt calo sâu hơn.",
    "soreVsInjury": "Đau nhói khớp thì dừng bài đó; mỏi âm ì là bình thường.",
    "overloadAdv": "Tăng tải có chủ đích; isolation có thể rest-pause nếu pool còn.",
    "rpe": "Working sets còn 1–3 cái (RIR); deload thì dễ hơn.",
    "volumeMuscle": "Nhóm ưu tiên +1 hiệp compound nếu chưa chạm trần buổi.",
    "deload": "Tuần deload giảm ~1/3 tải; giữ bài, không đổi sang nặng hơn.",
    "carbCycle": "Ngày tập tinh bột cao hơn, ngày nghỉ thấp hơn; đạm gần như cố.",
    "refeed": "Giảm cân: 1 ngày/tuần ~TDEE, tinh bột cao hơn (không đổi kho món).",
    "mmc": "Isolation chậm, siết nhóm mục tiêu; không thêm drop-set nếu user mới.",
    "intensityTech": "Chỉ isolation: được rest-pause/drop-set nếu pool còn và L3 pha 2.",
    "periodization": "3 pha 4+4+6 tuần; bài và liều đổi theo pha, deload cuối pha.",
}


@dataclass(frozen=True)
class PhaseFlags:
    want_overload: bool
    want_rep_ramp: bool
    want_set_ramp: bool
    want_carb_cycle: bool
    want_refeed: bool
    want_intensity_tech: bool
    want_beginner_deload: bool
    slugs: tuple[str, ...]
    labels: tuple[str, ...]


def refs_for_phase(level: int | None, month: int | None) -> list[PhaseRef]:
    exp = max(1, min(3, int(clamp_experience_level(level))))
    if month not in (1, 2, 3):
        return []
    keys = PHASE_KNOWLEDGE[exp][int(month)]
    return [_R[k] for k in keys]


def flags_for_phase(level: int | None, month: int | None) -> PhaseFlags:
    refs = refs_for_phase(level, month)
    slugs = tuple(r["slug"] for r in refs)
    labels = tuple(r["label"] for r in refs)
    has = set(slugs)
    return PhaseFlags(
        want_overload="19-progressive-overload-c-bn" in has
        or "20-ti-u-progressive-overload-nng-cao" in has,
        want_rep_ramp=month in (1, 2, 3),
        want_set_ramp="22-qun-l-volume-theo-nhm-c" in has,
        want_carb_cycle="24-carb-cycling-c-bn" in has,
        want_refeed="25-refeed-v-diet-break" in has,
        want_intensity_tech="27-k-thut-drop-set-superset-rest-pause" in has,
        want_beginner_deload="tuan-nhe-cho-nguoi-moi" in has,
        slugs=slugs,
        labels=labels,
    )


def briefs_for_phase(
    level: int | None,
    month: int | None,
    *,
    goal: str | None = None,
) -> list[str]:
    exp = max(1, min(3, int(clamp_experience_level(level))))
    if month not in (1, 2, 3):
        return []
    goal_n = str(goal or "").strip().lower()
    out: list[str] = []
    for key in PHASE_KNOWLEDGE[exp][int(month)]:
        ref = _R[key]
        brief = _BRIEFS[key]
        if key == "carbCycle" and goal_n in {"gain_weight", "gain_muscle"}:
            brief = "Cycle nhẹ: ngày tập tinh bột hơi cao, ngày nghỉ không cắt sâu."
        if key == "refeed" and goal_n != "lose_weight":
            brief = "Không refeed (không phải pha cắt). Giữ macro block."
        out.append(f"{ref['label']}: {brief}")
    return out


def playbook_vi(
    level: int | None,
    month: int | None,
    *,
    goal: str | None = None,
) -> str:
    lines = briefs_for_phase(level, month, goal=goal)
    return " ".join(lines)


def playbook_all_phases_vi(level: int | None, *, goal: str | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for month in (1, 2, 3):
        flags = flags_for_phase(level, month)
        out[str(month)] = {
            "labels": list(flags.labels),
            "briefs": briefs_for_phase(level, month, goal=goal),
            "want_carb_cycle": flags.want_carb_cycle,
            "want_refeed": flags.want_refeed and str(goal or "").strip().lower() == "lose_weight",
        }
    return out
