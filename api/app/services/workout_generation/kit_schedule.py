"""Pin the fitness-test lift for bands and dumbbells, and script bar/rings days."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.entities import Equipment, Exercise, ExerciseEquipment, MuscleGroup
from app.schemas.plans import PlanDayIn, PlanExerciseIn
from app.services.workout_generation.focus import (
    extra_focus_kind,
    normalize_focus_areas,
    sixty_push_pull_kinds,
)
from app.services.workout_generation.load_estimate import infer_test_kit
from app.services.workout_generation.shortlist import ShortlistItem
from app.services.workout_generation.split_map import normalize_split_role

# (name_en, name_vi) candidates, first hit in the catalog wins.
_DB_PUSH = [("Dumbbell Bench Press", "Đẩy ngực tạ đơn")]
_DB_PULL = [("Dumbbell Row Bilateral", "Chèo tạ đơn hai tay")]
_DB_LEGS = [("Dumbbell Goblet Squat", "Ngồi xổm ôm tạ đơn")]
_DB_FRONT = [
    ("Dumbbell Lateral Raise", "Nâng tay ngang tạ đơn"),
    ("Dumbbell Seated Overhead Press", "Đẩy vai ngồi tạ đơn"),
    ("Dumbbell Front Raise", "Nâng vai trước tạ đơn"),
]
_DB_TRI = [
    ("Dumbbell Skullcrusher", "Đập tạ sau đầu tạ đơn"),
    ("Dumbbell Seated Overhead Tricep Extension", "Duỗi tay sau ngồi tạ đơn"),
    ("Dumbbell Tricep Kickback", "Đá tay sau tạ đơn"),
]
_DB_FLY = [
    ("Dumbbell Chest Fly", "Ép ngực tạ đơn"),
    ("Dumbbell Incline Bench Press", "Đẩy ngực dốc lên tạ đơn"),
    ("Dumbbell Incline Chest Fly", "Ép ngực dốc lên tạ đơn"),
    ("Dumbbell Decline Bench Press", "Đẩy ngực dốc xuống tạ đơn"),
]
_DB_REAR = [
    ("Dumbbell Seated Rear Delt Fly", "Mở vai sau ngồi tạ đơn"),
    ("Dumbbell Rear Delt Fly", "Mở vai sau tạ đơn"),
]
_DB_BI = [
    ("Dumbbell Curl", "Cuốn tay tạ đơn"),
    ("Dumbbell Hammer Curl", "Cuốn tay kiểu búa tạ đơn"),
    ("Dumbbell Concentration Curl", "Cuốn tay tập trung tạ đơn"),
]
_DB_ROW2 = [
    ("Dumbbell Row Unilateral", "Chèo tạ đơn một tay"),
    ("Dumbbell Single Arm Row", "Chèo tạ đơn một tay"),
    ("Chest-Supported Dumbbell Row", "Chèo tạ đơn tựa ngực"),
]
_DB_HINGE = [
    ("Dumbbell Deadlift", "Nhấc tạ đơn từ đất"),
    ("Single-Leg Dumbbell Romanian Deadlift", "Kéo tạ đơn kiểu Romania một chân"),
    ("Kickstand Dumbbell Romanian Deadlift", "Nhấc tạ đơn gập hông chân trụ"),
]
_DB_QUAD = [
    [
        ("Dumbbell Lateral Lunge", "Chùng chân sang ngang tạ đơn"),
        ("Bodyweight Alternating Lateral Lunge", "Chùng chân sang ngang xen kẽ"),
    ],
    [("Dumbbell Step-Up (Low)", "Bước lên bục thấp tạ đơn")],
    [("Dumbbell Sumo Squat", "Ngồi xổm chân rộng tạ đơn")],
    [("Dumbbell Front Squat", "Ngồi xổm tạ đơn trước ngực")],
]
_DB_HAM = [
    [("Dumbbell Leg Curl", "Cuốn đùi sau tạ đơn")],
    [("Hamstring Curl", "Cuốn đùi sau")],
    [("Hip Hinge Speed Romanian Deadlift", "Nhấc tạ gập hông nhanh")],
    [("Kickstand Dumbbell Romanian Deadlift", "Nhấc tạ đơn gập hông chân trụ")],
    [("Dumbbell Deadlift", "Nhấc tạ đơn từ đất")],
]
_DB_CALF = [("Dumbbell Single Leg Calf Raise", "Nhón bắp chân một chân tạ đơn")]
_DB_SUMO_FILL = [
    ("Dumbbell Sumo Squat", "Ngồi xổm chân rộng tạ đơn"),
    ("Dumbbell Step-Up (Low)", "Bước lên bục thấp tạ đơn"),
    ("Dumbbell Front Squat", "Ngồi xổm tạ đơn trước ngực"),
    ("Dumbbell Hip Thrust", "Đẩy hông tạ đơn"),
]
_BAND_PUSH = [("Band Chest Press", "Đẩy ngực với dây kháng lực")]
_BAND_PULL = [("Band Seated Pulldown", "Kéo xô ngồi với dây")]
_BAND_LEGS = [("Band Squat", "Ngồi xổm với dây")]
_BAND_QUAD = [("Band Lunge", "Chùng chân với dây kháng lực")]
_BAND_FRONT = [
    ("Band Front Raise", "Nâng tay trước với dây"),
    ("Band Lateral Raise", "Nâng tay ngang với dây"),
    ("Band Single Arm Lateral Raise", "Nâng tay ngang một tay với dây"),
]
_BAND_TRI = [
    ("Band Tricep Pushdown", "Đẩy tay sau với dây"),
    ("Band Tricep Kickback", "Đá tay sau với dây"),
]
_BAND_FLY = [("Band Chest Fly", "Ép ngực với dây")]
_BAND_REAR = [
    ("Band Reverse Fly", "Bay vai sau với dây"),
    ("Band Pull-Apart", "Kéo dây tách"),
    ("Band Shrug", "Nhún vai với dây"),
]
_BAND_BI = [("Band Curl", "Cuốn tay với dây")]
_BAND_ROW2 = [("Band Row", "Chèo với dây"), ("Band Seated Row", "Chèo ngồi với dây")]
_BAND_HINGE = [
    ("Band Romanian Deadlift", "Nhấc tạ gập hông với dây"),
    ("Band Pull-Through", "Kéo dây qua háng"),
    ("Band Deadlift", "Kéo dây từ sàn"),
]
_BAND_HAM = [("Band Leg Curl", "Cuốn đùi sau với dây")]
_BAND_CALF = [
    ("Standing Calf Raise", "Nhón bắp chân đứng"),
    ("Bodyweight Calf Raise", "Nhón bắp chân"),
    ("Calf Raise", "Nhón bắp chân"),
]

_RING_PUSH = [("Ring Push-Up", "Chống đẩy vòng")]
_FLOOR_PUSH = [("Push Up", "Chống đẩy")]
_RING_DIP = [("Ring Dip", "Hít vòng")]
_PIKE = [
    ("Pike Push-Up", "Chống đẩy pike"),
    ("Elevated Pike Push-Up", "Chống đẩy pike chân cao"),
]
_RING_TRI = [
    ("Ring Triceps Extension", "Duỗi tay sau vòng"),
    ("Diamond Push Ups", "Chống đẩy kim cương"),
]
_RING_FLY = [("Ring Chest Fly", "Ép ngực vòng")]
_BAR_PULL = [("Pull Ups", "Hít xà"), ("Ring Pull-Up", "Kéo xà vòng")]
_RING_ROW = [("Ring Row", "Chèo vòng"), ("Pull-up Bar Inverted Row", "Chèo người trên xà")]
_REAR = [("Ring Rear Delt Fly", "Bay vai sau vòng"), ("Ring Face Pull", "Kéo mặt vòng")]
_RING_BI = [
    ("Ring Biceps Curl", "Cuốn tay trước vòng"),
    ("Chin-Up", "Hít xà úp"),
]
_ROW_EXTRA = [
    ("Ring Row", "Chèo vòng"),
    ("Ring Face-down Row", "Kéo ngang sấp vòng treo"),
    ("Pull-up Bar Inverted Row", "Chèo người trên xà"),
]
_SQUAT = [
    ("Bodyweight Squat", "Ngồi xổm không tạ"),
    ("Bodyweight Box Squat", "Ngồi xổm xuống hộp"),
    ("Bodyweight Alternating Reverse Lunges", "Chùng chân sau xen kẽ"),
]
_BULGARIAN = [("Bulgarian Ring Squat", "Squat Bulgaria vòng treo")]
_HAM = [("Ring Hamstring Curl", "Cuốn đùi sau vòng")]
_HINGE = [("Glute Bridge", "Cầu mông"), ("Single Leg Glute Bridge", "Cầu mông một chân")]
_CALF = [
    ("Standing Calf Raise", "Nhón bắp chân đứng"),
    ("Bodyweight Calf Raise", "Nhón bắp chân"),
    ("Calf Raise", "Nhón bắp chân"),
]
_BW_LEG_EXTRA = [
    ("Walking Lunge", "Bước tới"),
    ("Bodyweight Alternating Reverse Lunges", "Chùng chân sau xen kẽ"),
    ("Glute Bridge", "Cầu mông"),
    ("Standing Calf Raise", "Nhón bắp chân đứng"),
    ("Single Leg Glute Bridge", "Cầu mông một chân"),
]
_RING_ABS = [
    [("Ring Hanging Leg Raise", "Nâng chân treo vòng")],
    [
        ("Front Plank on Elbows", "Plank chống khuỷu"),
        ("Hand Plank", "Plank chống tay"),
    ],
]
_ABS = [
    ("Dead Bug", "Bọ chết"),
    ("Hand Plank", "Plank chống tay"),
    ("Bodyweight Russian Twist", "Xoay người"),
]
_FRONT_PLANK = [("Front Plank on Elbows", "Plank chống khuỷu")]
_ABS_EXTRA = [
    ("Dead Bug", "Nằm ngửa giơ tay chân"),
    ("Elbow Side Plank", "Chống người nghiêng chống khuỷu"),
    ("V-Up", "Gập bụng hai đầu"),
    ("Bodyweight Russian Twist", "Xoay người"),
]
_BW_ABS = [
    ("Dead Bug", "Bọ chết"),
    ("Front Plank on Elbows", "Plank chống khuỷu"),
    ("Hand Plank", "Plank chống tay"),
    ("Bodyweight Russian Twist", "Xoay người"),
]
_ABS_PLANK = [
    ("Front Plank on Elbows", "Plank chống khuỷu"),
    ("Hand Plank", "Plank chống tay"),
]
_ABS_SITUP = [("Dumbbell Situp", "Gập bụng ngồi tạ đơn")]
_DB_GLUTE = [
    ("Dumbbell Hip Thrust", "Đẩy hông tạ đơn"),
    ("Glute Bridge", "Cầu mông"),
    ("Single Leg Glute Bridge", "Cầu mông một chân"),
]
_BAND_GLUTE = [
    ("Band Hip Thrust", "Đẩy hông với dây"),
    ("Band Glute Kickback", "Đá mông với dây"),
    ("Glute Bridge", "Cầu mông"),
    ("Single Leg Glute Bridge", "Cầu mông một chân"),
]
_CARDIO_INTERVAL = [
    ("Shadow Boxing", "Đấm bóng tưởng tượng"),
    ("Jumping Jack", "Nhảy dang chân"),
]
_CARDIO_RUN = [("Trail Run", "Chạy bền")]


def resistance_slot_count(session_minutes: int | None) -> int:
    """Home 45/60 resistance slots. Unknown minutes stay at the 45-minute frame."""
    if session_minutes is None:
        return 3
    from app.services.schedule_spec_master import snap_session_minutes

    snap_session_minutes(int(session_minutes))
    return 5  # 45 and 60 both use five resistance slots


def _baseline_int(baseline: dict[str, Any] | None, key: str) -> int | None:
    if not isinstance(baseline, dict) or key not in baseline:
        return None
    raw = baseline.get(key)
    if raw is None or raw == "":
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _cycle(options: list[tuple[str, str]], month: int) -> list[tuple[str, str]]:
    """Keep the same muscle, start at a different exercise each month."""
    if len(options) < 2:
        return list(options)
    i = int(month) % len(options)
    return options[i:] + options[:i]


def _pick_month(
    groups: list[list[tuple[str, str]]], month: int
) -> list[tuple[str, str]]:
    if not groups:
        return []
    return list(groups[int(month) % len(groups)])


def _month_index(day_number: int | None) -> int:
    return max(0, int(day_number or 1) - 1) // 28


def _variety_index(day_number: int | None, explicit: int | None) -> int:
    if explicit is not None:
        return max(0, int(explicit))
    return max(0, (int(day_number or 1) - 1) // 3)


def _insert_kind(base: list[str], extra: str) -> list[str]:
    out = list(base)
    last = max((i for i, kind in enumerate(out) if kind == extra), default=None)
    if last is None:
        out.append(extra)
    else:
        out.insert(last + 1, extra)
    return out


def challenge_strength_kinds(role: str | None, phase_index: int) -> list[str]:
    """Fixed force-slot kinds for a 100-day phase. Test lift is always first."""
    key = str(role or "").strip().lower()
    extra = max(0, min(2, int(phase_index))) >= 1
    if key == "push":
        return (
            ["chest", "chest", "shoulder", "shoulder", "triceps"]
            if extra
            else ["chest", "chest", "shoulder", "triceps"]
        )
    if key == "pull":
        return (
            ["back", "back", "rear", "rear", "biceps"]
            if extra
            else ["back", "back", "rear", "biceps"]
        )
    if key in {"legs", "lower"}:
        return ["legs", "quad", "ham"] if extra else ["legs", "quad"]
    if key == "upper":
        return (
            ["chest", "back", "shoulder", "back", "biceps"]
            if extra
            else ["chest", "back", "shoulder", "biceps"]
        )
    return []


def challenge_strength_slots(role: str | None, phase_index: int) -> int:
    kinds = challenge_strength_kinds(role, phase_index)
    if kinds:
        return len(kinds)
    return 5 if max(0, min(2, int(phase_index))) >= 1 else 4


def challenge_finisher_kind(phase_index: int | None, week_day_index: int) -> str:
    """P1 both abs+cardio; P2/P3 alternate by session order in the week."""
    try:
        phase = 0 if phase_index is None else int(phase_index)
    except (TypeError, ValueError):
        phase = 0
    if phase <= 0:
        return "both"
    try:
        idx = int(week_day_index)
    except (TypeError, ValueError):
        idx = 0
    return "abs" if idx % 2 == 0 else "cardio"


def kit_kind_list(
    kit: str,
    role: str,
    slots: int,
    focus_keys: list[str] | None = None,
    phase_index: int | None = None,
) -> list[str]:
    """Default 45/60 kit layout; 60-minute extra isolation follows focus.

    Pass ``phase_index`` for the 100-day challenge (P1 four force slots, P2/P3 five).
    ``phase_index=None`` keeps the legacy 2-2-1 list even when ``slots`` is 4.
    """
    n = max(1, int(slots))
    key = str(role or "").strip().lower()
    loc = str(kit or "").strip().lower()
    if phase_index is not None:
        kinds = challenge_strength_kinds(role, phase_index)
        if kinds:
            extra = max(0, min(2, int(phase_index))) >= 1
            if loc == "band" and key in {"legs", "lower"}:
                return (
                    ["legs", "quad", "ham", "hinge", "glute"]
                    if extra
                    else ["legs", "quad", "hinge", "glute"]
                )
            if loc == "bar_rings" and key == "push" and extra:
                return ["chest", "chest", "shoulder", "chest", "triceps"]
            if loc == "dumbbell" and key in {"legs", "lower"} and len(kinds) < 3:
                return [*kinds, "sumo"]
            return kinds
    if key == "push":
        base = ["chest", "shoulder", "triceps"]
        default_extra = "chest"
    elif key == "pull":
        base = ["back", "rear", "biceps"]
        default_extra = "back"
    elif key in {"legs", "lower"}:
        if loc == "band":
            base = ["legs", "quad", "hinge"]
            default_extra = "glute"
        elif loc in {"dumbbell", "bar_rings"}:
            base = ["legs", "quad", "ham"]
            default_extra = "calf"
        else:
            base = ["legs", "hinge", "calf"]
            default_extra = "calf"
    elif key == "upper":
        base = ["chest", "back", "shoulder"]
        default_extra = "biceps"
    else:
        return []
    if n < 3:
        if key in {"legs", "lower"} and loc == "dumbbell":
            return ["legs", "ham"][:n]
        return base[:n]
    if n == 3:
        return base[:n]
    extra = extra_focus_kind(key, normalize_focus_areas(focus_keys))
    sixty = sixty_push_pull_kinds(key, extra)
    if sixty:
        return sixty
    if n >= 5 and key in {"legs", "lower"}:
        if loc == "band":
            return ["legs", "quad", "ham", "hinge", "glute"]
        if loc in {"dumbbell", "bar_rings"}:
            return ["legs", "quad", "ham", "glute", "calf"]
        return ["legs", "hinge", "glute", "ham", "calf"]
    if n >= 5 and key == "upper":
        return ["chest", "back", "back", "shoulder", "biceps"]
    if key in {"legs", "lower"}:
        extra = default_extra
    else:
        extra = extra or default_extra
    return _insert_kind(base, extra)[:n]


def gear_plan(
    kit: str,
    role: str,
    slots: int,
    month: int = 0,
    focus_keys: list[str] | None = None,
    phase_index: int | None = None,
) -> list[tuple[str, list[tuple[str, str]]]]:
    """Ordered (muscle, name candidates). The test lift stays; the rest rotate by month."""
    if kit == "dumbbell":
        bank = {
            "chest": [_DB_PUSH, _cycle(_DB_FLY, month)],
            "shoulder": [_cycle(_DB_FRONT, month)],
            "triceps": [_cycle(_DB_TRI, month)],
            "back": [_DB_PULL, _cycle(_DB_ROW2, month)],
            "rear": [_cycle(_DB_REAR, month)],
            "biceps": [_cycle(_DB_BI, month)],
            "legs": [_DB_LEGS],
            "quad": [_pick_month(_DB_QUAD, month)],
            "ham": [_pick_month(_DB_HAM, month)],
            "sumo": [_DB_SUMO_FILL],
            "calf": [_DB_CALF],
            "glute": [_cycle(_DB_GLUTE, month)],
            "hinge": [_pick_month(_DB_HAM, month)],
        }
    elif kit == "band":
        bank = {
            "chest": [_BAND_PUSH, _cycle(_BAND_FLY, month)],
            "shoulder": [_cycle(_BAND_FRONT, month)],
            "triceps": [_cycle(_BAND_TRI, month)],
            "back": [_BAND_PULL, _cycle(_BAND_ROW2, month)],
            "rear": [_cycle(_BAND_REAR, month)],
            "biceps": [_cycle(_BAND_BI, month)],
            "legs": [_BAND_LEGS],
            "quad": [_cycle(_BAND_QUAD, month)],
            "ham": [_cycle(_BAND_HAM, month)],
            "calf": [_cycle(_BAND_CALF, month)],
            "glute": [_cycle(_BAND_GLUTE, month)],
            "hinge": [_cycle(_BAND_HINGE, month)],
        }
    else:
        return []
    kinds = kit_kind_list(kit, role, slots, focus_keys, phase_index=phase_index)
    seen: dict[str, int] = {}
    out: list[tuple[str, list[tuple[str, str]]]] = []
    for kind in kinds:
        options = bank.get(kind) or []
        idx = seen.get(kind, 0)
        seen[kind] = idx + 1
        cands = options[min(idx, len(options) - 1)] if options else []
        if idx and len(options) == 1:
            cands = _cycle(cands, month + idx)
        out.append((kind, list(cands or [])))
    return out


def gear_main_slots(
    kit: str,
    role: str,
    slots: int,
    month: int = 0,
    focus_keys: list[str] | None = None,
    phase_index: int | None = None,
) -> list[list[tuple[str, str]]]:
    """Full main list for a home band or dumbbell day. Empty for other kits."""
    return [
        candidates
        for _kind, candidates in gear_plan(
            kit, role, slots, month, focus_keys=focus_keys, phase_index=phase_index
        )
    ]


def kit_anchor_slots(kit: str, role: str) -> list[list[tuple[str, str]]]:
    """First mains to lock for band and dumbbell days. Empty when this kit does not pin."""
    if kit == "dumbbell":
        push, pull, legs = _DB_PUSH, _DB_PULL, _DB_LEGS
    elif kit == "band":
        push, pull, legs = _BAND_PUSH, _BAND_PULL, _BAND_LEGS
    elif kit == "bar_rings":
        push, pull, legs = _RING_PUSH, _BAR_PULL, _SQUAT[:1]
    else:
        return []
    if role == "push":
        return [push]
    if role == "pull":
        return [pull]
    if role in {"legs", "lower"}:
        return [legs]
    if role == "upper":
        return [push, pull]
    return []


def bar_rings_slots(
    role: str,
    *,
    pushups_max: int | None,
    pullups_max: int | None,
    experience_level: int | None,
    slots: int,
    variety: int = 0,
    focus_keys: list[str] | None = None,
    phase_index: int | None = None,
) -> list[list[tuple[str, str]]]:
    """Ordered main slots for a pull-up bar and rings day. Each slot is a name fallback list."""
    del experience_level
    push_n = pushups_max if pushups_max is not None else 0
    pull_n = pullups_max if pullups_max is not None else 0
    v = max(0, int(variety or 0))
    n = max(1, int(slots))
    if phase_index is not None:
        n = max(1, challenge_strength_slots(role, phase_index))
    push_first = _RING_PUSH if push_n > 10 else _FLOOR_PUSH
    pull_first = _BAR_PULL if pull_n >= 5 else _RING_ROW
    chest_extra = list(_RING_DIP) + list(_RING_FLY) if push_n > 15 else list(_RING_FLY)
    squat = _cycle(_SQUAT, v)
    keys = normalize_focus_areas(focus_keys)

    if not keys and phase_index is None:
        if role in {"legs", "lower"}:
            if n >= 5:
                return [squat, _BULGARIAN, _HAM, _cycle(_BW_LEG_EXTRA, v), _HINGE]
            if n >= 4:
                return [squat, _BULGARIAN, _HAM, _cycle(_BW_LEG_EXTRA, v)]
            if n >= 3:
                return [squat, _BULGARIAN, _HAM]
            return [squat, _HAM][:n]

        if role == "upper":
            extras = [_PIKE, _cycle(_REAR, v), _RING_BI]
            rotated = extras[v % len(extras) :] + extras[: v % len(extras)]
            mains = [push_first, pull_first]
            if n >= 5 and pull_first != _RING_ROW:
                mains.append(_RING_ROW)
            return [*mains, *rotated][:n]

    kinds = kit_kind_list("bar_rings", role, n, keys, phase_index=phase_index)
    if phase_index is not None:
        chest_slots = (
            [push_first, list(_RING_DIP), list(_RING_FLY)]
            if push_n > 15
            else [push_first, list(_RING_FLY), list(_RING_TRI[1:])]
        )
        shoulder_slots = [_PIKE]
    else:
        chest_slots = [push_first, _cycle(chest_extra, v)]
        shoulder_slots = [
            _PIKE,
            [
                ("Elevated Pike Push-Up", "Chống đẩy pike chân cao"),
                ("Pike Push-Up", "Chống đẩy pike"),
            ],
        ]
    bank: dict[str, list[list[tuple[str, str]]]] = {
        "chest": chest_slots,
        "shoulder": shoulder_slots,
        "triceps": [_RING_TRI],
        "back": [pull_first, _cycle(_ROW_EXTRA, v)],
        "rear": [_cycle(_REAR, v)],
        "biceps": [_RING_BI],
        "legs": [squat],
        "quad": [_BULGARIAN],
        "ham": [_HAM],
        "calf": [_cycle(_BW_LEG_EXTRA, v)],
        "glute": [_HINGE],
        "hinge": [_HINGE],
    }
    seen: dict[str, int] = {}
    out: list[list[tuple[str, str]]] = []
    for kind in kinds:
        options = bank.get(kind) or []
        idx = seen.get(kind, 0)
        seen[kind] = idx + 1
        cands = options[min(idx, len(options) - 1)] if options else []
        if idx and len(options) == 1:
            cands = _cycle(cands, v + idx)
        out.append(list(cands or []))
    return out


def _lookup_named(
    db: Session,
    candidates: list[tuple[str, str]],
    used_ids: set[int] | None = None,
) -> Exercise | None:
    taken = used_ids or set()
    for name_en, name_vi in candidates:
        for column, value in ((Exercise.name_en, name_en), (Exercise.name_vi, name_vi)):
            text = str(value or "").strip()
            if not text:
                continue
            row = (
                db.query(Exercise)
                .filter(Exercise.is_active.is_(True), func.lower(column) == text.lower())
                .first()
            )
            if row is not None and int(row.id) not in taken:
                return row
    return None


def _place_extra(
    pairs: list[tuple[str, Exercise]],
    kind: str,
    row: Exercise,
) -> None:
    """Keep chest with chest and shoulders with shoulders. Abs close the day."""
    if kind == "abs":
        pairs.append((kind, row))
        return
    last = None
    for i, (slot_kind, _row) in enumerate(pairs):
        if slot_kind == kind:
            last = i
    if last is None:
        pairs.append((kind, row))
    else:
        pairs.insert(last + 1, (kind, row))


def _remember(db: Session, row: Exercise, meta_by_id: dict[int, Any] | None) -> None:
    if meta_by_id is None or int(row.id) in meta_by_id:
        return
    muscle = db.query(MuscleGroup).filter(MuscleGroup.id == row.muscle_group_id).first()
    gear = (
        db.query(Equipment.slug)
        .join(ExerciseEquipment, ExerciseEquipment.equipment_id == Equipment.id)
        .filter(ExerciseEquipment.exercise_id == row.id)
        .all()
    )
    meta_by_id[int(row.id)] = ShortlistItem(
        id=int(row.id),
        name_vi=row.name_vi,
        name_en=row.name_en,
        movement_role=row.movement_role,
        movement_pattern=row.movement_pattern,
        muscle_slug=str(getattr(muscle, "slug", "") or ""),
        difficulty=int(row.difficulty or 2),
        equipment_slugs=frozenset(str(slug) for (slug,) in gear if slug),
    )


def _clone_main(template: Any, exercise_id: int) -> PlanExerciseIn:
    return PlanExerciseIn(
        exercise_id=exercise_id,
        sets=int(getattr(template, "sets", None) or 3),
        reps=getattr(template, "reps", None) or "8-12",
        rest_seconds=int(getattr(template, "rest_seconds", None) or 90),
        section="main",
        notes_vi=getattr(template, "notes_vi", None),
        set_prescriptions=getattr(template, "set_prescriptions", None),
    )


def _splice_mains(day: PlanDayIn, mains: list[Any]) -> None:
    out: list[Any] = []
    inserted = False
    for ex in day.exercises:
        if str(getattr(ex, "section", "") or "") == "main":
            if not inserted:
                out.extend(mains)
                inserted = True
            continue
        out.append(ex)
    if not inserted:
        out.extend(mains)
    day.exercises = out
    for i, ex in enumerate(day.exercises, start=1):
        ex.sort_order = i


def _sets_max_for_level(experience_level: int | None) -> int:
    return 3 if int(experience_level or 2) <= 1 else 4


def _stamp_challenge_test_lift_sets(
    mains: list[PlanExerciseIn],
    pairs: list[tuple[str, Exercise]],
    *,
    phase_index: int,
    sets_cap: int,
) -> None:
    """P1 3 / P2 4 / P3 3 on the first force slot only. Isolation stays capped."""
    from app.services.workout_generation.challenge_dose import challenge_test_lift_sets

    test_sets = challenge_test_lift_sets(phase_index)
    first = True
    for ex, (kind, _row) in zip(mains, pairs):
        if kind in {"abs", "abs_extra", "bw", "cardio"}:
            continue
        if first:
            ex.sets = test_sets
            first = False
        else:
            ex.sets = min(int(sets_cap or 3), 3)


def _shift_one_set(
    mains: list[PlanExerciseIn],
    pairs: list[tuple[str, Exercise]],
    *,
    add: str,
    sub: str,
    sets_max: int,
) -> None:
    for ex, (kind, _row) in zip(mains, pairs):
        if kind == add:
            cur = int(ex.sets or 3)
            if cur < sets_max:
                ex.sets = cur + 1
            break
    for ex, (kind, _row) in zip(mains, pairs):
        if kind == sub:
            ex.sets = max(2, int(ex.sets or 3) - 1)
            break


def _apply_60_focus_sets(
    mains: list[PlanExerciseIn],
    pairs: list[tuple[str, Exercise]],
    role: str,
    focus_keys: list[str] | None,
    *,
    experience_level: int | None = None,
) -> None:
    extra = extra_focus_kind(role, normalize_focus_areas(focus_keys))
    if not extra:
        return
    sets_max = _sets_max_for_level(experience_level)
    if role == "push":
        if extra == "chest":
            _shift_one_set(mains, pairs, add="chest", sub="shoulder", sets_max=sets_max)
        elif extra == "shoulder":
            _shift_one_set(mains, pairs, add="shoulder", sub="chest", sets_max=sets_max)
        return
    if role == "pull":
        if extra == "back":
            _shift_one_set(mains, pairs, add="back", sub="rear", sets_max=sets_max)
        elif extra == "rear":
            _shift_one_set(mains, pairs, add="rear", sub="back", sets_max=sets_max)
        return
    if role != "upper":
        return
    for ex, (kind, _row) in zip(mains, pairs):
        if kind == extra:
            cur = int(ex.sets or 3)
            if cur < sets_max:
                ex.sets = cur + 1
            break
    else:
        return
    for ex, (kind, _row) in zip(mains, pairs):
        if kind not in {extra, "abs", "abs_extra", "cardio", "bw"}:
            ex.sets = max(2, int(ex.sets or 3) - 1)
            break


def apply_kit_mains(
    day: PlanDayIn,
    db: Session,
    *,
    equipment_slugs: list[str] | None,
    fitness_baseline: dict[str, Any] | None,
    experience_level: int | None,
    session_minutes: int | None,
    meta_by_id: dict[int, Any] | None,
    home_session: bool,
    challenge_session: bool = False,
    variety_index: int | None = None,
    focus_keys: list[str] | None = None,
    phase_index: int | None = None,
    week_day_index: int | None = None,
) -> None:
    """Overwrite the mains that must follow the kit. Other sections stay put."""
    if not home_session:
        return
    role = normalize_split_role(getattr(day, "split_role", None))
    kit = infer_test_kit(fitness_baseline, equipment_slugs)
    challenge_kit = bool(challenge_session) and kit in {"dumbbell", "band", "bar_rings"}
    phase_i: int | None = None
    if challenge_kit:
        try:
            phase_i = 0 if phase_index is None else max(0, min(2, int(phase_index)))
        except (TypeError, ValueError):
            phase_i = 0
    day_number = getattr(day, "day_number", None)
    month = phase_i if phase_i is not None else _month_index(day_number)
    cardio_month = _month_index(day_number)
    if phase_i is not None:
        slots = challenge_strength_slots(role, phase_i)
    else:
        slots = resistance_slot_count(session_minutes)
    slot_index = (
        _variety_index(day_number, variety_index)
        if kit in {"dumbbell", "bar_rings"}
        else month
    )
    from app.services.schedule_spec_master import snap_session_minutes

    minutes = snap_session_minutes(int(session_minutes or 45))
    if kit == "bar_rings":
        slot_cands = bar_rings_slots(
            role,
            pushups_max=_baseline_int(fitness_baseline, "pushups_max"),
            pullups_max=_baseline_int(fitness_baseline, "pullups_max"),
            experience_level=experience_level,
            slots=slots,
            variety=slot_index,
            focus_keys=focus_keys,
            phase_index=phase_i,
        )
        kinds = kit_kind_list(
            "bar_rings", role, slots, focus_keys, phase_index=phase_i
        )
        planned = (
            list(zip(kinds, slot_cands))
            if len(kinds) == len(slot_cands)
            else [("main", candidates) for candidates in slot_cands]
        )
    else:
        planned = gear_plan(
            kit, role, slots, slot_index, focus_keys=focus_keys, phase_index=phase_i
        )
    if not planned:
        return
    mains = [ex for ex in day.exercises if str(getattr(ex, "section", "") or "") == "main"]
    template = mains[0] if mains else PlanExerciseIn(exercise_id=1, sets=3, reps="8-12", rest_seconds=90)
    pairs: list[tuple[str, Exercise]] = []
    occupied = {
        int(ex.exercise_id)
        for ex in day.exercises
        if getattr(ex, "exercise_id", None)
        and str(getattr(ex, "section", "") or "main").strip().lower()
        not in {"main", "exercises", "warmup", "primer"}
    }
    for kind, candidates in planned:
        row = _lookup_named(
            db, candidates, occupied | {int(item.id) for _k, item in pairs}
        )
        if row is None:
            continue
        pairs.append((kind, row))
        occupied.add(int(row.id))
        _remember(db, row, meta_by_id)
    if not pairs:
        return
    challenge_db = bool(challenge_session) and kit == "dumbbell"
    challenge_rings = bool(challenge_session) and kit == "bar_rings"
    challenge_band = bool(challenge_session) and kit == "band"
    day_i = week_day_index
    if day_i is None:
        try:
            day_i = max(0, int(day_number or 1) - 1)
        except (TypeError, ValueError):
            day_i = 0
    finisher = challenge_finisher_kind(phase_i, day_i) if challenge_kit else None
    want_cardio = False
    want_abs = False
    if challenge_kit:
        want_cardio = finisher in {"both", "cardio"}
        want_abs = finisher in {"both", "abs"}
    elif kit == "dumbbell" and minutes >= 60:
        _add_cardio_replacement(
            db,
            pairs,
            kit=kit,
            month=month,
            day_number=day_number,
            meta_by_id=meta_by_id,
        )
    if want_abs or (not challenge_kit and minutes >= 60):
        _inject_abs_pairs(
            db,
            pairs,
            occupied,
            day_number=int(day_number or month or 1),
            meta_by_id=meta_by_id,
            extra=not (challenge_kit and finisher == "abs"),
        )
    compound_reps, accessory_reps = _db_rep_bands(role, fitness_baseline)
    sets_cap = _sets_max_for_level(experience_level)
    new_mains = []
    for index, (kind, row) in enumerate(pairs):
        ex = _clone_main(template, int(row.id))
        ex.set_prescriptions = None
        if kind == "abs":
            _dose_abs(ex, row, fitness_baseline, compact=True)
        elif kind == "abs_extra":
            _dose_abs_extra(ex, row)
        else:
            ex.sets = min(sets_cap, 3)
            if kit == "dumbbell":
                ex.reps = compound_reps if index == 0 else accessory_reps
        if minutes <= 45 and kind not in {"abs", "abs_extra", "bw"}:
            heavy = kind in {"back", "legs", "hinge", "quad", "sumo"} or (
                kind in {"chest", "main"} and index == 0
            )
            ex.rest_seconds = 120 if heavy else 90
        new_mains.append(ex)
    if phase_i is not None:
        _stamp_challenge_test_lift_sets(
            new_mains, pairs, phase_index=phase_i, sets_cap=sets_cap
        )
    scripted = sum(1 for kind, _row in pairs if kind not in {"abs", "abs_extra", "bw"})
    if kit in {"band", "dumbbell"} and not challenge_db and not challenge_band and len(mains) > scripted:
        for ex, (kind, _row) in zip(new_mains, pairs):
            if kind in {"abs", "abs_extra"}:
                continue
            ex.sets = min(sets_cap, int(ex.sets or 3) + 1)
    if minutes >= 60 and not challenge_kit:
        _apply_60_focus_sets(
            new_mains,
            pairs,
            role,
            focus_keys,
            experience_level=experience_level,
        )
    _splice_mains(day, new_mains)
    drop_cardio = (
        ((challenge_db or challenge_rings or challenge_band) and not want_cardio)
        or (
            not challenge_db
            and not challenge_rings
            and not challenge_band
            and kit in {"band", "dumbbell"}
            and minutes >= 60
        )
    )
    if drop_cardio:
        _strip_cardio(day)
    if (challenge_db or challenge_rings or challenge_band) and want_cardio:
        _strip_cardio(day)
        cardio = _lookup_named(
            db,
            _cardio_pool(cardio_month),
            occupied | {int(item.id) for _k, item in pairs},
        )
        if cardio is not None:
            _remember(db, cardio, meta_by_id)
            _insert_cardio(
                day,
                _dose_cardio(cardio, minutes, extra_minutes=2 if minutes >= 60 else 0),
            )
    _dedupe_day_exercise_ids(day)
    for i, ex in enumerate(day.exercises, start=1):
        ex.sort_order = i


def rotate_db_accessories_across_days(
    days: list[PlanDayIn],
    db: Session,
    *,
    equipment_slugs: list[str] | None,
    fitness_baseline: dict[str, Any] | None,
    session_minutes: int | None,
    meta_by_id: dict[int, Any] | None,
    home_session: bool,
) -> None:
    """Keep test lifts; walk accessory pools by same-role session across the whole plan."""
    if not home_session or not days:
        return
    kit = infer_test_kit(fitness_baseline, equipment_slugs)
    if kit not in {"dumbbell", "bar_rings"}:
        return
    slots = resistance_slot_count(session_minutes)
    role_seen: dict[str, int] = {}
    for day in days:
        if not getattr(day, "exercises", None):
            continue
        role = normalize_split_role(getattr(day, "split_role", None))
        variety = role_seen.get(role, 0)
        mains = [
            ex
            for ex in day.exercises
            if str(getattr(ex, "section", "") or "") == "main"
            and not _is_core_fill_ex(ex, meta_by_id)
        ]
        if not mains:
            continue
        planned_slots = min(slots, len(mains))
        if kit == "bar_rings":
            planned = [
                ("main", candidates)
                for candidates in bar_rings_slots(
                    role,
                    pushups_max=_baseline_int(fitness_baseline, "pushups_max"),
                    pullups_max=_baseline_int(fitness_baseline, "pullups_max"),
                    experience_level=None,
                    slots=planned_slots,
                    variety=variety,
                )
            ]
        else:
            planned = gear_plan(kit, role, planned_slots, variety)
        if not planned:
            continue
        keep = len(kit_anchor_slots(kit, role))
        used = {int(ex.exercise_id) for ex in day.exercises if getattr(ex, "exercise_id", None)}
        for index, (_kind, candidates) in enumerate(planned):
            if index < keep or index >= len(mains):
                continue
            ex = mains[index]
            current = int(ex.exercise_id)
            row = _lookup_named(db, candidates, used - {current})
            if row is None:
                continue
            if current != int(row.id):
                used.discard(current)
                ex.exercise_id = int(row.id)
                ex.set_prescriptions = None
            used.add(int(row.id))
            _remember(db, row, meta_by_id)
        _dedupe_day_exercise_ids(day)
        role_seen[role] = role_seen.get(role, 0) + 1


def _is_timed_main_reps(reps: Any) -> bool:
    blob = str(reps or "").lower()
    return any(tok in blob for tok in ("phút", "phut", "giây", "giay", "min", "sec"))


def _db_rep_bands(
    role: str, baseline: dict[str, Any] | None
) -> tuple[str, str]:
    key = {
        "push": "db_press_reps",
        "upper": "db_press_reps",
        "pull": "db_row_reps",
        "legs": "goblet_reps",
        "lower": "goblet_reps",
    }.get(role, "db_press_reps")
    n = _baseline_int(baseline, key)
    if n is None and role in {"legs", "lower"}:
        n = _baseline_int(baseline, "squats_max")
    compound = "4-8" if n is not None and n < 10 else "8-12"
    accessory = "8-12" if compound == "4-8" else "12-16"
    return compound, accessory


def _abs_pool(month: int) -> list[tuple[str, str]]:
    return _ABS_SITUP if int(month) % 2 else _ABS_PLANK


def _rings_abs_pool(month: int) -> list[tuple[str, str]]:
    return _pick_month(_RING_ABS, month)


def _cardio_pool(month: int) -> list[tuple[str, str]]:
    options = [*_CARDIO_INTERVAL, *_CARDIO_RUN]
    return _cycle(options, month)


def _append_named(
    db: Session,
    pairs: list[tuple[str, Exercise]],
    candidates: list[tuple[str, str]],
    kind: str,
    meta_by_id: dict[int, Any] | None,
) -> None:
    row = _lookup_named(db, candidates, {int(item.id) for _k, item in pairs})
    if row is None:
        return
    pairs.append((kind, row))
    _remember(db, row, meta_by_id)


def _is_extra_abs_name(row: Exercise) -> bool:
    blob = f"{getattr(row, 'name_en', '') or ''} {getattr(row, 'name_vi', '') or ''}".lower()
    return any(
        token in blob
        for token in (
            "dead bug",
            "v-up",
            "russian twist",
            "side plank",
            "nghiêng",
            "nghieng",
            "situp",
            "sit-up",
        )
    )


def _inject_abs_pairs(
    db: Session,
    pairs: list[tuple[str, Exercise]],
    occupied: set[int],
    *,
    day_number: int,
    meta_by_id: dict[int, Any] | None,
    extra: bool = True,
) -> None:
    taken = set(occupied) | {int(item.id) for _k, item in pairs}
    has_plank = any(_is_plank_name(row) for _k, row in pairs)
    has_extra = any(
        (kind == "abs_extra" or (kind == "abs" and not _is_plank_name(row)) or _is_extra_abs_name(row))
        and not _is_plank_name(row)
        for kind, row in pairs
    )
    if not has_plank:
        plank = _lookup_named(db, list(_FRONT_PLANK), taken)
        if plank is not None:
            insert_at = next(
                (
                    i
                    for i, (kind, row) in enumerate(pairs)
                    if kind in {"abs", "abs_extra"} or _is_extra_abs_name(row)
                ),
                len(pairs),
            )
            pairs.insert(insert_at, ("abs", plank))
            occupied.add(int(plank.id))
            taken.add(int(plank.id))
            _remember(db, plank, meta_by_id)
    if has_extra or not extra:
        return
    extra_row = _lookup_named(db, _cycle(_ABS_EXTRA, int(day_number or 1)), taken)
    if extra_row is None:
        return
    pairs.append(("abs_extra", extra_row))
    occupied.add(int(extra_row.id))
    _remember(db, extra_row, meta_by_id)


def _plank_hold_reps(baseline: dict[str, Any] | None) -> str:
    from app.services.workout_generation.assemble import plank_finisher_reps

    return plank_finisher_reps(baseline)


def _is_plank_name(row: Exercise | None, *, extra: str = "") -> bool:
    blob = f"{getattr(row, 'name_en', '') or ''} {getattr(row, 'name_vi', '') or ''} {extra}".lower()
    if "side" in blob or "bên" in blob or "nghiêng" in blob:
        return False
    return "plank" in blob


def _is_core_fill_ex(ex: PlanExerciseIn, meta_by_id: dict[int, Any] | None) -> bool:
    blob = str(getattr(ex, "reps", "") or "").lower()
    if "giây" in blob or "giay" in blob:
        return True
    meta = (meta_by_id or {}).get(int(ex.exercise_id or 0))
    name = ""
    slug = ""
    if meta is not None:
        if isinstance(meta, dict):
            name = f"{meta.get('name_en') or ''} {meta.get('name_vi') or ''}"
            slug = str(meta.get("muscle_slug") or "")
        else:
            name = f"{getattr(meta, 'name_en', '') or ''} {getattr(meta, 'name_vi', '') or ''}"
            slug = str(getattr(meta, "muscle_slug", "") or "")
    low = name.lower()
    if "plank" in low or "dead bug" in low or "v-up" in low or "russian twist" in low:
        return True
    return slug in {"core", "co-bung", "abs", "waist", "bung"}


def _dedupe_day_exercise_ids(day: PlanDayIn) -> None:
    """Drop duplicate mains/cardio ids. Keep warmup primers that copy the first main."""
    seen_main: set[int] = set()
    seen_other: set[int] = set()
    kept: list[Any] = []
    for ex in day.exercises:
        section = str(getattr(ex, "section", "") or "main").strip().lower()
        try:
            eid = int(ex.exercise_id)
        except (TypeError, ValueError):
            kept.append(ex)
            continue
        if section in {"warmup", "primer"}:
            kept.append(ex)
            continue
        if section in {"main", "exercises"}:
            if eid in seen_main:
                continue
            seen_main.add(eid)
        else:
            if eid in seen_other or eid in seen_main:
                continue
            seen_other.add(eid)
        kept.append(ex)
    day.exercises = kept


def _stamp_hold(ex: PlanExerciseIn, *, sets: int, reps: str) -> None:
    from app.services.workout_generation.coach_notes import hold_note_vi

    ex.sets = sets
    ex.reps = reps
    ex.notes_vi = hold_note_vi(reps)


def _stamp_rep_abs(ex: PlanExerciseIn, row: Exercise, *, sets: int, reps: str) -> None:
    from app.services.workout_generation.coach_notes import load_kind_for_item, working_note_vi

    ex.sets = sets
    ex.reps = reps
    kind = load_kind_for_item(row)
    ex.notes_vi = working_note_vi(reps, kind=kind, include_progress=kind == "loaded")


def _dose_abs_extra(ex: PlanExerciseIn, row: Exercise) -> None:
    blob = f"{row.name_en or ''} {row.name_vi or ''}".lower()
    if "side plank" in blob or "nghiêng" in blob:
        _stamp_hold(ex, sets=2, reps="20-30 giây")
        return
    _stamp_rep_abs(ex, row, sets=2, reps="12-15")


def _is_run_name(row: Exercise) -> bool:
    blob = f"{row.name_en or ''} {row.name_vi or ''}".lower()
    return "trail run" in blob or "chạy bền" in blob or "chay ben" in blob


def _dose_abs(
    ex: PlanExerciseIn,
    row: Exercise,
    baseline: dict[str, Any] | None,
    *,
    compact: bool,
) -> None:
    if _is_plank_name(row):
        _ = compact
        _stamp_hold(ex, sets=1, reps=_plank_hold_reps(baseline))
        return
    _stamp_rep_abs(ex, row, sets=2, reps="12-15")


def _dose_cardio(
    row: Exercise, minutes: int, *, extra_minutes: int = 0
) -> PlanExerciseIn:
    if _is_run_name(row):
        hold = 6 if minutes <= 45 else 10
        hold += max(0, int(extra_minutes))
        return PlanExerciseIn(
            exercise_id=int(row.id),
            sets=1,
            reps=f"{hold} phút",
            rest_seconds=60,
            section="cardio",
        )
    sets = 2 if minutes <= 45 else 3
    if extra_minutes:
        sets += 1
    return PlanExerciseIn(
        exercise_id=int(row.id),
        sets=sets,
        reps="20-30 giây",
        rest_seconds=60,
        section="cardio",
    )


def _strip_cardio(day: PlanDayIn) -> None:
    day.exercises = [
        ex for ex in day.exercises if str(getattr(ex, "section", "") or "") != "cardio"
    ]


def _insert_cardio(day: PlanDayIn, cardio: PlanExerciseIn) -> None:
    out: list[Any] = []
    placed = False
    last_main = max(
        (i for i, ex in enumerate(day.exercises) if str(getattr(ex, "section", "") or "") == "main"),
        default=-1,
    )
    for i, ex in enumerate(day.exercises):
        out.append(ex)
        if i == last_main:
            out.append(cardio)
            placed = True
    if not placed:
        out.append(cardio)
    day.exercises = out


def _add_cardio_replacement(
    db: Session,
    pairs: list[tuple[str, Exercise]],
    *,
    kit: str,
    month: int,
    day_number: int | None,
    meta_by_id: dict[int, Any] | None,
) -> None:
    """Trade the cardio block for one ab set, or one extra chest or shoulder lift."""
    kind = ("abs", "chest", "shoulder")[(max(1, int(day_number or 1)) - 1) % 3]
    if kit == "band":
        chest, shoulder = _BAND_FLY, _BAND_FRONT
    else:
        chest, shoulder = _DB_FLY, _DB_FRONT
    pool = {"abs": _ABS_EXTRA, "chest": chest, "shoulder": shoulder}[kind]
    used = {int(row.id) for _slot, row in pairs}
    row = _lookup_named(db, _cycle(pool, month), used)
    if row is None:
        return
    _place_extra(pairs, kind, row)
    _remember(db, row, meta_by_id)
