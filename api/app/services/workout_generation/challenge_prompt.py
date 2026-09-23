"""Challenge (100-day) GPT profile: body stats, fitness tests, equipment specs."""

from __future__ import annotations

from typing import Any

from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.models.entities import Equipment
from app.services.workout_generation.coach_advice import GOAL_VI
from app.services.workout_generation.focus import focus_labels_vi

_SPEC_FAMILY: dict[str, str] = {
    "resistance-band-1": "resistance-band",
    "resistance-band-2": "resistance-band",
    "day-mini-band": "resistance-band",
}


def _as_int(val: Any) -> int | None:
    if val is None or val == "":
        return None
    try:
        return int(float(val))
    except (TypeError, ValueError):
        return None


def _as_number_label(val: Any) -> str | None:
    n = _as_int(val)
    if n is None:
        return None
    return str(n)


def equipment_specs_for_slugs(db: Session, slugs: list[str] | None) -> list[dict[str, Any]]:
    """Load catalog specs_vi for wizard/home implements (empty if column missing)."""
    wanted: list[str] = []
    seen: set[str] = set()
    requested = {str(s or "").strip().lower() for s in (slugs or []) if str(s or "").strip()}
    for raw in slugs or []:
        slug = str(raw or "").strip().lower()
        if not slug or slug in seen:
            continue
        seen.add(slug)
        wanted.append(slug)
        parent = _SPEC_FAMILY.get(slug)
        if parent and parent not in seen:
            seen.add(parent)
            wanted.append(parent)
    if not wanted:
        return []
    try:
        rows = db.query(Equipment).filter(Equipment.slug.in_(wanted)).all()
    except OperationalError:
        db.rollback()
        return [{"slug": s, "name_vi": s, "specs_vi": None} for s in wanted if s in requested]
    by_slug = {str(r.slug): r for r in rows}
    out: list[dict[str, Any]] = []
    for slug in wanted:
        if slug not in requested:
            continue
        row = by_slug.get(slug)
        parent = by_slug.get(_SPEC_FAMILY.get(slug, ""))
        specs = None
        name_vi = slug
        if row is not None:
            name_vi = str(row.name_vi or slug)
            specs = str(getattr(row, "specs_vi", None) or "").strip() or None
        if not specs and parent is not None:
            specs = str(getattr(parent, "specs_vi", None) or "").strip() or None
            if not name_vi or name_vi == slug:
                name_vi = str(parent.name_vi or slug)
        out.append({"slug": slug, "name_vi": name_vi, "specs_vi": specs})
    return out


def challenge_user_summary(profile: dict[str, Any]) -> str:
    """Vietnamese one-liner for the challenge GPT user message."""
    bits: list[str] = []
    goal = str(profile.get("goal") or "").strip()
    goal_vi = GOAL_VI.get(goal, goal)
    if goal_vi:
        bits.append(f"mục tiêu {goal_vi.lower()}")
    height = _as_int(profile.get("height_cm"))
    weight = _as_int(profile.get("weight_kg"))
    if height and weight:
        bits.append(f"{height}cm/{weight}kg")
    elif height:
        bits.append(f"{height}cm")
    elif weight:
        bits.append(f"{weight}kg")
    age = _as_int(profile.get("age"))
    if age:
        bits.append(f"{age} tuổi")
    kit = str(profile.get("test_kit") or "").strip()
    if kit:
        kit_vi = {
            "dumbbell": "kit tạ đơn",
            "band": "kit dây",
            "bar_rings": "kit xà·vòng",
        }.get(kit, kit)
        bits.append(kit_vi)
    tests = [str(t).strip() for t in (profile.get("tests_vi") or []) if str(t).strip()]
    if tests:
        bits.extend(tests)
    else:
        baseline = profile.get("fitness_baseline") or {}
        push = _as_number_label(baseline.get("pushups_max"))
        pull = _as_number_label(baseline.get("pullups_max"))
        squat = _as_number_label(baseline.get("squats_max"))
        plank = _as_number_label(baseline.get("plank_seconds"))
        if push is not None:
            bits.append(f"chống đẩy {push}")
        if pull is not None:
            bits.append(f"kéo xà {pull}")
        if squat is not None:
            bits.append(f"squat {squat}")
        if plank is not None:
            bits.append(f"plank {plank}s")
    focus = focus_labels_vi(list(profile.get("focus_areas") or []))
    if focus:
        bits.append("ưu tiên " + ", ".join(focus))
    minutes = _as_int(profile.get("session_minutes"))
    if minutes:
        bits.append(f"buổi {minutes} phút")
    specs = list(profile.get("equipment_specs") or [])
    if specs:
        names: list[str] = []
        for item in specs:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name_vi") or item.get("slug") or "").strip()
            spec = str(item.get("specs_vi") or "").strip()
            if name and spec:
                names.append(f"{name} ({spec})")
            elif name:
                names.append(name)
        if names:
            bits.append("dụng cụ: " + "; ".join(names))
    elif profile.get("no_equipment"):
        bits.append("không dụng cụ")
    return ", ".join(bits)


def enrich_challenge_pick_profile(
    db: Session,
    profile: dict[str, Any],
    payload: dict[str, Any],
    equipment_list: list[str] | None,
) -> dict[str, Any]:
    """Add body stats + equipment specs + Vietnamese coach brief (challenge path only)."""
    from app.services.workout_generation.load_estimate import (
        apply_challenge_load,
        public_baseline,
    )

    out = dict(profile)
    out["height_cm"] = payload.get("height_cm")
    out["weight_kg"] = payload.get("weight_kg")
    out["age"] = payload.get("age")
    out["equipment_list"] = list(equipment_list or [])
    out["equipment_specs"] = equipment_specs_for_slugs(db, equipment_list)
    loaded = apply_challenge_load(
        out.get("fitness_baseline") or payload.get("fitness_baseline") or {},
        weight_kg=payload.get("weight_kg"),
        gender=str(out.get("gender") or payload.get("gender") or ""),
        equipment_list=equipment_list,
    )
    out["test_kit"] = loaded.get("test_kit")
    out["tests_vi"] = list(loaded.get("_tests_vi") or [])
    out["load_hints"] = list(loaded.get("_load_hints") or [])
    out["fitness_baseline"] = public_baseline(loaded)
    out["focus_areas_vi"] = focus_labels_vi(
        list(payload.get("focus_areas") or out.get("focus_areas") or [])
    )
    out["coach_brief_vi"] = challenge_user_summary(out)
    return out
