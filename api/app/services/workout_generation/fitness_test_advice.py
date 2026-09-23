"""OpenAI (or fallback) advice after a live fitness test."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Any

from app.core.config import get_settings
from app.services.workout_generation.fitness_standards import (
    evaluate_fitness_baseline,
    familiarization_catalog,
)

logger = logging.getLogger(__name__)

OFFER_LEVEL: dict[str, str] = {
    "challenge_100": "advanced",
}

OFFER_LABEL_VI: dict[str, str] = {
    "challenge_100": "Thử thách 100 ngày",
}

FALLBACK_ADVICE = [
    "Giữ form trước số lần: lưng thẳng, không nín thở, dừng khi đau nhói.",
    "Tập 3 buổi/tuần và ngủ 7–8 tiếng — thể lực tăng khi hồi phục, không khi nhồi.",
    "Nếu chưa đạt chuẩn gói, bắt đầu từ biến thể dễ hơn (quỳ gối, treo xà, squat nông) rồi tiến dần.",
    "Uống nước đều và ăn đủ đạm từ món quen; đừng cắt ăn gấp sau một bài test.",
]


def package_level_for_offer(offer: str) -> str:
    key = (offer or "").strip().lower()
    return OFFER_LEVEL.get(key, "advanced")


def _drop_run_for_challenge_100(
    offer: str,
    checks: dict[str, Any],
    not_met: list[str],
    standards: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[str], list[dict[str, Any]]]:
    if (offer or "").strip().lower() != "challenge_100":
        return checks, not_met, standards
    checks = {key: value for key, value in checks.items() if key != "run"}
    not_met = [key for key in not_met if key != "run"]
    standards = [row for row in standards if row.get("key") != "run"]
    return checks, not_met, standards


def build_fitness_test_advice(
    *,
    gender: str,
    offer: str,
    fitness_baseline: dict[str, Any] | None,
    stretch_completed: bool,
    feeling: str | None = None,
) -> dict[str, Any]:
    normalized_gender = "female" if str(gender).strip().lower() == "female" else "male"
    level = package_level_for_offer(offer)
    evaluation = evaluate_fitness_baseline(normalized_gender, fitness_baseline or {})
    checks = dict(evaluation.get(level) or {})
    not_met_key = "advanced_not_met" if level == "advanced" else "basic_not_met"
    not_met = list(evaluation.get(not_met_key) or [])
    catalog = familiarization_catalog()
    standards = list((catalog.get("standards") or {}).get(normalized_gender, {}).get(level, []))
    checks, not_met, standards = _drop_run_for_challenge_100(
        offer, checks, not_met, standards
    )
    package_pass = bool(checks) and all(value is True for value in checks.values())
    stretch_failed = not bool(stretch_completed)
    overall_failed = stretch_failed or not package_pass
    baseline = dict(fitness_baseline or {})
    if (offer or "").strip().lower() == "challenge_100":
        baseline.pop("run_10min_meters", None)

    advice_vi, used_openai = _advice_lines(
        gender=normalized_gender,
        offer=offer,
        level=level,
        baseline=baseline,
        checks=checks,
        not_met=not_met,
        stretch_failed=stretch_failed,
        feeling=feeling or "",
        package_pass=package_pass,
    )
    return {
        "gender": normalized_gender,
        "offer": offer,
        "package_level": level,
        "package_pass": package_pass,
        "stretch_failed": stretch_failed,
        "overall_failed": overall_failed,
        "checks": checks,
        "not_met": not_met,
        "standards": standards,
        "evaluation": evaluation,
        "recommended_path": evaluation.get("recommended_path"),
        "advice_vi": advice_vi,
        "used_openai": used_openai,
    }


def _fallback() -> list[str]:
    return list(FALLBACK_ADVICE)


def _advice_lines(
    *,
    gender: str,
    offer: str,
    level: str,
    baseline: dict[str, Any],
    checks: dict[str, Any],
    not_met: list[str],
    stretch_failed: bool,
    feeling: str,
    package_pass: bool,
) -> tuple[list[str], bool]:
    settings = get_settings()
    if not (settings.openai_api_key or "").strip():
        lines = _fallback()
        if stretch_failed:
            lines = ["Bạn bỏ giãn cơ nên bài test bị đánh failed. Lần sau giữ đủ 3 phút giãn."] + lines
        return lines[:6], False

    payload = {
        "gender": gender,
        "offer": offer,
        "offer_vi": OFFER_LABEL_VI.get(offer, offer),
        "package_level": level,
        "package_pass": package_pass,
        "stretch_failed": stretch_failed,
        "checks": checks,
        "not_met": not_met,
        "fitness_baseline": baseline,
        "feeling": feeling,
    }
    system = (
        "Bạn là huấn luyện viên thể lực Việt Nam. So sánh số liệu test với chuẩn gói. "
        "Không bịa số, không chẩn đoán bệnh, không bảo người tập khi đau nhói. "
        "Viết 4 đến 6 câu lời khuyên ngắn, khích lệ dù đạt hay chưa. "
        "Trả JSON: {\"advice_vi\":[\"...\"]}"
    )
    body = {
        "model": settings.openai_model,
        "temperature": min(0.5, float(settings.openai_temperature or 0.4)),
        "max_completion_tokens": min(1024, int(settings.openai_max_tokens or 1024)),
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
    }
    url = settings.openai_base_url.rstrip("/") + "/chat/completions"
    timeout = min(30, int(settings.openai_timeout_seconds or 30))
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        content = data["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        advice = parsed.get("advice_vi") or []
        if not isinstance(advice, list):
            advice = [str(advice)]
        advice = [str(a).strip() for a in advice if str(a).strip()]
        if not advice:
            return _fallback(), False
        return advice[:6], True
    except (
        urllib.error.URLError,
        urllib.error.HTTPError,
        KeyError,
        IndexError,
        json.JSONDecodeError,
        ValueError,
        TimeoutError,
    ) as exc:
        logger.warning("Fitness test advice OpenAI failed: %s", exc)
        return _fallback(), False
