"""Learner-facing 100-day phase copy (no internal playbook dump)."""

from __future__ import annotations

from typing import Any

from app.services.exercise_prescription import clamp_experience_level
from app.services.workout_generation.phase_knowledge import refs_for_challenge_phases_ui

_ACTIVITY_JOB = {
    "sedentary": "ngày thường ngồi nhiều",
    "light": "ngày thường đứng hoặc đi nhẹ",
    "moderate": "ngày thường đi lại nhiều",
    "active": "ngày thường lao động chân tay",
    "very_active": "ngày thường lao động nặng",
}

_PHASE_LABEL = ("Làm quen & dựng nền", "Tăng dần độ khó", "Củng cố thói quen")

# L1 = 0–1 tháng, L2 = 1–6 tháng, L3 = trên 6 tháng.
_PHASE_COPY: dict[int, tuple[str, str, str]] = {
    1: (
        "Trong pha này, bạn sẽ từng bước làm quen với các bài tập, học cách thực hiện động tác đúng kỹ thuật và xây dựng nền tảng thể lực cần thiết. Khối lượng tập được điều chỉnh để bạn có thể bắt đầu từ khả năng của chính mình, thay vì cố gắng chạy theo người khác.\n"
        "\n"
        "Mục tiêu pha này: Hiểu mình cần tập gì, biết cách tập an toàn hơn và tự tin hoàn thành những buổi tập đầu tiên.",
        "Khi bạn đã quen với việc tập luyện, đã đến lúc thử thách bản thân ở một cấp độ mới.\n"
        "Giáo án sẽ giúp bạn tiến bộ từng bước thông qua việc điều chỉnh độ khó bài tập, số lần lặp lại, số hiệp hoặc mức kháng lực tùy theo mục tiêu của bạn.\n"
        "\n"
        "Mục tiêu pha này: Khỏe hơn, thực hiện bài tập tốt hơn và từng bước nâng cao khả năng của bản thân.",
        "Trong pha này, bạn tập trung củng cố duy trì tập luyện, học cách duy trì sự nhất quán và điều chỉnh kế hoạch khi lịch trình hoặc thể trạng thay đổi. Bạn cũng sẽ hiểu rõ hơn cách lựa chọn bài tập và quản lý cường độ để tiếp tục tập luyện lâu dài.\n"
        "\n"
        "Mục tiêu của bạn: Chủ động duy trì tập luyện, bảo vệ những tiến bộ đã đạt được và xây dựng lối sống năng động bền vững.",
    ),
    2: (
        "Bạn đã bắt đầu vận động và có những trải nghiệm đầu tiên. Giờ là lúc xây dựng nền tảng để tập luyện hiệu quả hơn.\n"
        "\n"
        "Trong giai đoạn này, bạn sẽ làm quen với các bài tập phù hợp với khả năng hiện tại, từng bước hoàn thiện kỹ thuật và xây dựng nền tảng sức mạnh, sức bền cơ bắp cùng khả năng kiểm soát cơ thể.\n"
        "\n"
        "Mục tiêu: Nắm vững những kỹ năng cơ bản và sẵn sàng cho quá trình phát triển thể lực.",
        "Khi cơ thể đã thích nghi với những bài tập cơ bản, bạn có thể bắt đầu nâng cao thử thách.\n"
        "Thông qua việc điều chỉnh độ khó bài tập, số lần lặp, số hiệp hoặc mức kháng lực, bạn sẽ từng bước cải thiện sức mạnh, sức bền cơ bắp và khả năng vận động.\n"
        "Mỗi thay đổi đều dựa trên khả năng thực hiện và mức độ thích nghi của bạn, thay vì tăng độ khó một cách vội vàng.\n"
        "\n"
        "Mục tiêu: Phát triển có định hướng và nhận ra sự tiến bộ qua từng giai đoạn.",
        "Tiến bộ không chỉ nằm ở việc bạn có thể thực hiện nhiều bài tập hơn, mà còn ở khả năng duy trì việc tập luyện trong cuộc sống hằng ngày.\n"
        "\n"
        "Trong giai đoạn này, bạn củng cố kỹ thuật, duy trì lịch tập phù hợp và học cách điều chỉnh kế hoạch khi bận rộn hoặc cần thêm thời gian phục hồi.\n"
        "\n"
        "Mục tiêu: Xây dựng tính nhất quán và tạo nền tảng cho hành trình tập luyện lâu dài.",
    ),
    3: (
        "Bạn đã quen với việc vận động, nhưng mỗi hình thức tập luyện lại đòi hỏi những kỹ năng và khả năng thể chất khác nhau.\n"
        "Trong giai đoạn này, bạn sẽ làm quen với cấu trúc buổi tập, hoàn thiện kỹ thuật các bài tập và thích nghi dần với phương pháp tập luyện mới. Chương trình được thiết kế dựa trên khả năng hiện tại, giúp bạn tận dụng nền tảng vận động sẵn có mà không vội vàng tăng độ khó.\n"
        "Mục tiêu: Làm chủ những kỹ thuật cơ bản và sẵn sàng cho một chương trình tập luyện có hệ thống",
        "Khi đã thích nghi với phương pháp tập luyện mới, bạn có thể bắt đầu thử thách bản thân nhiều hơn.\n"
        "Thông qua việc điều chỉnh độ khó, khối lượng tập và cường độ phù hợp, bạn từng bước phát triển sức mạnh, sức bền cơ bắp và khả năng kiểm soát cơ thể. Các bài tập được lựa chọn theo mục tiêu, dụng cụ và khả năng thực hiện của bạn.\n"
        "Mục tiêu: Nâng cao năng lực thể chất và tạo ra những tiến bộ có thể theo dõi qua từng giai đoạn.",
        "Trong giai đoạn này, bạn củng cố kỹ thuật, duy trì khối lượng tập phù hợp và học cách cân bằng giữa tập luyện, nghỉ ngơi cùng các hoạt động thể thao khác. Bạn cũng từng bước chủ động hơn trong việc điều chỉnh kế hoạch theo lịch trình và mục tiêu cá nhân.\n"
        "\n"
        "Mục tiêu: Duy trì những tiến bộ đã đạt được và xây dựng nền tảng để tiếp tục phát triển lâu dài.",
    ),
}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _level(wizard: dict[str, Any]) -> int:
    return int(clamp_experience_level(wizard.get("experience_level")))


def _goal(wizard: dict[str, Any]) -> str:
    return _text(wizard.get("goal")).lower()


def _activity(wizard: dict[str, Any]) -> str:
    a = _text(wizard.get("activity")).lower()
    return a if a in _ACTIVITY_JOB else "moderate"


def challenge_phase_copy(wizard: dict[str, Any] | None) -> list[dict[str, Any]]:
    w = dict(wizard or {})
    level = _level(w)
    goal = _goal(w) or None
    activity = _activity(w)
    reading = refs_for_challenge_phases_ui(
        level,
        goal=goal,
        activity=activity,
        location=_text(w.get("location")) or None,
    )
    copy = _PHASE_COPY.get(level) or _PHASE_COPY[1]
    rows: list[dict[str, Any]] = []
    for i, label in enumerate(_PHASE_LABEL):
        rows.append(
            {
                "label_vi": label,
                "blurb_vi": "",
                "rationale_vi": copy[i],
                "knowledge_refs": reading[i],
            }
        )
    return rows
