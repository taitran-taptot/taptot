"""TAPTOT Q&A agent: OpenAI tool loop, compact context, persist ai_qa_messages."""

from __future__ import annotations

import json
import logging
import uuid
from collections.abc import Iterator
from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.entities import AiQaMessage, UserAiUsage
from app.services.ai_chat.compact import build_user_snapshot, clip_text, utcnow
from app.services.ai_chat.gate import LOCAL_REPLIES, classify_message
from app.services.ai_chat.openai_chat import OpenAIChatError, chat_completions
from app.services.ai_chat.tools import TOOL_STATUS_VI, TOOLS, execute_tool

logger = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 3
MAX_MESSAGE_CHARS = 2000

SYSTEM_PROMPT = """Bạn là HLV TAPTOT (tiếng Việt). Trả lời ngắn, rõ, hữu ích. Không viết chain-of-thought.

Quy tắc:
- Không bịa số liệu user, id bài tập, id thực phẩm, calo, sets. Chỉ dùng snapshot hoặc kết quả tool.
- Kiến thức chung (tần suất tập, nguyên tắc tăng cơ) được trả lời không cần tool.
- Hỏi về lịch/hồ sơ/macros của user → gọi tool. Hỏi lịch có phù hợp mục tiêu không → analyze_plan_for_goal.
- Không có lịch hoặc thiếu số → nói rõ và hỏi lại; đừng bịa.
- Không chẩn đoán bệnh; chấn thương/bệnh → khuyên gặp chuyên gia.
- Không sửa hay tạo lịch tập. Không đưa URL media.
- Chỉ trả lời tập luyện, lịch tập, dinh dưỡng, bài tập. Ngoài phạm vi thì từ chối ngắn.
- Kết luận trước, giải thích ngắn sau."""


def _history_turns() -> int:
    return max(2, min(12, int(get_settings().openai_chat_history_turns or 6)))


def _clip_limit() -> int:
    return max(80, min(800, int(get_settings().openai_chat_message_clip or 400)))


def resolve_conversation_id(db: Session, user_id: str, conversation_id: str | None) -> str:
    cid = (conversation_id or "").strip()
    if cid:
        try:
            return str(uuid.UUID(cid))
        except ValueError:
            cid = ""
    last = (
        db.query(AiQaMessage.conversation_id)
        .filter(AiQaMessage.user_id == user_id)
        .order_by(AiQaMessage.created_at.desc(), AiQaMessage.id.desc())
        .first()
    )
    if last and last[0]:
        return str(last[0])
    return str(uuid.uuid4())


def load_history_messages(
    db: Session,
    user_id: str,
    conversation_id: str,
    *,
    limit: int | None = None,
) -> list[AiQaMessage]:
    cap = limit if limit is not None else max(40, _history_turns() * 4)
    rows = (
        db.query(AiQaMessage)
        .filter(
            AiQaMessage.user_id == user_id,
            AiQaMessage.conversation_id == conversation_id,
        )
        .order_by(AiQaMessage.created_at.desc(), AiQaMessage.id.desc())
        .limit(cap)
        .all()
    )
    rows.reverse()
    return rows


def history_for_client(
    db: Session, user_id: str, conversation_id: str | None = None
) -> dict[str, Any]:
    cid = resolve_conversation_id(db, user_id, conversation_id)
    rows = load_history_messages(db, user_id, cid, limit=40)
    return {
        "conversation_id": cid,
        "messages": [
            {
                "id": row.id,
                "role": row.role,
                "content": row.content,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ],
    }


def _save_message(
    db: Session,
    *,
    user_id: str,
    conversation_id: str,
    role: str,
    content: str,
    referenced_exercise_ids: list[int] | None = None,
    referenced_food_ids: list[int] | None = None,
) -> AiQaMessage:
    row = AiQaMessage(
        user_id=user_id,
        conversation_id=conversation_id,
        role=role,
        content=content,
        referenced_exercise_ids=referenced_exercise_ids,
        referenced_food_ids=referenced_food_ids,
        created_at=utcnow(),
    )
    db.add(row)
    db.flush()
    return row


def _bump_usage(db: Session, user_id: str, tokens: int) -> None:
    month = date.today().strftime("%Y-%m")
    row = (
        db.query(UserAiUsage)
        .filter(UserAiUsage.user_id == user_id, UserAiUsage.usage_month == month)
        .first()
    )
    if not row:
        row = UserAiUsage(
            user_id=user_id,
            usage_month=month,
            generation_count=0,
            qa_message_count=0,
            tokens_used=0,
        )
        db.add(row)
    row.qa_message_count = int(row.qa_message_count or 0) + 1
    row.tokens_used = int(row.tokens_used or 0) + max(0, tokens)


def run_tool_loop(
    messages: list[dict[str, Any]],
    *,
    execute_fn,
    complete_fn,
    max_rounds: int = MAX_TOOL_ROUNDS,
) -> Iterator[dict[str, Any]]:
    """Yield status events; last yield is {event: final, content, tools_used, usage_tokens}."""
    tools_used: list[str] = []
    tokens = 0
    for round_i in range(max_rounds + 1):
        use_tools = round_i < max_rounds
        result = complete_fn(messages, TOOLS if use_tools else None)
        usage = result.get("usage") or {}
        try:
            tokens += int(usage.get("total_tokens") or 0)
        except (TypeError, ValueError):
            pass
        calls = result.get("tool_calls") if use_tools else None
        if calls:
            raw = result.get("raw_tool_calls") or [
                {
                    "id": c["id"],
                    "type": "function",
                    "function": {
                        "name": c["name"],
                        "arguments": json.dumps(c.get("arguments") or {}, ensure_ascii=False),
                    },
                }
                for c in calls
            ]
            messages.append(
                {
                    "role": "assistant",
                    "content": result.get("content"),
                    "tool_calls": raw,
                }
            )
            for call in calls:
                name = call["name"]
                tools_used.append(name)
                yield {
                    "event": "status",
                    "data": {
                        "tool": name,
                        "label_vi": TOOL_STATUS_VI.get(name, "Đang soạn…"),
                    },
                }
                payload = execute_fn(name, call.get("arguments") or {})
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call["id"],
                        "content": payload,
                    }
                )
            continue
        content = (result.get("content") or "").strip()
        yield {
            "event": "final",
            "content": content,
            "tools_used": tools_used,
            "usage_tokens": tokens,
        }
        return
    yield {
        "event": "final",
        "content": "Mình chưa tổng hợp được câu trả lời lúc này. Bạn hỏi lại ngắn hơn giúp mình nhé.",
        "tools_used": tools_used,
        "usage_tokens": tokens,
    }


def run_chat_events(
    db: Session,
    user_id: str,
    message: str,
    conversation_id: str | None = None,
    *,
    complete_fn=None,
    execute_fn=None,
) -> Iterator[dict[str, Any]]:
    text = (message or "").strip()
    if not text:
        yield {"event": "error", "data": {"message": "Nhập câu hỏi trước khi gửi."}}
        return
    if len(text) > MAX_MESSAGE_CHARS:
        yield {
            "event": "error",
            "data": {"message": f"Câu hỏi tối đa {MAX_MESSAGE_CHARS} ký tự."},
        }
        return

    cid = resolve_conversation_id(db, user_id, conversation_id)
    try:
        history = load_history_messages(db, user_id, cid, limit=_history_turns())
        last_assistant = next((row.content for row in reversed(history) if row.role == "assistant"), None)
        intent = classify_message(text, last_assistant=last_assistant)
        if intent != "allow":
            reply = LOCAL_REPLIES[intent]
            _save_message(db, user_id=user_id, conversation_id=cid, role="user", content=text)
            assistant = _save_message(
                db, user_id=user_id, conversation_id=cid, role="assistant", content=reply
            )
            db.commit()
            yield {"event": "delta", "data": {"text": reply}}
            yield {
                "event": "done",
                "data": {
                    "conversation_id": cid,
                    "message_id": assistant.id,
                    "tools_used": [],
                    "local": True,
                },
            }
            return

        snapshot = build_user_snapshot(db, user_id)
        clip = _clip_limit()
        openai_messages: list[dict[str, Any]] = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT
                + "\n\nHồ sơ hiện tại (JSON):\n"
                + json.dumps(snapshot, ensure_ascii=False, default=str),
            }
        ]
        for row in history:
            role = row.role if row.role in {"user", "assistant"} else "user"
            openai_messages.append({"role": role, "content": clip_text(row.content, clip) or ""})
        openai_messages.append({"role": "user", "content": text})

        _save_message(db, user_id=user_id, conversation_id=cid, role="user", content=text)
        db.commit()
    except Exception:
        logger.exception("Chat setup failed user=%s", user_id)
        db.rollback()
        yield {"event": "error", "data": {"message": "Có lỗi khi trả lời. Thử lại giúp mình."}}
        return

    completer = complete_fn or chat_completions

    def _exec(name: str, arguments: dict[str, Any]) -> str:
        if execute_fn:
            return execute_fn(name, arguments)
        return execute_tool(db, user_id, name, arguments)

    final_text = ""
    tools_used: list[str] = []
    tokens = 0
    try:
        for ev in run_tool_loop(openai_messages, execute_fn=_exec, complete_fn=completer):
            if ev.get("event") == "status":
                yield ev
            elif ev.get("event") == "final":
                final_text = ev.get("content") or ""
                tools_used = list(ev.get("tools_used") or [])
                tokens = int(ev.get("usage_tokens") or 0)
    except OpenAIChatError as exc:
        logger.warning("Chat OpenAI failed user=%s: %s", user_id, exc)
        msg = "Không gọi được trợ lý lúc này. Thử lại sau vài giây."
        if exc.status_code == 503:
            msg = "Trợ lý chưa được cấu hình OpenAI."
        yield {"event": "error", "data": {"message": msg}}
        return
    except Exception:
        logger.exception("Chat agent failed user=%s", user_id)
        yield {"event": "error", "data": {"message": "Có lỗi khi trả lời. Thử lại giúp mình."}}
        return

    if not final_text:
        final_text = "Mình chưa có câu trả lời phù hợp. Bạn diễn đạt lại câu hỏi nhé."

    try:
        assistant = _save_message(
            db,
            user_id=user_id,
            conversation_id=cid,
            role="assistant",
            content=final_text,
        )
        _bump_usage(db, user_id, tokens)
        db.commit()
    except Exception:
        logger.exception("Chat persist failed user=%s", user_id)
        db.rollback()
        yield {"event": "delta", "data": {"text": final_text}}
        yield {
            "event": "done",
            "data": {"conversation_id": cid, "message_id": None, "tools_used": tools_used},
        }
        return

    yield {"event": "delta", "data": {"text": final_text}}
    yield {
        "event": "done",
        "data": {
            "conversation_id": cid,
            "message_id": assistant.id,
            "tools_used": tools_used,
        },
    }
