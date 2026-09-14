"""Tool schemas + executors for the TAPTOT Q&A agent. user_id is never a model argument."""

from __future__ import annotations

import json
import logging
from typing import Any, Callable

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.pagination import PaginationParams
from app.models.entities import KnowledgeArticle
from app.services.ai_chat.compact import (
    analyze_plan_for_goal,
    build_user_snapshot,
    clip_text,
    compact_plan_overview,
    drop_heavy_fields,
    profile_for_calculator,
)
from app.services.calculator_service import CalculatorService
from app.services.search_service import SearchService
from app.services.workout_generation.nutrition_targets import estimate_targets

logger = logging.getLogger(__name__)

TOOL_STATUS_VI = {
    "get_user_context": "Đang đọc hồ sơ…",
    "get_plan_overview": "Đang xem lịch tập…",
    "analyze_plan_for_goal": "Đang phân tích volume…",
    "search_exercises": "Đang tìm bài tập…",
    "get_exercise": "Đang đọc bài tập…",
    "search_foods": "Đang tìm thực phẩm…",
    "search_knowledge": "Đang đọc kiến thức…",
    "calculate_nutrition": "Đang tính calo…",
}

TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_user_context",
            "description": (
                "Lấy hồ sơ tập luyện đã lưu (mục tiêu, cân, TDEE, lịch đang dùng). "
                "Không cần khi câu hỏi chỉ là kiến thức chung."
            ),
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_plan_overview",
            "description": (
                "Đọc lịch tập/ăn hiện tại của user: một tuần mẫu (ngày, split, bài sets/reps, bữa ăn). "
                "Có today_day_number và is_today để trả lời 'hôm nay tập gì'. Không trả instruction/gif."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "plan_id": {
                        "type": "integer",
                        "description": "Id lịch cụ thể. Bỏ trống = lịch mới cập nhật nhất.",
                    }
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_plan_for_goal",
            "description": (
                "Phân tích volume/tần suất nhóm cơ của lịch hiện tại so với ngân sách tuần "
                "(hard sets, verdict low/ok/high). Bắt buộc khi hỏi lịch có phù hợp mục tiêu không."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "plan_id": {
                        "type": "integer",
                        "description": "Id lịch. Bỏ trống = lịch mới nhất.",
                    }
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_exercises",
            "description": "Tìm bài tập trong catalog TAPTOT theo tên hoặc nhóm cơ. Tối đa 5 kết quả.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Tên bài hoặc từ khóa (ví dụ: bench, ngực)."},
                    "body_part": {
                        "type": "string",
                        "description": "Slug hoặc tên nhóm cơ (chest, back, quads...).",
                    },
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_exercise",
            "description": "Chi tiết một bài tập theo id catalog (form ngắn). Chỉ dùng id lấy từ search_exercises hoặc lịch.",
            "parameters": {
                "type": "object",
                "properties": {"exercise_id": {"type": "integer"}},
                "required": ["exercise_id"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_foods",
            "description": "Tìm thực phẩm trong catalog (macros/khẩu phần). Tối đa 5.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "Tên món, ví dụ ức gà, cơm."}},
                "required": ["query"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_knowledge",
            "description": "Tìm bài viết kiến thức TAPTOT (excerpt ngắn). Dùng khi cần nội dung giáo dục nội bộ.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_nutrition",
            "description": (
                "Tính BMR/TDEE/macro bằng công thức (không suy đoán). "
                "Thiếu số liệu thì dùng hồ sơ user; vẫn thiếu thì báo thiếu."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "weight_kg": {"type": "number"},
                    "height_cm": {"type": "number"},
                    "age": {"type": "integer"},
                    "gender": {"type": "string", "enum": ["male", "female"]},
                    "activity_level": {
                        "type": "string",
                        "enum": ["sedentary", "light", "moderate", "active", "very_active"],
                    },
                    "goal": {
                        "type": "string",
                        "enum": ["lose_weight", "maintain", "gain_weight", "gain_muscle"],
                    },
                },
                "additionalProperties": False,
            },
        },
    },
]

TOOL_NAMES = frozenset(
    fn["function"]["name"] for fn in TOOLS if isinstance(fn.get("function"), dict)
)


def _compact_dump(payload: Any) -> str:
    cleaned = drop_heavy_fields(payload)
    return json.dumps(cleaned, ensure_ascii=False, separators=(",", ":"), default=str)


def _search_exercises(db: Session, user_id: str, args: dict[str, Any]) -> dict[str, Any]:
    q = clip_text(args.get("query"), 80)
    body_part = clip_text(args.get("body_part"), 40)
    items, total = SearchService(db).search_exercises(
        PaginationParams(page=1, page_size=5),
        q=q,
        body_part=body_part,
    )
    compact = [
        {
            "id": it.get("id"),
            "name_vi": it.get("name_vi"),
            "muscle_group": it.get("muscle_group"),
            "body_part": it.get("body_part"),
            "difficulty": it.get("difficulty"),
            "exercise_type": it.get("exercise_type"),
        }
        for it in items
    ]
    return {"total": total, "items": compact}


def _get_exercise(db: Session, user_id: str, args: dict[str, Any]) -> dict[str, Any]:
    try:
        eid = int(args.get("exercise_id"))
    except (TypeError, ValueError):
        return {"error": "invalid_exercise_id"}
    detail = SearchService(db).get_exercise_detail(eid)
    if not detail:
        return {"error": "not_found", "exercise_id": eid}
    return {
        "id": detail.get("id"),
        "name_vi": detail.get("name_vi"),
        "muscle_group": detail.get("muscle_group"),
        "difficulty": detail.get("difficulty"),
        "movement_role": detail.get("movement_role"),
        "instruction_vi": clip_text(detail.get("instruction_vi"), 800),
        "common_mistakes_vi": clip_text(detail.get("common_mistakes_vi"), 400),
        "tips_vi": clip_text(detail.get("tips_vi"), 400),
    }


def _search_foods(db: Session, user_id: str, args: dict[str, Any]) -> dict[str, Any]:
    q = clip_text(args.get("query"), 80)
    if not q:
        return {"error": "missing_query"}
    items, total = SearchService(db).search_foods(
        PaginationParams(page=1, page_size=5),
        q=q,
        owner_user_id=user_id,
    )
    compact = [
        {
            "id": food.id,
            "name_vi": food.name_vi,
            "serving_size": food.serving_size,
            "calories": food.calories,
            "protein_g": food.protein_g,
            "carbs_g": food.carbs_g,
            "fat_g": food.fat_g,
        }
        for food in items
    ]
    return {"total": total, "items": compact}


def _search_knowledge(db: Session, user_id: str, args: dict[str, Any]) -> dict[str, Any]:
    q = clip_text(args.get("query"), 80)
    if not q:
        return {"error": "missing_query"}
    pattern = f"%{q}%"
    rows = (
        db.query(KnowledgeArticle)
        .filter(
            KnowledgeArticle.is_published.is_(True),
            or_(
                KnowledgeArticle.title_vi.ilike(pattern),
                KnowledgeArticle.content_md.ilike(pattern),
                KnowledgeArticle.seo_description.ilike(pattern),
            ),
        )
        .order_by(KnowledgeArticle.sort_order.asc())
        .limit(3)
        .all()
    )
    return {
        "items": [
            {
                "id": a.id,
                "slug": a.slug,
                "title_vi": a.title_vi,
                "level": a.level,
                "excerpt": clip_text(a.content_md, 400),
            }
            for a in rows
        ]
    }


def _calculate_nutrition(db: Session, user_id: str, args: dict[str, Any]) -> dict[str, Any]:
    defaults = profile_for_calculator(db, user_id)
    gender = (args.get("gender") or defaults.get("gender") or "male") or "male"
    try:
        weight = float(args["weight_kg"]) if args.get("weight_kg") is not None else defaults.get("weight_kg")
        height = float(args["height_cm"]) if args.get("height_cm") is not None else defaults.get("height_cm")
        age = int(args["age"]) if args.get("age") is not None else defaults.get("age")
    except (TypeError, ValueError):
        return {"error": "invalid_numbers", "message_vi": "Số liệu cân/chiều cao/tuổi không hợp lệ."}
    if not weight or not height or not age:
        return {
            "error": "missing_profile",
            "message_vi": "Thiếu cân, chiều cao hoặc tuổi để tính TDEE. Hãy cung cấp hoặc cập nhật hồ sơ.",
        }
    activity = args.get("activity_level") or defaults.get("activity_level") or "moderate"
    goal = args.get("goal") or defaults.get("goal") or "maintain"
    calc = CalculatorService(db)
    tdee = calc.tdee(
        gender=str(gender),
        weight_kg=float(weight),
        height_cm=float(height),
        age=int(age),
        activity_level=str(activity),
        goal=str(goal) if str(goal) in {"lose_weight", "maintain", "gain_muscle"} else "maintain",
    )
    macros = calc.macros(int(tdee["target_calories"]), float(weight), str(goal))
    bmi = calc.bmi(float(weight), float(height))
    extra = estimate_targets(
        {
            "gender": gender,
            "weight_kg": weight,
            "height_cm": height,
            "age": age,
            "activity": activity,
            "goal": goal,
        }
    )
    out = {**tdee, **macros, **bmi}
    if extra:
        out["clamped_target_calories"] = extra.target_calories
        out["delta_kcal"] = extra.delta_kcal
        out["protein_g"] = extra.protein_g
        out["carbs_g"] = extra.carbs_g
        out["fat_g"] = extra.fat_g
    return out


_HANDLERS: dict[str, Callable[[Session, str, dict[str, Any]], dict[str, Any]]] = {
    "get_user_context": lambda db, user_id, _args: build_user_snapshot(db, user_id),
    "get_plan_overview": lambda db, user_id, args: compact_plan_overview(
        db, user_id, args.get("plan_id")
    ),
    "analyze_plan_for_goal": lambda db, user_id, args: analyze_plan_for_goal(
        db, user_id, args.get("plan_id")
    ),
    "search_exercises": _search_exercises,
    "get_exercise": _get_exercise,
    "search_foods": _search_foods,
    "search_knowledge": _search_knowledge,
    "calculate_nutrition": _calculate_nutrition,
}


def execute_tool(db: Session, user_id: str, name: str, arguments: dict[str, Any] | None) -> str:
    args = arguments if isinstance(arguments, dict) else {}
    handler = _HANDLERS.get(name)
    if not handler:
        return _compact_dump({"error": "unknown_tool", "name": name})
    try:
        result = handler(db, user_id, args)
    except Exception:
        logger.exception("Chat tool %s failed for user=%s", name, user_id)
        return _compact_dump({"error": "tool_failed", "name": name})
    return _compact_dump(result)
