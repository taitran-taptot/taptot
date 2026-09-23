"""Coach skill ladders: keep the tested movement and at most one harder rung."""

from __future__ import annotations

from typing import Any

from app.services.workout_generation.weekly_volume import (
    fold_lift_name,
    is_knee_pushup_name,
    is_pushup_name,
)


def _as_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _blob(name_vi: str | None, name_en: str | None) -> str:
    return fold_lift_name(f"{name_vi or ''} {name_en or ''}")


def _item_names(item: Any) -> tuple[str | None, str | None]:
    if isinstance(item, dict):
        return (
            str(item.get("name_vi") or "") or None,
            str(item.get("name_en") or "") or None,
        )
    return (
        str(getattr(item, "name_vi", None) or "") or None,
        str(getattr(item, "name_en", None) or "") or None,
    )


def pushup_rung(name_vi: str | None, name_en: str | None = None) -> int | None:
    """0 wall … 4 floor … 6 decline/ring. None if not a push-up."""
    if not (is_pushup_name(name_vi) or is_pushup_name(name_en)):
        return None
    blob = _blob(name_vi, name_en)
    if any(k in blob for k in ("wall", "tuong")):
        return 0
    if any(
        k in blob
        for k in (
            "decline",
            "chan tren ghe",
            "chan ghe",
            "feet elevated",
            "elevated feet",
            "ring push",
        )
    ):
        return 6
    if any(
        k in blob
        for k in (
            "diamond",
            "kim cuong",
            "close grip",
            "close-grip",
            "hep",
            "archer",
        )
    ):
        return 5
    if is_knee_pushup_name(name_vi, name_en):
        return 3
    if any(k in blob for k in ("high incline", "incline high", "tay cao", "ke tay cao")):
        return 1
    if any(k in blob for k in ("low incline", "incline low", "tay thap", "ke tay thap")):
        return 2
    if any(k in blob for k in ("incline", "doc len", "tay tren ghe")):
        return 1
    return 4


def pull_rung(name_vi: str | None, name_en: str | None = None) -> int | None:
    """0 hang … 1 row … 2 assisted … 3 pull-up … 4 muscle-up. None if not in family."""
    blob = _blob(name_vi, name_en)
    if not blob:
        return None
    if any(k in blob for k in ("muscle-up", "muscle up", "muscleup", "weighted pull")):
        return 4
    pull_skill = any(
        k in blob
        for k in (
            "pull-up",
            "pull up",
            "pullup",
            "chin-up",
            "chin up",
            "chinup",
            "keo xa",
            "hit xa",
        )
    )
    if pull_skill and any(
        k in blob
        for k in ("assisted", "tro luc", "1/3", "scapular", "ba vai")
    ):
        return 2
    if pull_skill:
        return 3
    if any(
        k in blob
        for k in (
            "inverted",
            "australian",
            "ring row",
            "cheo vong",
            "keo nguoi nam",
            "keo nguoi duoi",
            "table row",
        )
    ):
        return 1
    if any(
        k in blob
        for k in ("dead hang", "active hang", "treo nguoi", "treo xa", "treo tha")
    ):
        return 0
    return None


def _push_working(baseline: dict[str, Any]) -> tuple[int, str, int | None] | None:
    reps = _as_int(baseline.get("pushups_max"))
    variant = str(baseline.get("pushup_variant") or "standard").strip().lower()
    if variant in {"wall"}:
        return 0, variant, reps
    if variant in {"incline_high", "incline-high", "high_incline"}:
        return 1, variant, reps
    if variant in {"incline_low", "incline-low", "low_incline", "incline"}:
        return 2, variant, reps
    if variant == "knee":
        return 3, variant, reps
    if reps is None and variant in {"", "standard"}:
        return None
    if reps is not None and reps <= 2:
        return 3, "standard", reps
    return 4, "standard", reps


def allowed_push_rungs(
    baseline: dict[str, Any] | None,
    *,
    phase_i: int = 0,
) -> frozenset[int] | None:
    base = baseline if isinstance(baseline, dict) else {}
    parsed = _push_working(base)
    if parsed is None:
        return None
    working, variant, reps = parsed
    lo = working
    if variant == "standard" and reps is not None and 3 <= reps <= 8:
        lo = 3
    if phase_i <= 0:
        hi = working
    elif phase_i == 1:
        hi = working + 1
    else:
        hi = working + 1
        if reps is not None and reps >= 20 and working >= 4:
            hi = min(6, working + 2)
    return frozenset(range(lo, hi + 1))


def allowed_pull_rungs(
    baseline: dict[str, Any] | None,
    *,
    phase_i: int = 0,
) -> frozenset[int] | None:
    base = baseline if isinstance(baseline, dict) else {}
    pullups = _as_int(base.get("pullups_max"))
    inverted = _as_int(base.get("inverted_rows_max"))
    variant = str(base.get("pull_test_variant") or "").strip().lower()
    if pullups is not None and pullups > 0:
        working = 3
    elif variant.startswith("inverted") or inverted is not None:
        working = 1
    elif variant in {"hang", "dead_hang", "dead-hang"}:
        working = 0
    elif pullups == 0:
        working = 1
    else:
        return None
    hi = working if phase_i <= 0 else min(4, working + 1)
    return frozenset(range(working, hi + 1))


def item_allowed_for_ladder(
    item: Any,
    *,
    push_rungs: frozenset[int] | None,
    pull_rungs: frozenset[int] | None,
) -> bool:
    nv, ne = _item_names(item)
    pr = pushup_rung(nv, ne)
    if pr is not None and push_rungs is not None and pr not in push_rungs:
        return False
    lr = pull_rung(nv, ne)
    if lr is not None and pull_rungs is not None and lr not in pull_rungs:
        return False
    return True


def filter_pool_by_ladder(
    items: list[Any],
    baseline: dict[str, Any] | None,
    *,
    phase_i: int = 0,
) -> list[Any]:
    push_rungs = allowed_push_rungs(baseline, phase_i=phase_i)
    pull_rungs = allowed_pull_rungs(baseline, phase_i=phase_i)
    if push_rungs is None and pull_rungs is None:
        return list(items)
    kept = [
        x
        for x in items
        if item_allowed_for_ladder(x, push_rungs=push_rungs, pull_rungs=pull_rungs)
    ]
    return kept or list(items)


def ladder_prompt_vi(
    baseline: dict[str, Any] | None,
    *,
    phase_i: int = 0,
) -> str:
    base = baseline if isinstance(baseline, dict) else {}
    bits: list[str] = []
    parsed = _push_working(base)
    if parsed is not None:
        working, variant, reps = parsed
        rungs = allowed_push_rungs(base, phase_i=phase_i) or frozenset()
        if working >= 4 and reps is not None and reps >= 20:
            bits.append(
                "Test sàn "
                f"{reps}: chỉ chống đẩy sàn hoặc kim cương/ring; cấm tường/quỳ."
            )
        elif variant == "knee":
            bits.append("Test quỳ gối: ưu tiên chống đẩy quỳ; cấm tường.")
        elif rungs:
            bits.append(
                f"Chống đẩy: chỉ rung {min(rungs)}–{max(rungs)} "
                "(không regression dễ hơn bài test)."
            )
    pull_rungs = allowed_pull_rungs(base, phase_i=phase_i)
    pullups = _as_int(base.get("pullups_max"))
    if pullups is not None and pullups > 0:
        bits.append(f"Test kéo xà {pullups}: được kéo xà trần; cấm inverted/hang làm compound chính.")
    elif pull_rungs is not None:
        bits.append("Chưa kéo xà trần: ưu tiên inverted/ring row; cấm kéo xà trần.")
    return " ".join(bits)
