"""Overview knowledge playbook for the 100-day challenge (mirrors frontend phaseKnowledge)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.services.exercise_prescription import clamp_experience_level

PhaseRef = dict[str, str]

_R: dict[str, PhaseRef] = {
    "readPlan": {
        "slug": "cach-doc-lich-tap-quy-uoc-buoi-tap",
        "label": "1.1 — Cách đọc lịch tập & Quy ước buổi tập",
    },
    "goals": {"slug": "xac-dinh-muc-tieu-tap-luyen", "label": "1.0 — Xác định mục tiêu tập luyện"},
    "muscles": {
        "slug": "ban-do-cac-nhom-co-chinh-co-che-chuyen-dong",
        "label": "1.2 — Bản đồ các nhóm cơ chính & Cơ chế chuyển động",
    },
    "calories": {
        "slug": "nang-luong-va-can-nang-tham-hut-thang-du-va-can-bang-calo",
        "label": "1.9 — Năng lượng và Cân nặng: Thâm hụt, Thặng dư và Cân bằng Calo",
    },
    "tdee": {
        "slug": "cach-tinh-tdee-theo-muc-van-dong-thuc-te",
        "label": "1.10 — Cách tính TDEE theo mức vận động thực tế",
    },
    "macros": {
        "slug": "dinh-duong-da-luong-chat-dam-protein-tinh-bot-carb-va-chat-beo-fat",
        "label": "1.11 — Dinh dưỡng đa lượng: Protein, Carb và Fat",
    },
    "warmup": {
        "slug": "khoi-dong-warm-up-van-dong-khop-mobility",
        "label": "1.3 — Khởi động (Warm-up) & Vận động khớp (Mobility)",
    },
    "form": {
        "slug": "ky-thuat-tap-chuan-form-an-toan-co-xuong-khop",
        "label": "1.4 — Kỹ thuật tập chuẩn (Form) & An toàn cơ xương khớp",
    },
    "vif": {
        "slug": "ba-nut-chinh-khoi-luong-volume-do-nang-intensity-tan-suat-frequency",
        "label": "1.5 — Ba nút chỉnh: Volume, Intensity, Frequency",
    },
    "recovery": {
        "slug": "phuc-hoi-co-bap-giac-ngu-va-toi-uu-phat-trien",
        "label": "1.12 — Phục hồi cơ bắp, Giấc ngủ và Tối ưu phát triển",
    },
    "overload": {
        "slug": "nguyen-tac-qua-tai-luy-tien-progressive-overload-co-ban",
        "label": "1.6 — Nguyên tắc Quá tải lũy tiến (Progressive Overload) cơ bản",
    },
    "beginnerDeload": {
        "slug": "tuan-xa-tai-nhe-deload-cho-nguoi-moi",
        "label": "1.8 — Tuần xả tải nhẹ (Deload) cho người mới",
    },
    "soreVsInjury": {
        "slug": "dau-moi-co-doms-va-chan-thuong-cach-phan-biet-va-xu-ly",
        "label": "1.7 — Đau mỏi cơ (DOMS) và Chấn thương",
    },
    "glossary": {
        "slug": "tu-dien-thuat-ngu-tap-luyen-cho-nguoi-moi",
        "label": "1.13 — Từ điển thuật ngữ tập luyện cho người mới",
    },
    "movementPatterns": {
        "slug": "mau-van-dong-va-cach-tang-giam-do-kho-bai-tap",
        "label": "1.14 — Mẫu vận động và cách tăng, giảm độ khó bài tập",
    },
    "cardio": {
        "slug": "cardio-cho-suc-khoe-va-giam-mo",
        "label": "1.15 — Cardio cho sức khỏe và giảm mỡ",
    },
    "painGuide": {
        "slug": "theo-doi-dau-va-dau-hieu-can-kham",
        "label": "1.16 — Theo dõi đau và dấu hiệu cần đi khám",
    },
    "hydration": {
        "slug": "nuoc-dien-giai-va-ruou-bia-khi-tap-luyen",
        "label": "1.17 — Nước, điện giải và rượu bia khi tập luyện",
    },
    "supplements": {
        "slug": "thuc-pham-bo-sung-theo-muc-do-bang-chung",
        "label": "1.18 — Thực phẩm bổ sung theo mức độ bằng chứng",
    },
    "overloadAdv": {
        "slug": "toi-uu-progressive-overload-nang-cao",
        "label": "2.0 — Tối ưu Progressive Overload nâng cao",
    },
    "rpe": {"slug": "rpe-va-rir-trong-tung-set", "label": "2.1 — RPE và RIR trong từng set"},
    "volumeMuscle": {
        "slug": "quan-ly-volume-theo-nhom-co",
        "label": "2.2 — Quản lý Volume theo nhóm cơ",
    },
    "deload": {"slug": "deload-dung-thoi-diem", "label": "2.3 — Deload đúng thời điểm"},
    "carbCycle": {"slug": "carb-cycling-co-ban", "label": "2.4 — Carb cycling cơ bản"},
    "refeed": {"slug": "refeed-va-diet-break", "label": "2.5 — Refeed và diet break"},
    "mmc": {
        "slug": "mind-muscle-connection-nang-cao",
        "label": "2.6 — Mind-Muscle Connection nâng cao",
    },
    "intensityTech": {
        "slug": "ky-thuat-drop-set-superset-rest-pause",
        "label": "2.7 — Kỹ thuật Drop set, Superset, Rest-pause",
    },
    "periodization": {"slug": "periodization-co-ban", "label": "2.8 — Periodization cơ bản"},
}

PHASE_KNOWLEDGE: dict[int, dict[int, tuple[str, ...]]] = {
    1: {
        1: ("readPlan", "glossary", "goals", "movementPatterns", "form", "warmup", "soreVsInjury", "painGuide"),
        2: ("calories", "tdee", "macros", "recovery", "hydration", "muscles", "cardio"),
        3: ("vif", "overload", "beginnerDeload", "supplements"),
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
    "glossary": "Hiểu set, rep, ROM, RIR/RPE trước khi tự đổi lịch.",
    "movementPatterns": "Chọn biến thể squat/hinge/push/pull phù hợp khả năng kiểm soát.",
    "cardio": "Bắt đầu cardio vừa sức; tăng thời lượng trước khi tăng cường độ.",
    "painGuide": "Đau nhói hoặc mất lực: dừng, đổi bài và theo dõi; có dấu hiệu đỏ thì đi khám.",
    "hydration": "Uống theo khát và điều kiện; chỉ thêm điện giải khi thực sự cần.",
    "supplements": "Không dùng supplement thay cho tập, ăn và ngủ; ưu tiên sản phẩm có bằng chứng.",
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
        want_overload="nguyen-tac-qua-tai-luy-tien-progressive-overload-co-ban" in has
        or "toi-uu-progressive-overload-nang-cao" in has,
        want_rep_ramp=month in (1, 2, 3),
        want_set_ramp="quan-ly-volume-theo-nhom-co" in has,
        want_carb_cycle="carb-cycling-co-ban" in has,
        want_refeed="refeed-va-diet-break" in has,
        want_intensity_tech="ky-thuat-drop-set-superset-rest-pause" in has,
        want_beginner_deload="tuan-xa-tai-nhe-deload-cho-nguoi-moi" in has,
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
