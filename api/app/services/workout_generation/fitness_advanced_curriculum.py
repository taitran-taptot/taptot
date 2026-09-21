"""Hardcoded 12-week advanced fitness challenge (male/female × 4–6 sessions)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import BadRequestError
from app.models.entities import Exercise
from app.schemas.plans import CreatePlanRequest, PlanDayIn, PlanExerciseIn
from app.services.plan_service import PlanService
from app.services.workout_generation.bmi import build_familiarization_weight_goal
from app.services.workout_generation.familiarization_curriculum import (
    _attach_familiarization_meals,
    expand_familiarization_weeks,
)

WEEKS = 12
DAYS_PER_WEEK = 7
DURATION_DAYS = WEEKS * DAYS_PER_WEEK
MIN_SESSIONS = 4
MAX_SESSIONS = 6
SESSION_MINUTES = 55
FITNESS_TEST_HREF = "/kiemtratheluc"

STANDARDS = {
    "male": {
        "gioi": {"push": 50, "pull": 18, "squat": 70, "plank": 210, "run_m": 2400},
        "kha": {"push": 40, "pull": 15, "squat": 60, "plank": 180, "run_m": 2200},
        "dat": {"push": 30, "pull": 12, "squat": 50, "plank": 150, "run_m": 2000},
    },
    "female": {
        "gioi": {"push": 20, "pull": 8, "squat": 55, "plank": 180, "run_m": 2100},
        "kha": {"push": 15, "pull": 6, "squat": 48, "plank": 150, "run_m": 1900},
        "dat": {"push": 10, "pull": 4, "squat": 40, "plank": 120, "run_m": 1700},
    },
}


def normalize_fitness_advanced_offer(raw: Any) -> str:
    key = str(raw or "").strip().lower()
    if key in {"fitness_advanced", "fitness_soldier"}:
        return "fitness_advanced"
    return key


def clamp_sessions(raw: Any) -> int:
    try:
        value = int(raw)
    except (TypeError, ValueError):
        value = MIN_SESSIONS
    return max(MIN_SESSIONS, min(MAX_SESSIONS, value))


def _gender(raw: Any) -> str:
    return "female" if str(raw or "").strip().lower() == "female" else "male"


def _blob(ex: Exercise) -> str:
    return f"{ex.name_vi or ''} {ex.name_en or ''}".lower()


def _has(blob: str, needles: tuple[str, ...]) -> bool:
    return any(n in blob for n in needles)


def _pick(
    rows: list[Exercise],
    *,
    require: tuple[str, ...],
    reject: tuple[str, ...] = (),
) -> Exercise | None:
    for ex in rows:
        blob = _blob(ex)
        if reject and _has(blob, reject):
            continue
        if _has(blob, require):
            return ex
    return None


def resolve_catalog(db: Session) -> dict[str, Exercise]:
    rows = (
        db.query(Exercise)
        .filter(Exercise.is_active.is_(True))
        .order_by(Exercise.id.asc())
        .all()
    )
    catalog: dict[str, Exercise] = {}
    catalog["push"] = _pick(
        rows,
        require=("chống đẩy", "chong day", "push-up", "push up", "pushup"),
        reject=("wall", "tường", "tuong", "knee", "quỳ", "quy", "incline", "kê tay", "ke tay"),
    ) or _pick(rows, require=("push-up", "push up", "chống đẩy", "chong day"))
    catalog["incline_push"] = _pick(
        rows,
        require=("incline", "kê tay", "ke tay", "elevated push"),
        reject=("decline",),
    )
    catalog["pull"] = _pick(
        rows,
        require=("pull-up", "pull up", "pullup", "kéo lên", "keo len", "kéo xà"),
        reject=("assisted", "band", "dây", "1/3", "scapular", "âm", "negative"),
    )
    catalog["chin"] = _pick(rows, require=("chin-up", "chin up", "chinup"))
    catalog["negative_pull"] = _pick(
        rows, require=("negative pull", "pha âm", "pha am", "kéo xà pha")
    )
    catalog["row"] = _pick(
        rows,
        require=("inverted row", "kéo người nằm", "keo nguoi nam", "australian"),
    )
    catalog["squat"] = _pick(
        rows,
        require=("bodyweight squat", "squat thể trọng", "squat the trong", "ngồi xổm"),
        reject=("jump", "goblet", "barbell", "bulgarian", "split"),
    ) or _pick(rows, require=("squat",), reject=("jump", "goblet", "barbell", "hack", "machine"))
    catalog["plank"] = _pick(
        rows,
        require=("plank",),
        reject=("side", "bên", "ben", "knee", "quỳ"),
    ) or _pick(rows, require=("plank",))
    catalog["run_easy"] = _pick(
        rows,
        require=("chạy bền", "chay ben", "trail run", "easy continuous", "chạy nhẹ"),
    ) or _pick(rows, require=("chạy", "chay", "run", "jog"))
    catalog["run_tempo"] = _pick(rows, require=("tempo-run", "tempo run", "chạy tempo"))
    catalog["run_interval"] = _pick(
        rows, require=("running-interval", "chạy ngắt", "interval")
    )
    catalog["lunge"] = _pick(
        rows,
        require=("lunge", "bước lunge"),
        reject=("barbell", "dumbbell", "bulgarian"),
    )
    missing = [key for key in ("push", "pull", "squat", "plank", "run_easy") if catalog.get(key) is None]
    if missing:
        raise BadRequestError(
            "Kho bài tập thiếu bài cho thử thách thể lực nâng cao: " + ", ".join(missing)
        )
    return catalog


def _ex(
    catalog: dict[str, Exercise],
    key: str,
    sets: int,
    reps: str,
    *,
    section: str = "main",
    rest: int = 90,
    notes: str | None = None,
    fallback: str | None = None,
) -> PlanExerciseIn | None:
    item = catalog.get(key) or (catalog.get(fallback) if fallback else None)
    if item is None:
        return None
    return PlanExerciseIn(
        exercise_id=int(item.id),
        sets=sets,
        reps=reps,
        rest_seconds=rest,
        section=section,  # type: ignore[arg-type]
        notes_vi=notes,
    )


def _block(week: int) -> int:
    if week <= 4:
        return 1
    if week <= 8:
        return 2
    return 3


def _session_letters(sessions: int) -> tuple[str, ...]:
    base = ("A", "B", "C", "D")
    if sessions >= 5:
        base = base + ("E",)
    if sessions >= 6:
        base = base + ("F",)
    return base


def _male_session(
    catalog: dict[str, Exercise], week: int, letter: str, *, test_day: bool
) -> list[PlanExerciseIn]:
    if test_day:
        return []
    block = _block(week)
    deload = week == 12
    scale = 0.6 if deload else 1.0
    out: list[PlanExerciseIn] = []

    def add(key: str, sets: int, reps: str, **kwargs: Any) -> None:
        item = _ex(catalog, key, max(2, int(round(sets * scale))), reps, **kwargs)
        if item:
            out.append(item)

    if letter == "A":
        if block == 1:
            add("push", 5, "8")
            add("plank", 4, "45 giây", section="main", rest=60)
            add("incline_push", 3, "8", fallback="push", notes="Phụ đẩy — còn dư 2–3 cái")
        elif block == 2:
            add("push", 5, "12")
            add("plank", 4, "70 giây", rest=60)
        else:
            add("push", 5, "18–22")
            add("plank", 3, "90–110 giây", rest=60)
    elif letter == "B":
        if block == 1:
            add("run_easy", 1, "30 phút", section="cardio", rest=0, notes="Nhịp nói được câu")
        elif block == 2:
            if week % 2 == 0:
                add("run_tempo", 1, "20 phút", section="cardio", rest=0, fallback="run_easy")
            else:
                add("run_easy", 1, "35–40 phút", section="cardio", rest=0)
        else:
            add("run_easy", 1, "40 phút", section="cardio", rest=0)
    elif letter == "C":
        if block == 1:
            add("pull", 6, "3", notes="Còn dư 2–3. Chưa vững thì dùng kéo âm / chin-up.")
            add("squat", 4, "15")
            add("row", 3, "8", fallback="pull")
        elif block == 2:
            add("pull", 5, "5")
            add("squat", 4, "20")
        else:
            add("pull", 5, "6–8")
            add("squat", 5, "25")
    elif letter == "D":
        if week == 8:
            add(
                "run_easy",
                1,
                "10 phút",
                section="cardio",
                rest=0,
                notes="Test 10 phút trên lịch — ghi mét. Không dùng camera.",
            )
        elif block == 1:
            add(
                "run_interval",
                8,
                "200 m jog / đi 90 giây",
                section="cardio",
                rest=90,
                fallback="run_easy",
            )
            add("run_easy", 1, "10 phút dễ", section="cardio", rest=0)
        elif block == 2:
            add(
                "run_interval",
                6,
                "400 m / đi 2 phút",
                section="cardio",
                rest=120,
                fallback="run_easy",
            )
        else:
            add(
                "run_interval",
                5,
                "800 m hoặc tempo 15 phút",
                section="cardio",
                rest=120,
                fallback="run_tempo",
            )
    elif letter == "E":
        if week % 2 == 1:
            add("run_easy", 1, "25 phút", section="cardio", rest=0)
        else:
            add("pull", 4, "3", notes="Volume nhẹ, còn dư 3 cái")
            add("plank", 3, "40 giây", rest=60)
    elif letter == "F":
        add("push", 4, "6", notes="Volume nhẹ, không max")
        add("plank", 3, "40 giây", rest=60)
    return out


def _female_session(
    catalog: dict[str, Exercise], week: int, letter: str, *, test_day: bool
) -> list[PlanExerciseIn]:
    if test_day:
        return []
    block = _block(week)
    deload = week == 12
    scale = 0.6 if deload else 1.0
    out: list[PlanExerciseIn] = []

    def add(key: str, sets: int, reps: str, **kwargs: Any) -> None:
        item = _ex(catalog, key, max(2, int(round(sets * scale))), reps, **kwargs)
        if item:
            out.append(item)

    push_key = "incline_push" if block == 1 and catalog.get("incline_push") else "push"
    pull_key = "chin" if catalog.get("chin") and block == 1 else "pull"
    if letter == "A":
        if block == 1:
            add(push_key, 5, "4", fallback="push", notes="Sàn nếu form vững; kê tay thấp nếu gãy.")
            add("plank", 4, "40 giây", rest=60)
        elif block == 2:
            add("push", 5, "6")
            add("plank", 4, "60 giây", rest=60)
        else:
            add("push", 5, "8")
            add("plank", 3, "80–100 giây", rest=60)
    elif letter == "B":
        if block == 1:
            add("run_easy", 1, "28 phút chạy/đi", section="cardio", rest=0)
        elif block == 2:
            if week % 2 == 0:
                add("run_tempo", 1, "15 phút", section="cardio", rest=0, fallback="run_easy")
            else:
                add("run_easy", 1, "32–35 phút", section="cardio", rest=0)
        else:
            add("run_easy", 1, "35 phút", section="cardio", rest=0)
    elif letter == "C":
        if block == 1:
            add(pull_key, 8, "2", fallback="pull", notes="Chin-up hoặc pha âm 5 giây.")
            add("row", 3, "8", fallback="pull")
            add("squat", 4, "12")
        elif block == 2:
            add("pull", 6, "3")
            add("squat", 4, "18")
        else:
            add("pull", 5, "4")
            add("squat", 5, "20")
    elif letter == "D":
        if week == 8:
            add(
                "run_easy",
                1,
                "10 phút",
                section="cardio",
                rest=0,
                notes="Test 10 phút trên lịch — ghi mét. Không dùng camera.",
            )
        elif block == 1:
            add(
                "run_interval",
                6,
                "200 m dễ / đi 90 giây",
                section="cardio",
                rest=90,
                fallback="run_easy",
            )
        elif block == 2:
            add(
                "run_interval",
                5,
                "400 m",
                section="cardio",
                rest=120,
                fallback="run_easy",
            )
        else:
            add(
                "run_interval",
                4,
                "600–800 m",
                section="cardio",
                rest=120,
                fallback="run_easy",
            )
    elif letter == "E":
        if week % 2 == 1:
            add("run_easy", 1, "25 phút", section="cardio", rest=0)
        else:
            add("pull", 4, "2", notes="Volume nhẹ")
            add("plank", 3, "30 giây", rest=60)
    elif letter == "F":
        add("push", 4, "4", notes="Volume nhẹ, không max")
        add("plank", 3, "30 giây", rest=60)
    return out


_TITLES = {
    "A": "Đẩy + plank",
    "B": "Chạy dễ / tempo",
    "C": "Kéo xà + squat",
    "D": "Chạy chất lượng",
    "E": "Volume phụ",
    "F": "Đẩy nhẹ + plank",
}


def build_fitness_advanced_week_templates(
    db: Session,
    payload: dict[str, Any],
    *,
    catalog: dict[str, Exercise] | None = None,
) -> list[list[PlanDayIn]]:
    gender = _gender(payload.get("gender"))
    sessions = clamp_sessions(payload.get("sessions_per_week"))
    letters = _session_letters(sessions)
    resolved = catalog or resolve_catalog(db)
    builder = _female_session if gender == "female" else _male_session
    templates: list[list[PlanDayIn]] = []
    day_no = 1
    for week in range(1, WEEKS + 1):
        week_days: list[PlanDayIn] = []
        for slot in range(1, DAYS_PER_WEEK + 1):
            is_last = week == WEEKS and slot == DAYS_PER_WEEK
            letter = letters[slot - 1] if slot <= len(letters) else None
            if is_last:
                week_days.append(
                    PlanDayIn(
                        day_number=day_no,
                        title_vi=f"Tuần {week} · Tốt nghiệp",
                        split_role="test",
                        notes_vi=(
                            "Ngày cuối: test chính thức 5 môn bằng camera. "
                            "Nghỉ 2 phút giữa các bài. Bấm Bắt đầu test chính thức."
                        ),
                        exercises=[],
                    )
                )
            elif letter is None:
                week_days.append(
                    PlanDayIn(
                        day_number=day_no,
                        title_vi=f"Tuần {week} · Nghỉ",
                        split_role="recovery",
                        notes_vi="Nghỉ chủ động — đi bộ nhẹ 15–20 phút nếu muốn.",
                        exercises=[],
                    )
                )
            else:
                deload_note = " Giảm ~40% so với tuần 11." if week == 12 else ""
                week_days.append(
                    PlanDayIn(
                        day_number=day_no,
                        title_vi=f"Tuần {week} · {_TITLES[letter]}",
                        split_role=letter.lower(),
                        notes_vi=(
                            f"Còn dư 2–3 cái (khối 1) hoặc 1–2 cái (khối 2–3).{deload_note}"
                        ),
                        exercises=builder(
                            resolved, week, letter, test_day=False
                        ),
                    )
                )
            day_no += 1
        templates.append(week_days)
    return templates


def generate_fitness_advanced_workout(
    db: Session,
    user_id: str | None,
    payload: dict[str, Any],
    *,
    persist: bool = True,
) -> dict[str, Any]:
    gender = _gender(payload.get("gender"))
    sessions = clamp_sessions(payload.get("sessions_per_week"))
    templates = build_fitness_advanced_week_templates(db, payload)
    weight_goal = build_familiarization_weight_goal(payload)
    templates, meal_result = _attach_familiarization_meals(
        db, payload, templates, weight_goal
    )
    first_week = templates[0]
    dat = STANDARDS[gender]["dat"]
    stamp = datetime.now().strftime("%d/%m/%Y %H:%M")
    gender_href = f"{FITNESS_TEST_HREF}?gender={gender}"
    insights: dict[str, Any] = {
        "overview": {
            "schedule_vi": (
                f"12 tuần · {sessions} buổi/tuần · khoảng {SESSION_MINUTES} phút/buổi. "
                "Cùng 5 bài: chống đẩy, kéo xà, squat, plank, chạy 10 phút."
            ),
            "summary_vi": (
                "Thử thách thể lực nâng cao — lịch cố định theo giới, "
                f"mốc Đạt: chống {dat['push']}, xà {dat['pull']}, squat {dat['squat']}, "
                f"plank {dat['plank'] // 60}:{dat['plank'] % 60:02d}, "
                f"chạy 10 phút {dat['run_m'] / 1000:.1f} km."
            ),
            "periodization_vi": (
                "Tuần 1–4 volume (còn dư 2–3). Tuần 5–8 mật độ. "
                "Tuần 9–11 gần max. Tuần 8 chạy 10 phút trên lịch. "
                "Tuần 12 giảm tải rồi kiểm tra camera."
            ),
            "nutrition_vi": (
                "Đạm 1,6–2,0 g/kg, ngủ 7–8,5 tiếng. Ngày nghỉ đi bộ nhẹ 15–20 phút."
            ),
            "mission_vi": (
                "Xuất phát từ cửa ra Nền tảng nâng cao. Pass = đủ 5/5 Đạt."
            ),
            "outcome_vi": (
                f"Nam Đạt 30/12/50/2:30/2,0 km. Nữ Đạt 10/4/40/2:00/1,7 km."
                if gender == "male"
                else "Nữ Đạt 10 chống / 4 xà / 40 squat / plank 2:00 / chạy 1,7 km / 10 phút."
            ),
        },
        "advice_vi": [
            "Form trước số lần. Dừng khi đau nhói, chóng mặt hoặc khó thở bất thường.",
            "Cần xà đơn. Chạy ngoài trời hoặc máy chạy.",
            "Ngày cuối tuần 12 là test chính thức — nghỉ 2 phút giữa các bài camera.",
        ],
        "generator": "fitness_advanced_rules_v1",
        "used_openai": False,
        "used_openai_pick": False,
        "challenge_100_days": False,
        "generation_mode": "fitness_advanced",
        "challenge_kind": "fitness_advanced",
        "duration_days": DURATION_DAYS,
        "duration_weeks": WEEKS,
        "sessions_per_week": sessions,
        "session_minutes": SESSION_MINUTES,
        "fitness_test_href": gender_href,
        "standards": STANDARDS[gender],
        "familiarization_week_templates": [
            [day.model_dump() for day in week] for week in templates
        ],
        "weight_goal": weight_goal,
    }
    if meal_result is not None:
        if meal_result.warning_vi:
            insights["meal_warning_vi"] = meal_result.warning_vi
        if meal_result.rest_day_template and meal_result.schedule:
            rest = meal_result.schedule.rest
            insights["rest_day_nutrition"] = {
                "target_calories": rest.target_calories,
                "protein_g": rest.protein_g,
                "carbs_g": rest.carbs_g,
                "fat_g": rest.fat_g,
            }
            insights["rest_day_meals"] = [
                {
                    "food_id": item.food_id,
                    "meal_type": item.meal_type,
                    "servings": item.servings,
                    "notes_vi": item.notes_vi,
                }
                for item in meal_result.rest_day_template.meals
            ]
        insights["nutrition"] = (
            {
                "tdee": (weight_goal or {}).get("tdee"),
                "target_calories": (weight_goal or {}).get("daily_kcal"),
                "protein_g": (weight_goal or {}).get("protein_g"),
            }
            if weight_goal
            else None
        )
    start_date = datetime.now(UTC).date()
    create = CreatePlanRequest(
        title_vi=f"Thể lực nâng cao {stamp}",
        description_vi=str(insights["overview"]["summary_vi"]),
        start_date=start_date,
        end_date=start_date + timedelta(days=DURATION_DAYS - 1),
        source="ai",
        duration_weeks=WEEKS,
        experience_level=min(max(int(payload.get("experience_level") or 3), 1), 3),
        strength_tier="strong",
        challenge_100_days=False,
        days=first_week,
    )
    settings = get_settings()
    usage = {
        "month": "",
        "generation_count": 0,
        "qa_message_count": 0,
        "limit": None,
        "remaining": None,
        "unlimited": True,
        "price_vnd": 0,
        "model": settings.openai_model,
        "openai_configured": bool((settings.openai_api_key or "").strip()),
    }
    if not persist:
        return {
            "plan": None,
            "plan_id": None,
            "share_token": None,
            "share_url_path": None,
            "days": [
                day.model_dump() for day in expand_familiarization_weeks(templates)
            ],
            "sessions_requested": sessions,
            "sessions_actual": sessions,
            "session_minutes": SESSION_MINUTES,
            "insights": insights,
            "usage": usage,
        }
    detail = PlanService(db).create_plan(user_id, create, insights_json=insights)
    token = detail.get("share_token")
    return {
        "plan": detail,
        "plan_id": detail.get("id"),
        "share_token": token,
        "share_url_path": f"/lich/{token}" if token else None,
        "usage": usage,
    }
