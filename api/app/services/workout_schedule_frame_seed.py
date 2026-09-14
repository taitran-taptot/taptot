"""Canonical Level 1–3 schedule frames (experience × sessions) for AI plan generation."""

from __future__ import annotations

from typing import Any

# (day_index, label_vi, split_role, focus_vi, notes_vi|None, intensity)
DaySpec = tuple[int, str, str, str | None, str | None, str]

# (code, experience_level, sessions, name_vi, exp_label, exp_range, goal_vi, sort, days)
FrameSpec = tuple[str, int, int, str, str, str, str, int, list[DaySpec]]

L1_LABEL = "Chưa tập bao giờ"
L1_RANGE = "0–1 tháng"
L1_GOAL = "Làm quen kỹ thuật, cải thiện vận động và hình thành thói quen tập luyện."

L2_LABEL = "Mới tập cơ bản"
L2_RANGE = "1–6 tháng"
L2_GOAL = "Học bài tập chính, phát triển cơ bắp và sức mạnh nền tảng."

L3_LABEL = "Trung cấp"
L3_RANGE = "6 tháng–2 năm"
L3_GOAL = "Tăng cơ rõ rệt, tăng sức mạnh và quản lý khối lượng tập."


def _d(
    day_index: int,
    label_vi: str,
    split_role: str,
    focus_vi: str | None = None,
    notes_vi: str | None = None,
    intensity: str = "moderate",
) -> DaySpec:
    return (day_index, label_vi, split_role, focus_vi, notes_vi, intensity)


SCHEDULE_FRAME_SEED: list[FrameSpec] = [
    # —— Level 1 ——
    (
        "l1_s2_push_pull",
        1,
        2,
        "Làm quen động tác Toàn thân 2 buổi",
        L1_LABEL,
        L1_RANGE,
        L1_GOAL,
        10,
        [
            _d(0, "Buổi 1: Push — Đẩy", "push", "Đẩy", "Bao gồm chân", "easy"),
            _d(1, "Buổi 2: Pull — Kéo", "pull", "Kéo", "Bao gồm chân", "easy"),
        ],
    ),
    (
        "l1_s3_full_foundation",
        1,
        3,
        "Nền tảng Toàn thân 3 buổi",
        L1_LABEL,
        L1_RANGE,
        L1_GOAL,
        20,
        [
            _d(0, "Buổi 1: Thân trên cơ bản", "upper", "Thân trên cơ bản", None, "easy"),
            _d(1, "Buổi 2: Thân dưới cơ bản", "lower", "Thân dưới cơ bản", None, "easy"),
            _d(
                2,
                "Buổi 3: Cardio nhẹ, mobility và core",
                "conditioning",
                "Cardio nhẹ, mobility, core",
                None,
                "easy",
            ),
        ],
    ),
    (
        "l1_s4_movement_intro",
        1,
        4,
        "Làm quen Vận động 4 buổi",
        L1_LABEL,
        L1_RANGE,
        L1_GOAL,
        30,
        [
            _d(0, "Buổi 1: Thân trên cơ bản", "upper", "Thân trên cơ bản", None, "easy"),
            _d(1, "Buổi 2: Thân dưới cơ bản", "lower", "Thân dưới cơ bản", None, "easy"),
            _d(2, "Buổi 3: Full Body kỹ thuật", "fb", "Full body kỹ thuật", None, "easy"),
            _d(
                3,
                "Buổi 4: Cardio nhẹ, mobility và core",
                "conditioning",
                "Cardio nhẹ, mobility, core",
                None,
                "easy",
            ),
        ],
    ),
    (
        "l1_s5_fitness_base",
        1,
        5,
        "Nền tảng Thể lực 5 buổi",
        L1_LABEL,
        L1_RANGE,
        L1_GOAL,
        40,
        [
            _d(0, "Buổi 1: Thân trên cơ bản", "upper", "Thân trên cơ bản", None, "easy"),
            _d(1, "Buổi 2: Thân dưới cơ bản", "lower", "Thân dưới cơ bản", None, "easy"),
            _d(2, "Buổi 3: Cardio nhẹ và mobility", "conditioning", "Cardio nhẹ, mobility", None, "easy"),
            _d(3, "Buổi 4: Full Body nhẹ", "fb", "Full body nhẹ", None, "easy"),
            _d(
                4,
                "Buổi 5: Core, thăng bằng và vận động chức năng",
                "core",
                "Core, thăng bằng, vận động chức năng",
                None,
                "easy",
            ),
        ],
    ),
    (
        "l1_s6_habit",
        1,
        6,
        "Thói quen Vận động 6 buổi",
        L1_LABEL,
        L1_RANGE,
        L1_GOAL,
        50,
        [
            _d(0, "Buổi 1: Thân trên cơ bản", "upper", "Thân trên cơ bản", None, "easy"),
            _d(1, "Buổi 2: Thân dưới cơ bản", "lower", "Thân dưới cơ bản", None, "easy"),
            _d(2, "Buổi 3: Mobility và core", "mobility", "Mobility, core", None, "easy"),
            _d(3, "Buổi 4: Full Body B", "fb", "Full body B", None, "easy"),
            _d(
                4,
                "Buổi 5: Đi bộ, giãn cơ và phục hồi chủ động",
                "recovery",
                "Đi bộ, giãn cơ, phục hồi chủ động",
                None,
                "easy",
            ),
            _d(5, "Buổi 6: Full Body B", "fb", "Full body B", None, "easy"),
        ],
    ),
    # —— Level 2 ——
    (
        "l2_s2_ul",
        2,
        2,
        "Toàn thân Cơ bản 2 buổi",
        L2_LABEL,
        L2_RANGE,
        L2_GOAL,
        110,
        [
            _d(0, "Buổi 1: Upper — Ngực, lưng, vai, tay", "upper", "Ngực, lưng, vai, tay"),
            _d(1, "Buổi 2: Lower — Đùi trước, đùi sau, mông, bắp chân", "lower", "Đùi trước, đùi sau, mông, bắp chân"),
        ],
    ),
    (
        "l2_s3_ppl",
        2,
        3,
        "Toàn thân Phát triển 3 buổi",
        L2_LABEL,
        L2_RANGE,
        L2_GOAL,
        120,
        [
            _d(0, "Buổi 1: Push — Ngực, vai trước, tay sau", "push", "Ngực, vai trước, tay sau"),
            _d(1, "Buổi 2: Pull — Lưng, vai sau, tay trước", "pull", "Lưng, vai sau, tay trước"),
            _d(2, "Buổi 3: Legs — Chân, mông, bắp chân", "legs", "Chân, mông, bắp chân"),
        ],
    ),
    (
        "l2_s4_ul_ab",
        2,
        4,
        "Upper Lower Cơ bản 4 buổi",
        L2_LABEL,
        L2_RANGE,
        L2_GOAL,
        130,
        [
            _d(0, "Buổi 1: Upper A — Ngực, lưng, vai, tay", "upper", "Ngực, lưng, vai, tay"),
            _d(1, "Buổi 2: Lower A — Đùi trước, đùi sau, mông, bắp chân", "lower", "Đùi trước, đùi sau, mông, bắp chân"),
            _d(2, "Buổi 3: Upper B — Biến thể thân trên", "upper", "Biến thể thân trên"),
            _d(3, "Buổi 4: Lower B — Biến thể thân dưới", "lower", "Biến thể thân dưới"),
        ],
    ),
    (
        "l2_s5_ppl_ul",
        2,
        5,
        "Push Pull Legs Cơ bản 5 buổi",
        L2_LABEL,
        L2_RANGE,
        L2_GOAL,
        140,
        [
            _d(0, "Buổi 1: Push — Ngực, vai trước, tay sau", "push", "Ngực, vai trước, tay sau"),
            _d(1, "Buổi 2: Pull — Lưng, vai sau, tay trước", "pull", "Lưng, vai sau, tay trước"),
            _d(2, "Buổi 3: Legs — Chân, mông, bắp chân", "legs", "Chân, mông, bắp chân"),
            _d(3, "Buổi 4: Upper — Thân trên tổng hợp", "upper", "Thân trên tổng hợp"),
            _d(4, "Buổi 5: Lower — Thân dưới tổng hợp", "lower", "Thân dưới tổng hợp"),
        ],
    ),
    (
        "l2_s6_ppl_ab",
        2,
        6,
        "Push Pull Legs Cơ bản 6 buổi",
        L2_LABEL,
        L2_RANGE,
        L2_GOAL,
        150,
        [
            _d(0, "Buổi 1: Push A — Bài cơ bản, rep thấp đến trung bình", "push", "Bài cơ bản, rep thấp đến trung bình"),
            _d(1, "Buổi 2: Pull A — Bài cơ bản, rep thấp đến trung bình", "pull", "Bài cơ bản, rep thấp đến trung bình"),
            _d(2, "Buổi 3: Legs A — Bài cơ bản, rep thấp đến trung bình", "legs", "Bài cơ bản, rep thấp đến trung bình"),
            _d(3, "Buổi 4: Push B — Máy và bài phụ, rep trung bình đến cao", "push", "Máy và bài phụ, rep trung bình đến cao"),
            _d(4, "Buổi 5: Pull B — Máy và bài phụ, rep trung bình đến cao", "pull", "Máy và bài phụ, rep trung bình đến cao"),
            _d(5, "Buổi 6: Legs B — Máy và bài phụ, rep trung bình đến cao", "legs", "Máy và bài phụ, rep trung bình đến cao"),
        ],
    ),
    # —— Level 3 (maps UI experience 3–4: 6 tháng–2 năm) ——
    (
        "l3_s2_ul_intense",
        3,
        2,
        "Toàn thân Cường độ cao 2 buổi",
        L3_LABEL,
        L3_RANGE,
        L3_GOAL,
        210,
        [
            _d(0, "Buổi 1: Upper — Thân trên tổng hợp", "upper", "Thân trên tổng hợp", None, "hard"),
            _d(1, "Buổi 2: Lower — Thân dưới tổng hợp", "lower", "Thân dưới tổng hợp", None, "hard"),
        ],
    ),
    (
        "l3_s3_ppl",
        3,
        3,
        "Toàn thân Trung cấp 3 buổi",
        L3_LABEL,
        L3_RANGE,
        L3_GOAL,
        220,
        [
            _d(0, "Buổi 1: Push — Ngực, vai trước, tay sau", "push", "Ngực, vai trước, tay sau"),
            _d(1, "Buổi 2: Pull — Lưng, vai sau, tay trước", "pull", "Lưng, vai sau, tay trước"),
            _d(2, "Buổi 3: Legs — Chân, mông, bắp chân", "legs", "Chân, mông, bắp chân"),
        ],
    ),
    (
        "l3_s4_ul_strength_hyper",
        3,
        4,
        "Upper Lower Trung cấp 4 buổi",
        L3_LABEL,
        L3_RANGE,
        L3_GOAL,
        230,
        [
            _d(0, "Buổi 1: Upper Strength — Thân trên thiên về sức mạnh", "upper", "Thân trên thiên về sức mạnh", None, "hard"),
            _d(1, "Buổi 2: Lower Strength — Thân dưới thiên về sức mạnh", "lower", "Thân dưới thiên về sức mạnh", None, "hard"),
            _d(2, "Buổi 3: Upper Hypertrophy — Thân trên thiên về tăng cơ", "upper", "Thân trên thiên về tăng cơ", None, "hypertrophy"),
            _d(3, "Buổi 4: Lower Hypertrophy — Thân dưới thiên về tăng cơ", "lower", "Thân dưới thiên về tăng cơ", None, "hypertrophy"),
        ],
    ),
    (
        "l3_s5_muscle_dev",
        3,
        5,
        "Phát triển Cơ bắp Trung cấp 5 buổi",
        L3_LABEL,
        L3_RANGE,
        L3_GOAL,
        240,
        [
            _d(0, "Buổi 1: Push — Ngực, vai, tay sau", "push", "Ngực, vai, tay sau"),
            _d(1, "Buổi 2: Pull — Lưng, vai sau, tay trước", "pull", "Lưng, vai sau, tay trước"),
            _d(2, "Buổi 3: Legs — Chân và mông", "legs", "Chân và mông"),
            _d(3, "Buổi 4: Upper — Thân trên, ưu tiên nhóm cơ yếu", "upper", "Thân trên, ưu tiên nhóm cơ yếu"),
            _d(4, "Buổi 5: Lower — Thân dưới, ưu tiên nhóm cơ yếu", "lower", "Thân dưới, ưu tiên nhóm cơ yếu"),
        ],
    ),
    (
        "l3_s6_ppl_strength_hyper",
        3,
        6,
        "Push Pull Legs Trung cấp 6 buổi",
        L3_LABEL,
        L3_RANGE,
        L3_GOAL,
        250,
        [
            _d(0, "Buổi 1: Push Strength", "push", "Push strength", None, "hard"),
            _d(1, "Buổi 2: Pull Strength", "pull", "Pull strength", None, "hard"),
            _d(2, "Buổi 3: Legs Strength", "legs", "Legs strength", None, "hard"),
            _d(3, "Buổi 4: Push Hypertrophy", "push", "Push hypertrophy", None, "hypertrophy"),
            _d(4, "Buổi 5: Pull Hypertrophy", "pull", "Pull hypertrophy", None, "hypertrophy"),
            _d(5, "Buổi 6: Legs Hypertrophy", "legs", "Legs hypertrophy", None, "hypertrophy"),
        ],
    ),
]


def frames_as_dicts() -> list[dict[str, Any]]:
    """Flatten seed for tests / tooling."""
    out: list[dict[str, Any]] = []
    for code, level, sessions, name, exp_label, exp_range, goal, sort, days in SCHEDULE_FRAME_SEED:
        out.append(
            {
                "code": code,
                "experience_level": level,
                "sessions_per_week": sessions,
                "name_vi": name,
                "experience_label_vi": exp_label,
                "experience_range_vi": exp_range,
                "goal_vi": goal,
                "sort_order": sort,
                "days": [
                    {
                        "day_index": d[0],
                        "label_vi": d[1],
                        "split_role": d[2],
                        "focus_vi": d[3],
                        "notes_vi": d[4],
                        "intensity": d[5],
                    }
                    for d in days
                ],
            }
        )
    return out
