"""Master schedule spec — sync with frontend/src/lib/scheduleSpecMaster.ts."""

from __future__ import annotations

import re
from dataclasses import dataclass

def _week_code(
    *,
    experience: str,
    sessions: int,
    gender: str,
    location: str,
    home_equip: str,
) -> str:
    """Master week token for experience × sessions × gender × gym/home × equipment."""
    sess = max(2, min(6, int(sessions)))
    g = "female" if (gender or "").strip().lower() == "female" else "male"
    loc = (location or "gym").strip().lower()
    he = home_equip if home_equip in {"with_equip", "no_equip"} else "with_equip"
    no_equip = loc == "home" and he == "no_equip"
    l1 = experience == "0-1"
    loaded = not no_equip

    if g == "male":
        if sess == 3:
            return "PPL" if loaded else "ULU"
        if loaded:
            return {2: "UL", 4: "ULUL", 5: "PPLUL", 6: "PPLPPL"}[sess]
        return {
            2: "UL",
            4: "ULUL",
            5: "ULUL, Cardio-Core",
            6: "ULULUL",
        }[sess]

    if loaded:
        return {
            2: "Lower, Upper",
            3: "LUL",
            4: "LPPL",
            5: "LULU, Cardio-Core",
            6: "Lower, Upper, Lower, Upper, Lower, Upper",
        }[sess]
    if l1:
        return {
            2: "Lower, Upper",
            3: "LUL",
            4: "ULUL",
            5: "LULU, Cardio-Core",
            6: "Lower, Upper, Lower, Upper, Lower, Upper",
        }[sess]
    return {
        2: "UL",
        3: "LUL",
        4: "ULUL",
        5: "LULU, Cardio-Core",
        6: "ULULUL",
    }[sess]


def _build_week_matrix() -> dict[str, str]:
    out: dict[str, str] = {}
    for exp in ("0-1", "1-6", "6-24"):
        for sess in (2, 3, 4, 5, 6):
            for gender in ("male", "female"):
                out[f"{exp}|{sess}|{gender}|gym"] = _week_code(
                    experience=exp,
                    sessions=sess,
                    gender=gender,
                    location="gym",
                    home_equip="with_equip",
                )
                for he in ("with_equip", "no_equip"):
                    out[f"{exp}|{sess}|{gender}|home|{he}"] = _week_code(
                        experience=exp,
                        sessions=sess,
                        gender=gender,
                        location="home",
                        home_equip=he,
                    )
    return out


WEEK_MATRIX: dict[str, str] = _build_week_matrix()

GYM_SESSION_BY_MIN: dict[int, dict] = {30: {'minutes': 30, 'warmup': '3p', 'lifting': '25p', 'cardio': 0, 'cooldown': '2p', 'totalLifts': 3, 'compounds': 1, 'compoundSets': 3, 'compoundRest': '2–3p', 'isolates': 2, 'isolateSets': 3, 'isolateRest': '1–2p'}, 45: {'minutes': 45, 'warmup': '5p', 'lifting': '35p', 'cardio': 0, 'cooldown': '5p', 'totalLifts': 4, 'compounds': 2, 'compoundSets': 3, 'compoundRest': '2–3p', 'isolates': 2, 'isolateSets': 3, 'isolateRest': '1–2p'}, 60: {'minutes': 60, 'warmup': '5p', 'lifting': '40p', 'cardio': '10p', 'cooldown': '5p', 'totalLifts': 5, 'compounds': 2, 'compoundSets': 3, 'compoundRest': '2–3p', 'isolates': 3, 'isolateSets': 3, 'isolateRest': '1–2p'}, 75: {'minutes': 75, 'warmup': '10p', 'lifting': '45p', 'cardio': '15p', 'cooldown': '5p', 'totalLifts': 6, 'compounds': 2, 'compoundSets': 3, 'compoundRest': '2–3p', 'isolates': 4, 'isolateSets': 3, 'isolateRest': '1–2p'}, 90: {'minutes': 90, 'warmup': '10p', 'lifting': '60p', 'cardio': '15p', 'cooldown': '5p', 'totalLifts': 7, 'compounds': 3, 'compoundSets': 3, 'compoundRest': '2–3p', 'isolates': 4, 'isolateSets': 3, 'isolateRest': '1–2p'}}

HOME_SESSION_BY_MIN: dict[int, dict] = {
    30: {
        "minutes": 30,
        "warmup": "3p",
        "cooldown": "2p",
        "main": "25p",
        "resistanceCount": 2,
        "conditioningCount": 1,
        "conditioningMinutes": 5,
        "resistanceSets": 3,
        "resistanceRest": "2–3p",
        "conditioningSets": 3,
        "conditioningRest": "1–2p",
    },
    45: {
        "minutes": 45,
        "warmup": "5p",
        "cooldown": "5p",
        "main": "35p",
        "resistanceCount": 3,
        "conditioningCount": 1,
        "conditioningMinutes": 8,
        "resistanceSets": 3,
        "resistanceRest": "2–3p",
        "conditioningSets": 3,
        "conditioningRest": "1–2p",
    },
    60: {
        "minutes": 60,
        "warmup": "5p",
        "cooldown": "10p",
        "main": "40p",
        "resistanceCount": 4,
        "conditioningCount": 1,
        "conditioningMinutes": 10,
        "resistanceSets": 3,
        "resistanceRest": "2–3p",
        "conditioningSets": 3,
        "conditioningRest": "1–2p",
    },
    75: {
        "minutes": 75,
        "warmup": "10p",
        "cooldown": "10p",
        "main": "55p",
        "resistanceCount": 5,
        "conditioningCount": 1,
        "conditioningMinutes": 15,
        "resistanceSets": 3,
        "resistanceRest": "2–3p",
        "conditioningSets": 3,
        "conditioningRest": "1–2p",
    },
    90: {
        "minutes": 90,
        "warmup": "10p",
        "cooldown": "10p",
        "main": "70p",
        "resistanceCount": 6,
        "conditioningCount": 1,
        "conditioningMinutes": 20,
        "resistanceSets": 3,
        "resistanceRest": "2–3p",
        "conditioningSets": 3,
        "conditioningRest": "1–2p",
    },
}

SESSION_MINUTE_BUCKETS: tuple[int, ...] = (30, 45, 60, 75, 90)

EXPERIENCE_TO_MASTER: dict[int, str] = {1: "0-1", 2: "1-6", 3: "6-24"}


@dataclass(frozen=True)
class ResolvedFrameDay:
    day_index: int
    label_vi: str
    split_role: str
    focus_vi: str | None = None
    notes_vi: str | None = None
    intensity: str = "moderate"


@dataclass(frozen=True)
class ResolvedFrame:
    code: str
    name_vi: str
    experience_level: int
    sessions_per_week: int
    week_code: str
    days: tuple[ResolvedFrameDay, ...]


def experience_to_master_key(experience_level: int) -> str:
    level = max(1, min(3, int(experience_level or 1)))
    return EXPERIENCE_TO_MASTER[level]


def snap_session_minutes(minutes: int) -> int:
    try:
        n = int(minutes)
    except (TypeError, ValueError):
        n = 60
    n = max(30, min(90, n))
    return min(SESSION_MINUTE_BUCKETS, key=lambda b: abs(b - n))


def lookup_week_split(
    *,
    experience: str,
    sessions: int,
    gender: str,
    location: str,
    home_equip: str,
) -> str | None:
    loc = (location or "home").strip().lower()
    g = "female" if (gender or "").strip().lower() == "female" else "male"
    if loc == "gym":
        key = f"{experience}|{sessions}|{g}|gym"
    else:
        he = home_equip if home_equip in {"with_equip", "no_equip"} else "with_equip"
        key = f"{experience}|{sessions}|{g}|home|{he}"
    return WEEK_MATRIX.get(key)


def _expand_token(token: str) -> list[str]:
    t = token.strip()
    if not t:
        return []
    if re.match(r"^FB\s*[×x]\s*2$", t, re.I):
        return ["Full Body", "Full Body"]
    compact = re.sub(r"\s+", "", t.replace(",", ""))
    if re.match(r"^(PPL){2}$", compact, re.I):
        return ["Push", "Pull", "Legs", "Push", "Pull", "Legs"]
    if re.match(r"^PPLUL$", compact, re.I):
        return ["Push", "Pull", "Legs", "Upper", "Lower"]
    if re.match(r"^LPPL$", compact, re.I):
        return ["Lower", "Push", "Pull", "Legs"]
    if re.match(r"^LULU$", compact, re.I):
        return ["Lower", "Upper", "Lower", "Upper"]
    if re.match(r"^LUL$", compact, re.I):
        return ["Lower", "Upper", "Lower"]
    if re.match(r"^(UL){3}$", compact, re.I):
        return ["Upper", "Lower", "Upper", "Lower", "Upper", "Lower"]
    if re.match(r"^ULUL$", compact, re.I):
        return ["Upper", "Lower", "Upper", "Lower"]
    if re.match(r"^ULU$", compact, re.I):
        return ["Upper", "Lower", "Upper"]
    if re.match(r"^PPL$", compact, re.I):
        return ["Push", "Pull", "Legs"]
    if re.match(r"^UL$", compact, re.I):
        return ["Upper", "Lower"]
    if re.match(r"^FB$", t, re.I) or re.match(r"^FullBody$", t, re.I):
        return ["Full Body"]
    if re.match(r"^(Leg|Legs)$", t, re.I):
        return ["Legs"]
    if re.match(r"^Lower$", t, re.I):
        return ["Lower"]
    if re.match(r"^Upper$", t, re.I):
        return ["Upper"]
    if re.match(r"^Push$", t, re.I):
        return ["Push"]
    if re.match(r"^Pull$", t, re.I):
        return ["Pull"]
    if re.match(r"^Cardio-Core$", t, re.I):
        return ["Cardio-Core"]
    return [t]


def expand_week_days(code: str) -> list[str]:
    raw = re.sub(r"\s+", " ", (code or "").strip())
    if not raw:
        return []
    if re.match(r"^FB\s*[×x]\s*2$", raw, re.I):
        return ["Full Body", "Full Body"]
    parts = raw.split(",") if "," in raw else [raw]
    out: list[str] = []
    for p in parts:
        out.extend(_expand_token(p))
    return out


def day_label_to_split_role(label: str) -> str:
    key = label.strip().lower()
    mapping = {
        "push": "push",
        "pull": "pull",
        "legs": "legs",
        "leg": "legs",
        "lower": "legs",
        "upper": "upper",
        "full body": "fb",
        "cardio-core": "core",
    }
    return mapping.get(key, "fb")


def home_bw_focus_label(split_role: str | None) -> str | None:
    """Honest home no-equip titles: Pull/Upper are not gym bar work."""
    key = (split_role or "").strip().lower()
    if key == "pull":
        return "Lưng · core (BW)"
    if key == "upper":
        return "Thân trên (BW)"
    return None


def resolve_master_frame(
    *,
    experience_level: int,
    sessions_per_week: int,
    gender: str,
    location: str,
    no_equipment: bool,
    week_code: str | None = None,
) -> ResolvedFrame:
    exp = experience_to_master_key(experience_level)
    sessions = max(2, min(6, int(sessions_per_week or 3)))
    loc = (location or "home").strip().lower()
    home_equip = "no_equip" if no_equipment else "with_equip"
    week_code = week_code or lookup_week_split(
        experience=exp,
        sessions=sessions,
        gender=gender,
        location=loc,
        home_equip=home_equip,
    )
    if not week_code:
        raise ValueError(
            f"No Master week template for {exp}, {sessions} buoi, {gender}, {loc}, {home_equip}"
        )
    labels = expand_week_days(week_code)
    days: list[ResolvedFrameDay] = []
    for i, lbl in enumerate(labels[:sessions]):
        role = day_label_to_split_role(lbl)
        intensity = "easy" if experience_level <= 1 else "moderate"
        display = lbl
        if no_equipment and loc == "home":
            display = home_bw_focus_label(role) or lbl
        days.append(
            ResolvedFrameDay(
                day_index=i,
                label_vi=f"Buổi {i + 1}: {display}",
                split_role=role,
                focus_vi=display,
                notes_vi=None,
                intensity=intensity,
            )
        )
    g = (gender or "male").strip().lower()[:1]
    code = f"master_{exp.replace('-', '')}_s{sessions}_{g}_{loc[:1]}_{home_equip[:2]}"
    name = f"Master {week_code} · {sessions} buổi/tuần"
    return ResolvedFrame(
        code=code,
        name_vi=name,
        experience_level=max(1, min(3, int(experience_level or 1))),
        sessions_per_week=sessions,
        week_code=week_code,
        days=tuple(days),
    )


def parse_duration_minutes(value: str | int | None) -> int:
    if value is None:
        return 0
    if isinstance(value, int):
        return max(0, value)
    s = str(value).strip().lower().replace("p", "")
    if not s or s == "0":
        return 0
    try:
        return max(0, int(float(s)))
    except ValueError:
        return 0


def gym_session_spec(minutes: int) -> dict:
    return dict(GYM_SESSION_BY_MIN[snap_session_minutes(minutes)])


def home_session_spec(minutes: int) -> dict:
    return dict(HOME_SESSION_BY_MIN[snap_session_minutes(minutes)])
