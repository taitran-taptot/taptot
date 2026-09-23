"""Challenge-only working-load hints from kit tests (Epley / bodyweight proxies)."""

from __future__ import annotations

import math
from typing import Any

_KIT_ALIASES = {
    "dumbbell": "dumbbell",
    "db": "dumbbell",
    "ta": "dumbbell",
    "tạ đơn": "dumbbell",
    "band": "band",
    "resistance-band": "band",
    "resistance_band": "band",
    "dây": "band",
    "bar_rings": "bar_rings",
    "bar-and-rings": "bar_rings",
    "bar-rings": "bar_rings",
    "bodyweight": "bar_rings",
    "xa": "bar_rings",
}


def epley_1rm(weight_kg: float, reps: int) -> float:
    """Epley 1RM = w × (1 + reps/30)."""
    return float(weight_kg) * (1.0 + max(0, int(reps)) / 30.0)


def working_8_10(one_rm: float) -> float:
    """Working load for ~8–10 reps ≈ 1RM / 1.30."""
    return float(one_rm) / 1.30


def clamp(value: float, lo: float, hi: float) -> float:
    return max(float(lo), min(float(hi), float(value)))


def round_kg(value: float) -> float:
    if value <= 0:
        return 0.0
    return float(round(value))


def working_rep_band(test_max: int, *, easy: bool = False) -> tuple[int, int]:
    """70–80% of an AMRAP test (60–75% for beginners / weak tests)."""
    if test_max <= 0:
        return 1, 3
    lo_pct, hi_pct = (0.60, 0.75) if easy else (0.70, 0.80)
    lo = max(1, int(math.floor(test_max * lo_pct)))
    hi = max(lo, int(math.floor(test_max * hi_pct)))
    return lo, min(hi, test_max)


def floor_from_knee_band(test_max: int) -> tuple[int, int]:
    """Standard push-up working reps from a knee-push-up test (not 70% of knee max)."""
    if test_max <= 0:
        return 3, 5
    lo = max(3, int(math.floor(test_max * 0.40)))
    hi = max(lo, int(math.floor(test_max * 0.55)))
    return lo, min(6, max(hi, 5))


def _as_int(val: Any) -> int | None:
    if val is None or val == "":
        return None
    try:
        return int(float(val))
    except (TypeError, ValueError):
        return None


def _as_float(val: Any) -> float | None:
    if val is None or val == "":
        return None
    try:
        n = float(val)
    except (TypeError, ValueError):
        return None
    if n < 0 or not math.isfinite(n):
        return None
    return n


def infer_test_kit(baseline: dict[str, Any] | None, equipment_list: list[str] | None) -> str:
    raw = str((baseline or {}).get("test_kit") or "").strip().lower()
    if raw in _KIT_ALIASES:
        return _KIT_ALIASES[raw]
    slugs = {str(s or "").strip().lower() for s in (equipment_list or []) if str(s or "").strip()}
    if "dumbbell" in slugs:
        return "dumbbell"
    if any("resistance-band" in s or s == "day-mini-band" for s in slugs):
        return "band"
    return "bar_rings"


def _rep_label(lo: int, hi: int) -> str:
    return f"{lo}-{hi}" if lo != hi else str(lo)


def _hint(
    pattern: str,
    *,
    working_reps: str,
    load_kg_each: float | None = None,
    note_vi: str,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "pattern": pattern,
        "working_reps": working_reps,
        "note_vi": note_vi,
    }
    if load_kg_each is not None and load_kg_each > 0:
        row["load_kg_each"] = round_kg(load_kg_each)
    return row


def build_tests_vi(kit: str, baseline: dict[str, Any], gender: str | None = None) -> list[str]:
    """Vietnamese sentences naming the tests the user actually did."""
    out: list[str] = []
    female = str(gender or "").strip().lower() == "female"
    plank = _as_int(baseline.get("plank_seconds"))

    if kit == "dumbbell":
        press_r = _as_int(baseline.get("db_press_reps"))
        press_kg = _as_float(baseline.get("db_press_kg"))
        row_r = _as_int(baseline.get("db_row_reps"))
        row_kg = _as_float(baseline.get("db_row_kg"))
        gob_r = _as_int(baseline.get("goblet_reps"))
        gob_kg = _as_float(baseline.get("goblet_kg"))
        if press_r is not None:
            if press_kg:
                out.append(f"đẩy ngực tạ đơn {press_r} cái × {press_kg:g} kg")
            else:
                out.append(f"đẩy ngực tạ đơn {press_r} cái")
        if row_r is not None:
            if row_kg:
                out.append(f"chèo tạ đơn {row_r} cái × {row_kg:g} kg")
            else:
                out.append(f"chèo tạ đơn {row_r} cái")
        if gob_r is not None:
            if gob_kg:
                out.append(f"goblet squat {gob_r} cái × {gob_kg:g} kg")
            else:
                out.append(f"goblet squat {gob_r} cái")
        elif _as_int(baseline.get("squats_max")) is not None:
            out.append(f"squat {_as_int(baseline.get('squats_max'))} cái")
    elif kit == "band":
        push = _as_int(baseline.get("pushups_max"))
        pull = _as_int(baseline.get("pullups_max"))
        squat = _as_int(baseline.get("squats_max"))
        if push is not None:
            variant = str(baseline.get("pushup_variant") or "")
            name = "chống đẩy gối" if variant == "knee" else "chống đẩy sàn"
            out.append(f"{name} {push} cái")
        if pull is not None:
            out.append(f"kéo xô dây {pull} cái")
        if squat is not None:
            out.append(f"squat {squat} cái")
        level = str(baseline.get("band_level") or "").strip()
        if level:
            labels = {"light": "nhẹ", "medium": "vừa", "heavy": "nặng"}
            out.append(f"mức dây {labels.get(level, level)}")
    else:
        push = _as_int(baseline.get("pushups_max"))
        if push is not None:
            variant = str(baseline.get("pushup_variant") or "")
            name = "chống đẩy gối" if variant == "knee" else "chống đẩy"
            out.append(f"{name} {push} cái")
        hang = _as_int(baseline.get("pull_hold_seconds"))
        inv = _as_int(baseline.get("inverted_rows_max"))
        pull = _as_int(baseline.get("pullups_max"))
        variant = str(baseline.get("pull_test_variant") or "")
        if variant == "hang" or (hang is not None and pull is None and inv is None):
            if hang is not None:
                out.append(f"treo xà {hang} giây")
        elif variant.startswith("inverted") or inv is not None:
            if inv is not None:
                out.append(f"chèo vòng treo {inv} cái")
        elif pull is not None:
            out.append("treo xà" if female and pull == 0 else f"kéo xà {pull} cái")
        squat = _as_int(baseline.get("squats_max"))
        if squat is not None:
            out.append(f"squat {squat} cái")

    if plank is not None:
        out.append(f"plank {plank} giây")
    return out


def build_load_hints(
    kit: str,
    baseline: dict[str, Any],
    weight_kg: Any = None,
    *,
    easy: bool = False,
) -> list[dict[str, Any]]:
    hints: list[dict[str, Any]] = []
    bw = _as_float(weight_kg) or 0.0
    pct_note = "60–75% max test" if easy else "70–80% max test"

    def _wr(n: int) -> tuple[int, int]:
        return working_rep_band(n, easy=easy)

    if kit == "dumbbell":
        press_r = _as_int(baseline.get("db_press_reps"))
        press_kg = _as_float(baseline.get("db_press_kg"))
        if press_r is not None and press_kg:
            work = working_8_10(epley_1rm(press_kg, press_r))
            wr = _wr(press_r)
            fly = work * 0.55
            hints.append(
                _hint(
                    "h_press",
                    working_reps=_rep_label(*wr),
                    load_kg_each=work,
                    note_vi=(
                        f"Đẩy ngực tạ đơn: working ~{round_kg(work):g} kg mỗi tay "
                        f"({_rep_label(*wr)} cái)."
                    ),
                )
            )
            iso_lo, iso_hi = wr
            hints.append(
                _hint(
                    "iso_chest",
                    working_reps=_rep_label(iso_lo, iso_hi),
                    load_kg_each=fly,
                    note_vi=(
                        f"Isolation/fly ngực ~{round_kg(fly):g} kg, "
                        f"{_rep_label(iso_lo, iso_hi)} cái ({pct_note})."
                    ),
                )
            )
        elif press_r is not None:
            wr = _wr(press_r)
            hints.append(
                _hint(
                    "h_press",
                    working_reps=_rep_label(*wr),
                    note_vi=f"Đẩy ngực: {_rep_label(*wr)} cái ({pct_note}).",
                )
            )
        row_r = _as_int(baseline.get("db_row_reps"))
        row_kg = _as_float(baseline.get("db_row_kg"))
        if row_r is not None and row_kg:
            work = working_8_10(epley_1rm(row_kg, row_r))
            wr = _wr(row_r)
            hints.append(
                _hint(
                    "h_pull",
                    working_reps=_rep_label(*wr),
                    load_kg_each=work,
                    note_vi=f"Chèo tạ đơn: working ~{round_kg(work):g} kg mỗi tay ({_rep_label(*wr)} cái).",
                )
            )
        elif row_r is not None:
            wr = _wr(row_r)
            hints.append(
                _hint(
                    "h_pull",
                    working_reps=_rep_label(*wr),
                    note_vi=f"Chèo: {_rep_label(*wr)} cái ({pct_note}).",
                )
            )
        gob_r = _as_int(baseline.get("goblet_reps")) or _as_int(baseline.get("squats_max"))
        gob_kg = _as_float(baseline.get("goblet_kg"))
        if gob_r is not None and gob_kg:
            work = working_8_10(epley_1rm(gob_kg, gob_r))
            wr = _wr(gob_r)
            hints.append(
                _hint(
                    "squat",
                    working_reps=_rep_label(*wr),
                    load_kg_each=work,
                    note_vi=f"Goblet squat: working ~{round_kg(work):g} kg ({_rep_label(*wr)} cái).",
                )
            )
        elif gob_r is not None:
            wr = _wr(gob_r)
            hints.append(
                _hint(
                    "squat",
                    working_reps=_rep_label(*wr),
                    note_vi=f"Squat: {_rep_label(*wr)} cái ({pct_note}).",
                )
            )
        return hints

    if kit == "band":
        push = _as_int(baseline.get("pushups_max"))
        variant = str(baseline.get("pushup_variant") or "")
        if push is not None:
            wr = _wr(push)
            name = "chống đẩy gối" if variant == "knee" else "đẩy dây/chống đẩy"
            hints.append(
                _hint(
                    "h_press",
                    working_reps=_rep_label(*wr),
                    note_vi=f"{name.capitalize()}: {_rep_label(*wr)} cái — không bịa kg.",
                )
            )
            if variant == "knee":
                fl = floor_from_knee_band(push)
                hints.append(
                    _hint(
                        "h_press_floor",
                        working_reps=_rep_label(*fl),
                        note_vi=f"Chống đẩy sàn (từ test quỳ): {_rep_label(*fl)} cái.",
                    )
                )
        pull = _as_int(baseline.get("pullups_max"))
        if pull is not None:
            wr = _wr(pull)
            level = str(baseline.get("band_level") or "").strip()
            labels = {"light": "nhẹ", "medium": "vừa", "heavy": "nặng"}
            extra = f" mức dây {labels[level]}" if level in labels else ""
            note = f"Kéo xô/chèo dây: {_rep_label(*wr)} cái — không bịa kg"
            if extra:
                note = f"{note} ({extra.strip()})."
            else:
                note = f"{note}."
            hints.append(_hint("v_pull", working_reps=_rep_label(*wr), note_vi=note))
            hints.append(_hint("h_pull", working_reps=_rep_label(*wr), note_vi=note))
        squat = _as_int(baseline.get("squats_max"))
        if squat is not None:
            wr = _wr(squat)
            hints.append(
                _hint(
                    "squat",
                    working_reps=_rep_label(*wr),
                    note_vi=f"Squat dây: {_rep_label(*wr)} cái.",
                )
            )
        return hints

    push = _as_int(baseline.get("pushups_max"))
    variant = str(baseline.get("pushup_variant") or "")
    if push is not None:
        wr = _wr(push)
        bench_kg = None
        db_press = None
        if bw > 0 and variant != "knee":
            load = 0.66 * bw
            factor = clamp(push / 20.0, 0.45, 1.3)
            bench_kg = load * factor
            db_press = 0.40 * bench_kg
        name = "Chống đẩy gối" if variant == "knee" else "Chống đẩy"
        note = f"{name}: {_rep_label(*wr)} cái."
        if db_press:
            note += (
                f" Nếu lịch có tạ: bench 8–10 ~{round_kg(bench_kg or 0):g} kg; "
                f"DB press mỗi tay ~{round_kg(db_press):g} kg."
            )
        hints.append(
            _hint("h_press", working_reps=_rep_label(*wr), load_kg_each=db_press, note_vi=note)
        )
        if variant == "knee":
            fl = floor_from_knee_band(push)
            hints.append(
                _hint(
                    "h_press_floor",
                    working_reps=_rep_label(*fl),
                    note_vi=f"Chống đẩy sàn (từ test quỳ): {_rep_label(*fl)} cái.",
                )
            )

    pull_variant = str(baseline.get("pull_test_variant") or "").strip().lower()
    inv = _as_int(baseline.get("inverted_rows_max"))
    pullups = _as_int(baseline.get("pullups_max"))
    inverted = pull_variant.startswith("inverted") or (inv is not None and pullups is None)
    if inverted and inv is not None:
        wr = _wr(inv)
        hints.append(
            _hint(
                "h_pull",
                working_reps=_rep_label(*wr),
                note_vi=f"Chèo vòng treo: {_rep_label(*wr)} cái — không gắn kg kéo xà.",
            )
        )
    elif pullups is not None:
        wr = _wr(pullups)
        pulldown = None
        db_row = None
        if bw > 0:
            one_rm = bw * (1.0 + pullups / 30.0)
            pulldown = working_8_10(one_rm)
            db_row = 0.40 * pulldown
        note = f"Kéo xà: {_rep_label(*wr)} cái."
        if pulldown:
            note += (
                f" Pulldown 8–10 ~{round_kg(pulldown):g} kg; "
                f"DB row mỗi tay ~{round_kg(db_row or 0):g} kg."
            )
        hints.append(_hint("v_pull", working_reps=_rep_label(*wr), load_kg_each=pulldown, note_vi=note))
        hints.append(_hint("h_pull", working_reps=_rep_label(*wr), load_kg_each=db_row, note_vi=note))

    squat = _as_int(baseline.get("squats_max"))
    if squat is not None:
        wr = _wr(squat)
        hints.append(
            _hint("squat", working_reps=_rep_label(*wr), note_vi=f"Squat thể trọng: {_rep_label(*wr)} cái.")
        )
    return hints


def apply_challenge_load(
    baseline: dict[str, Any] | None,
    *,
    weight_kg: Any = None,
    gender: str | None = None,
    equipment_list: list[str] | None = None,
    easy: bool = False,
) -> dict[str, Any]:
    """Attach test_kit, tests_vi, load_hints onto a fitness_baseline copy."""
    out = dict(baseline or {})
    kit = infer_test_kit(out, equipment_list)
    out["test_kit"] = kit
    tests = build_tests_vi(kit, out, gender)
    hints = build_load_hints(kit, out, weight_kg, easy=easy)
    out["_tests_vi"] = tests
    out["_load_hints"] = hints
    return out


def public_baseline(baseline: dict[str, Any] | None) -> dict[str, Any]:
    return {k: v for k, v in dict(baseline or {}).items() if not str(k).startswith("_")}


def _item_blob(item: Any) -> tuple[str, str, str]:
    if isinstance(item, dict):
        names = f"{item.get('name_vi') or ''} {item.get('name_en') or ''}".strip().lower()
        pattern = str(item.get("movement_pattern") or "").strip().lower()
        role = str(item.get("movement_role") or "").strip().lower()
        return names, pattern, role
    names = f"{getattr(item, 'name_vi', '') or ''} {getattr(item, 'name_en', '') or ''}".strip().lower()
    pattern = str(getattr(item, "movement_pattern", "") or "").strip().lower()
    role = str(getattr(item, "movement_role", "") or "").strip().lower()
    return names, pattern, role


def hint_for_item(item: Any, hints: list[dict[str, Any]] | None) -> dict[str, Any] | None:
    """Pick the load hint whose pattern best matches an exercise."""
    if not hints:
        return None
    names, pattern, role = _item_blob(item)
    want: str | None = None
    knee = any(k in names for k in ("knee", "gối", "goi", "quỳ", "quy"))
    pullupish = any(
        k in names
        for k in ("pull-up", "pullup", "pull up", "kéo xà", "hít xà", "chin-up", "chinup")
    ) and not any(k in names for k in ("inverted", "row", "chèo", "scapular", "assisted", "1/3"))
    if pattern in {"h_push", "v_push"} or any(
        k in names for k in ("press", "push-up", "push up", "chống đẩy", "bench", "đẩy ngực")
    ):
        iso = role == "isolation" or any(
            k in names for k in ("fly", "ép ngực", "ep nguc", "raise", "crossover")
        )
        if iso:
            want = "iso_chest"
        elif not knee:
            want = "h_press_floor"
        else:
            want = "h_press"
    elif pattern == "v_pull" or any(
        k in names for k in ("pulldown", "pull-up", "kéo xà", "kéo xô", "chin")
    ):
        want = "v_pull"
    elif pattern == "h_pull" or any(k in names for k in ("row", "chèo", "face pull")):
        want = "h_pull"
    elif pattern == "squat" or "squat" in names or "goblet" in names:
        want = "squat"
    elif pattern == "hinge":
        want = "squat"
    by_pat = {str(h.get("pattern") or ""): h for h in hints if isinstance(h, dict)}
    if want and want in by_pat:
        return by_pat[want]
    if want == "h_press_floor" and "h_press" in by_pat:
        return by_pat["h_press"]
    if want == "iso_chest" and "h_press" in by_pat:
        return by_pat["h_press"]
    if want == "v_pull" and "h_pull" in by_pat and not pullupish:
        return by_pat["h_pull"]
    if want == "h_pull" and "v_pull" in by_pat:
        return by_pat["v_pull"]
    return None
