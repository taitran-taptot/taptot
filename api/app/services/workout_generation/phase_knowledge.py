"""Overview knowledge playbook for the 100-day challenge (mirrors frontend phaseKnowledge)."""

from __future__ import annotations

from dataclasses import dataclass

from app.services.exercise_prescription import clamp_experience_level

PhaseRef = dict[str, str]

_R: dict[str, PhaseRef] = {
    "readPlan": {
        "slug": "cach-doc-lich-tap-quy-uoc-buoi-tap",
        "label": "Cách đọc lịch tập & Quy ước buổi tập",
    },
    "goals": {"slug": "xac-dinh-muc-tieu-tap-luyen", "label": "Xác định mục tiêu tập luyện"},
    "muscles": {
        "slug": "ban-do-cac-nhom-co-chinh-co-che-chuyen-dong",
        "label": "Bản đồ các nhóm cơ chính & Cơ chế chuyển động",
    },
    "calories": {
        "slug": "nang-luong-va-can-nang-tham-hut-thang-du-va-can-bang-calo",
        "label": "Năng lượng và Cân nặng: Thâm hụt, Thặng dư và Cân bằng Calo",
    },
    "tdee": {
        "slug": "cach-tinh-tdee-theo-muc-van-dong-thuc-te",
        "label": "Cách tính TDEE theo mức vận động thực tế",
    },
    "macros": {
        "slug": "dinh-duong-da-luong-chat-dam-protein-tinh-bot-carb-va-chat-beo-fat",
        "label": "Dinh dưỡng đa lượng: Chất đạm (Protein), Tinh bột (Carb) và Chất béo (Fat)",
    },
    "warmup": {
        "slug": "khoi-dong-warm-up-van-dong-khop-mobility",
        "label": "Khởi động (Warm-up) & Vận động khớp (Mobility)",
    },
    "form": {
        "slug": "ky-thuat-tap-chuan-form-an-toan-co-xuong-khop",
        "label": "Kỹ thuật tập chuẩn (Form) & An toàn cơ xương khớp",
    },
    "vif": {
        "slug": "ba-nut-chinh-khoi-luong-volume-do-nang-intensity-tan-suat-frequency",
        "label": "Ba nút chỉnh: Khối lượng (Volume), Độ nặng (Intensity), Tần suất (Frequency)",
    },
    "recovery": {
        "slug": "phuc-hoi-co-bap-giac-ngu-va-toi-uu-phat-trien",
        "label": "Phục hồi cơ bắp, Giấc ngủ và Tối ưu phát triển",
    },
    "overload": {
        "slug": "nguyen-tac-qua-tai-luy-tien-progressive-overload-co-ban",
        "label": "Nguyên tắc Quá tải lũy tiến (Progressive Overload) cơ bản",
    },
    "beginnerDeload": {
        "slug": "tuan-xa-tai-nhe-deload-cho-nguoi-moi",
        "label": "Tuần xả tải nhẹ (Deload) cho người mới",
    },
    "soreVsInjury": {
        "slug": "dau-moi-co-doms-va-chan-thuong-cach-phan-biet-va-xu-ly",
        "label": "Đau mỏi cơ (DOMS) và Chấn thương: Cách phân biệt và xử lý",
    },
    "glossary": {
        "slug": "tu-dien-thuat-ngu-tap-luyen-cho-nguoi-moi",
        "label": "Từ điển thuật ngữ tập luyện cho người mới",
    },
    "movementPatterns": {
        "slug": "mau-van-dong-va-cach-tang-giam-do-kho-bai-tap",
        "label": "Mẫu vận động và cách tăng, giảm độ khó bài tập",
    },
    "cardio": {
        "slug": "cardio-cho-suc-khoe-va-giam-mo",
        "label": "Cardio cho sức khỏe và giảm mỡ",
    },
    "painGuide": {
        "slug": "theo-doi-dau-va-dau-hieu-can-kham",
        "label": "Theo dõi đau và dấu hiệu cần đi khám",
    },
    "hydration": {
        "slug": "nuoc-dien-giai-va-ruou-bia-khi-tap-luyen",
        "label": "Nước, điện giải và rượu bia khi tập luyện",
    },
    "supplements": {
        "slug": "thuc-pham-bo-sung-theo-muc-do-bang-chung",
        "label": "Thực phẩm bổ sung theo mức độ bằng chứng",
    },
    "overloadAdv": {
        "slug": "toi-uu-progressive-overload-nang-cao",
        "label": "Tối ưu Quá tải lũy tiến (Progressive Overload)",
    },
    "rpe": {"slug": "rpe-va-rir-trong-tung-set", "label": "RPE và RIR: Nghệ thuật đo lường nỗ lực trong từng hiệp tập"},
    "volumeMuscle": {
        "slug": "quan-ly-volume-theo-nhom-co",
        "label": "Quản lý Khối lượng tập luyện (Volume) theo từng nhóm cơ",
    },
    "deload": {"slug": "deload-dung-thoi-diem", "label": "Deload đúng thời điểm: Khoa học xả tải để bứt phá thể lực"},
    "carbCycle": {"slug": "carb-cycling-co-ban", "label": "Carb Cycling: Phân bổ carbohydrate theo ngày tập và ngày nghỉ"},
    "refeed": {"slug": "refeed-va-diet-break", "label": "Refeed và Diet Break: Công cụ hỗ trợ khi siết mỡ"},
    "mmc": {
        "slug": "mind-muscle-connection-nang-cao",
        "label": "Kết nối Não – Cơ (Mind-Muscle Connection) và Kỹ thuật điều khiển nhịp độ",
    },
    "intensityTech": {
        "slug": "ky-thuat-drop-set-superset-rest-pause",
        "label": "Kỹ thuật Cường độ cao: Drop Set, Superset và Rest-Pause",
    },
    "periodization": {"slug": "periodization-co-ban", "label": "Chu kỳ hóa tập luyện cơ bản (Periodization)"},
    "brace": {
        "slug": "hit-tho-bracing-va-kiem-soat-ap-luc-khi-tap",
        "label": "Hít thở, Brace và kiểm soát thân mình khi tập",
    },
    "homeGear": {
        "slug": "tap-tai-nha-chon-va-su-dung-dung-cu-an-toan",
        "label": "Tập tại nhà: Chọn và sử dụng dụng cụ an toàn",
    },
    "journal": {
        "slug": "theo-doi-tien-bo-va-nhat-ky-tap-luyen",
        "label": "Theo dõi tiến bộ và sử dụng nhật ký tập luyện",
    },
    "portions": {
        "slug": "uoc-luong-khau-phan-va-an-uong-thuc-te",
        "label": "Ước lượng khẩu phần và áp dụng dinh dưỡng vào đời sống",
    },
    "mistakes": {
        "slug": "nhung-sai-lam-pho-bien-khi-moi-tap",
        "label": "Những sai lầm phổ biến khi mới bắt đầu tập luyện",
    },
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


def _job_group(activity: str | None) -> str:
    """sit = sedentary, walk = light/moderate, heavy = active/very_active."""
    job = _activity_bucket(activity)
    if job == "sedentary":
        return "sit"
    if job in {"active", "very_active"}:
        return "heavy"
    return "walk"


def _nutrition_key(bucket: str) -> str:
    if bucket == "lose":
        return "calories"
    if bucket == "gain":
        return "macros"
    return "tdee"


def _phase_one_nutrition(level: int, job: str, bucket: str) -> str:
    """Phase 3 keeps the named macro/TDEE article for walkers, so phase 1 takes the other one."""
    if level in {2, 3} and job == "walk" and bucket == "gain":
        return "tdee"
    if level in {2, 3} and job == "walk" and bucket == "maintain":
        return "calories"
    return _nutrition_key(bucket)


def _phase_one(level: int, job: str, bucket: str) -> list[str]:
    nutrition = _phase_one_nutrition(level, job, bucket)
    if level == 1:
        if job == "sit":
            return ["readPlan", "warmup", "form", nutrition]
        if job == "heavy":
            return ["readPlan", "painGuide", "brace", nutrition]
        return ["readPlan", "form", "homeGear", nutrition]
    if level == 2:
        third = {"sit": "warmup", "walk": "form", "heavy": "painGuide"}[job]
        return ["readPlan", "vif", third, nutrition]
    third = {"sit": "rpe", "walk": "volumeMuscle", "heavy": "painGuide"}[job]
    return ["readPlan", "periodization", third, nutrition]


def _phase_two(level: int, job: str, bucket: str) -> list[str]:
    if level == 1:
        # Form and the pain guide are already in phase 1 for these jobs.
        if job == "sit":
            return ["movementPatterns", "soreVsInjury", "glossary", "portions"]
        if job == "heavy":
            return ["movementPatterns", "glossary", "recovery", "portions"]
        return ["movementPatterns", "soreVsInjury", "glossary", "portions"]
    if level == 2:
        if job == "sit":
            # Warmup is already in phase 1. Portions stays in phase 3 for gain/maintain.
            fourth = "portions" if bucket == "lose" else "soreVsInjury"
            return ["overload", "rpe", "form", fourth]
        if job == "heavy":
            # Pain guide is in phase 1; recovery is in phase 3.
            return ["overload", "form", "soreVsInjury", "portions"]
        return ["overload", "rpe", "soreVsInjury", "portions"]
    if job == "sit":
        fourth = "portions" if bucket == "lose" else "hydration"
        return ["overloadAdv", "mmc", "intensityTech", fourth]
    if job == "heavy":
        # Pain guide is in phase 1; recovery is in phase 3.
        return ["overloadAdv", "mmc", "soreVsInjury", "portions"]
    fourth = "portions" if bucket == "lose" else "hydration"
    return ["overloadAdv", "mmc", "rpe", fourth]


def _phase_three(level: int, job: str, bucket: str) -> list[str]:
    if level == 1:
        if bucket == "lose":
            fourth = "hydration" if job == "heavy" else "cardio"
        else:
            # Portions is already the phase-2 nutrition article.
            fourth = "mistakes"
        return ["overload", "beginnerDeload", "journal", fourth]
    if level == 2:
        if job == "heavy":
            if bucket == "lose":
                fourth = "hydration"
            elif bucket == "gain":
                fourth = "tdee"
            else:
                fourth = "calories"
            return ["volumeMuscle", "recovery", "journal", fourth]
        if bucket == "lose":
            fourth = "carbCycle" if job == "sit" else "cardio"
        elif job == "walk":
            fourth = "macros" if bucket == "gain" else "tdee"
        else:
            fourth = "portions"
        return ["volumeMuscle", "periodization", "journal", fourth]
    if job == "sit":
        if bucket == "lose":
            return ["deload", "journal", "carbCycle", "refeed"]
        return ["deload", "journal", "portions", "supplements"]
    if job == "walk":
        # Volume is already in phase 1, so phase 3 uses the journal instead.
        if bucket == "lose":
            return ["deload", "journal", "carbCycle", "refeed"]
        if bucket == "gain":
            return ["deload", "journal", "portions", "macros"]
        return ["deload", "journal", "portions", "tdee"]
    if bucket == "lose":
        return ["deload", "recovery", "hydration", "refeed"]
    return ["deload", "recovery", "hydration", "supplements"]


def _keys_for_phase(
    level: int,
    month: int,
    *,
    goal: str | None = None,
    activity: str | None = None,
    location: str | None = None,
) -> list[str]:
    """Four articles for one phase, in the order to read that month.

    Location does not change the list. Home gear is the level-1 walking phase-1 article.
    """
    del location
    bucket = _goal_bucket(goal)
    job = _job_group(activity)
    phases = (
        _phase_one(level, job, bucket),
        _phase_two(level, job, bucket),
        _phase_three(level, job, bucket),
    )
    return list(phases[month - 1])


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
    exp = max(1, min(3, int(clamp_experience_level(level))))
    month_n = int(month) if month in (1, 2, 3) else 0
    lose = _goal_bucket(goal) == "lose"
    return PhaseFlags(
        want_overload=(exp == 1 and month_n == 3)
        or (exp == 2 and month_n == 2)
        or (exp == 3 and month_n == 2),
        want_rep_ramp=month_n in (1, 2, 3),
        want_set_ramp=(exp == 2 and month_n == 3) or (exp == 3 and month_n == 1),
        want_carb_cycle=lose and ((exp == 2 and month_n == 3) or (exp == 3 and month_n == 2)),
        want_refeed=lose and exp == 3 and month_n == 3,
        want_intensity_tech=exp == 3 and month_n == 2,
        want_beginner_deload=exp == 1 and month_n == 3,
        slugs=slugs,
        labels=labels,
    )
