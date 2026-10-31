"""Overview knowledge playbook for the 100-day challenge (mirrors frontend phaseKnowledge)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.services.exercise_prescription import clamp_experience_level

PhaseRef = dict[str, str]

_R: dict[str, PhaseRef] = {
    "readPlan": {
        "slug": "cach-doc-lich-tap-quy-uoc-buoi-tap",
        "label": "1.9 — Cách đọc lịch tập & Quy ước buổi tập",
    },
    "goals": {"slug": "xac-dinh-muc-tieu-tap-luyen", "label": "1.0 — Xác định mục tiêu tập luyện"},
    "muscles": {
        "slug": "ban-do-cac-nhom-co-chinh-co-che-chuyen-dong",
        "label": "1.1 — Bản đồ các nhóm cơ chính & Cơ chế chuyển động",
    },
    "calories": {
        "slug": "nang-luong-va-can-nang-tham-hut-thang-du-va-can-bang-calo",
        "label": "1.17 — Năng lượng và Cân nặng: Thâm hụt, Thặng dư và Cân bằng Calo",
    },
    "tdee": {
        "slug": "cach-tinh-tdee-theo-muc-van-dong-thuc-te",
        "label": "1.18 — Cách tính TDEE theo mức vận động thực tế",
    },
    "macros": {
        "slug": "dinh-duong-da-luong-chat-dam-protein-tinh-bot-carb-va-chat-beo-fat",
        "label": "1.19 — Dinh dưỡng đa lượng: Chất đạm (Protein), Tinh bột (Carb) và Chất béo (Fat)",
    },
    "warmup": {
        "slug": "khoi-dong-warm-up-van-dong-khop-mobility",
        "label": "1.5 — Khởi động (Warm-up) & Vận động khớp (Mobility)",
    },
    "form": {
        "slug": "ky-thuat-tap-chuan-form-an-toan-co-xuong-khop",
        "label": "1.7 — Kỹ thuật tập chuẩn (Form) & An toàn cơ xương khớp",
    },
    "vif": {
        "slug": "ba-nut-chinh-khoi-luong-volume-do-nang-intensity-tan-suat-frequency",
        "label": "1.10 — Ba nút chỉnh: Khối lượng (Volume), Độ nặng (Intensity), Tần suất (Frequency)",
    },
    "recovery": {
        "slug": "phuc-hoi-co-bap-giac-ngu-va-toi-uu-phat-trien",
        "label": "1.14 — Phục hồi cơ bắp, Giấc ngủ và Tối ưu phát triển",
    },
    "overload": {
        "slug": "nguyen-tac-qua-tai-luy-tien-progressive-overload-co-ban",
        "label": "1.11 — Nguyên tắc Quá tải lũy tiến (Progressive Overload) cơ bản",
    },
    "beginnerDeload": {
        "slug": "tuan-xa-tai-nhe-deload-cho-nguoi-moi",
        "label": "1.15 — Tuần xả tải nhẹ (Deload) cho người mới",
    },
    "soreVsInjury": {
        "slug": "dau-moi-co-doms-va-chan-thuong-cach-phan-biet-va-xu-ly",
        "label": "1.13 — Đau mỏi cơ (DOMS) và Chấn thương: Cách phân biệt và xử lý",
    },
    "glossary": {
        "slug": "tu-dien-thuat-ngu-tap-luyen-cho-nguoi-moi",
        "label": "1.2 — Từ điển thuật ngữ tập luyện cho người mới",
    },
    "movementPatterns": {
        "slug": "mau-van-dong-va-cach-tang-giam-do-kho-bai-tap",
        "label": "1.3 — Mẫu vận động và cách tăng, giảm độ khó bài tập",
    },
    "cardio": {
        "slug": "cardio-cho-suc-khoe-va-giam-mo",
        "label": "1.22 — Cardio cho sức khỏe và giảm mỡ",
    },
    "painGuide": {
        "slug": "theo-doi-dau-va-dau-hieu-can-kham",
        "label": "1.8 — Theo dõi đau và dấu hiệu cần đi khám",
    },
    "hydration": {
        "slug": "nuoc-dien-giai-va-ruou-bia-khi-tap-luyen",
        "label": "1.21 — Nước, điện giải và rượu bia khi tập luyện",
    },
    "supplements": {
        "slug": "thuc-pham-bo-sung-theo-muc-do-bang-chung",
        "label": "1.23 — Thực phẩm bổ sung theo mức độ bằng chứng",
    },
    "overloadAdv": {
        "slug": "toi-uu-progressive-overload-nang-cao",
        "label": "1.24 — Tối ưu Quá tải lũy tiến (Progressive Overload)",
    },
    "rpe": {"slug": "rpe-va-rir-trong-tung-set", "label": "1.25 — RPE và RIR: Nghệ thuật đo lường nỗ lực trong từng hiệp tập"},
    "volumeMuscle": {
        "slug": "quan-ly-volume-theo-nhom-co",
        "label": "1.26 — Quản lý Khối lượng tập luyện (Volume) theo từng nhóm cơ",
    },
    "deload": {"slug": "deload-dung-thoi-diem", "label": "1.27 — Deload đúng thời điểm: Khoa học xả tải để bứt phá thể lực"},
    "carbCycle": {"slug": "carb-cycling-co-ban", "label": "1.31 — Carb Cycling: Phân bổ carbohydrate theo ngày tập và ngày nghỉ"},
    "refeed": {"slug": "refeed-va-diet-break", "label": "1.32 — Refeed và Diet Break: Công cụ hỗ trợ khi siết mỡ"},
    "mmc": {
        "slug": "mind-muscle-connection-nang-cao",
        "label": "1.29 — Kết nối Não – Cơ (Mind-Muscle Connection) và Kỹ thuật điều khiển nhịp độ",
    },
    "intensityTech": {
        "slug": "ky-thuat-drop-set-superset-rest-pause",
        "label": "1.30 — Kỹ thuật Cường độ cao: Drop Set, Superset và Rest-Pause",
    },
    "periodization": {"slug": "periodization-co-ban", "label": "1.28 — Chu kỳ hóa tập luyện cơ bản (Periodization)"},
    "brace": {
        "slug": "hit-tho-bracing-va-kiem-soat-ap-luc-khi-tap",
        "label": "1.6 — Hít thở, Brace và kiểm soát thân mình khi tập",
    },
    "homeGear": {
        "slug": "tap-tai-nha-chon-va-su-dung-dung-cu-an-toan",
        "label": "1.4 — Tập tại nhà: Chọn và sử dụng dụng cụ an toàn",
    },
    "journal": {
        "slug": "theo-doi-tien-bo-va-nhat-ky-tap-luyen",
        "label": "1.12 — Theo dõi tiến bộ và sử dụng nhật ký tập luyện",
    },
    "portions": {
        "slug": "uoc-luong-khau-phan-va-an-uong-thuc-te",
        "label": "1.20 — Ước lượng khẩu phần và áp dụng dinh dưỡng vào đời sống",
    },
    "mistakes": {
        "slug": "nhung-sai-lam-pho-bien-khi-moi-tap",
        "label": "1.16 — Những sai lầm phổ biến khi mới bắt đầu tập luyện",
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
    "brace": "Giữ hơi và siết thân khi squat, hinge, đẩy, kéo; không nín thở đến chóng mặt.",
    "homeGear": "Chọn biến thể vừa dụng cụ tại nhà; không đuổi mức tạ của phòng gym.",
    "journal": "Ghi hiệp và cái để biết tuần sau tăng hay giữ.",
    "portions": "Ước lượng khẩu phần bằng tay; không cần cân từng bữa.",
    "mistakes": "Giữ các bài chính đủ lâu; không đổi lịch sau một tuần.",
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


def _goal_bucket(goal: str | None) -> str:
    g = str(goal or "").strip().lower()
    if g in {"gain_weight", "gain_muscle"}:
        return "gain"
    if g == "lose_weight":
        return "lose"
    return "maintain"


def _activity_bucket(activity: str | None) -> str:
    a = str(activity or "").strip().lower()
    if a in {"sedentary", "light", "moderate", "active", "very_active"}:
        return a
    return "moderate"


def _is_labor(activity: str) -> bool:
    return activity in {"active", "very_active"}


def _is_home(location: str | None) -> bool:
    return str(location or "").strip().lower() in {"home", "tai_nha", "at_home"}


def _nutrition_key(bucket: str) -> str:
    if bucket == "lose":
        return "calories"
    if bucket == "gain":
        return "macros"
    return "tdee"


def _keys_for_phase(
    level: int,
    month: int,
    *,
    goal: str | None = None,
    activity: str | None = None,
    location: str | None = None,
) -> list[str]:
    """Four articles for one phase, in the order to read that month."""
    bucket = _goal_bucket(goal)
    job = _activity_bucket(activity)
    home = _is_home(location)
    labor = _is_labor(job)
    if level == 1 and month == 1:
        return ["readPlan", "form", "painGuide" if labor else "warmup", "homeGear" if home else "brace"]
    if level == 1 and month == 2:
        return ["movementPatterns", "soreVsInjury", "glossary" if labor else "painGuide", _nutrition_key(bucket)]
    if level == 1 and month == 3:
        return ["overload", "beginnerDeload", "journal", "cardio" if bucket == "lose" else "mistakes"]
    if level == 2 and month == 1:
        fourth = "warmup" if job == "sedentary" else "painGuide" if labor else "form"
        return ["readPlan", "vif", "recovery", fourth]
    if level == 2 and month == 2:
        return ["overload", "rpe", "soreVsInjury", _nutrition_key(bucket)]
    if level == 2 and month == 3:
        return ["volumeMuscle", "periodization", "journal", "carbCycle" if bucket == "lose" else "portions"]
    if level == 3 and month == 1:
        return ["readPlan", "periodization", "volumeMuscle", "rpe"]
    if level == 3 and month == 2:
        fourth = "carbCycle" if bucket == "lose" else "macros" if bucket == "gain" else "recovery"
        return ["overloadAdv", "intensityTech", "mmc", fourth]
    fourth = "refeed" if bucket == "lose" else "portions"
    return ["deload", "journal", "supplements", fourth]


def refs_for_phase(
    level: int | None,
    month: int | None,
    *,
    goal: str | None = None,
    activity: str | None = None,
    location: str | None = None,
) -> list[PhaseRef]:
    exp = max(1, min(3, int(clamp_experience_level(level))))
    if month not in (1, 2, 3):
        return []
    keys = _keys_for_phase(exp, int(month), goal=goal, activity=activity, location=location)
    return [_R[k] for k in keys]


def refs_for_challenge_phases_ui(
    level: int | None,
    *,
    goal: str | None = None,
    activity: str | None = None,
    location: str | None = None,
) -> list[list[PhaseRef]]:
    """Four learner articles per phase, in reading order for that month."""
    return [
        refs_for_phase(level, month, goal=goal, activity=activity, location=location)
        for month in (1, 2, 3)
    ]


def refs_for_phase_ui(
    level: int | None,
    month: int | None,
    *,
    goal: str | None = None,
    activity: str | None = None,
    location: str | None = None,
) -> list[PhaseRef]:
    """Single-phase view; challenge overview should use refs_for_challenge_phases_ui."""
    return refs_for_phase(level, month, goal=goal, activity=activity, location=location)


def flags_for_phase(
    level: int | None,
    month: int | None,
    *,
    goal: str | None = None,
    activity: str | None = None,
    location: str | None = None,
) -> PhaseFlags:
    refs = refs_for_phase(level, month, goal=goal, activity=activity, location=location)
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
    for key in _keys_for_phase(exp, int(month), goal=goal):
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
        flags = flags_for_phase(level, month, goal=goal)
        out[str(month)] = {
            "labels": list(flags.labels),
            "briefs": briefs_for_phase(level, month, goal=goal),
            "want_carb_cycle": flags.want_carb_cycle,
            "want_refeed": flags.want_refeed and str(goal or "").strip().lower() == "lose_weight",
        }
    return out
