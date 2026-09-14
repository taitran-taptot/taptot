"""Q&A chat agent: compact payloads, tool loop cap, auth, rate limit."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

from app.core.rate_limit import classify_rate_limit
from app.services.ai_chat.compact import drop_heavy_fields, resolve_today_day_number, week_day_range
from app.services.ai_chat.agent import MAX_TOOL_ROUNDS, run_tool_loop
from app.services.ai_chat.tools import TOOL_NAMES, TOOLS, execute_tool


def test_intent_gate_allows_fitness_blocks_offtopic():
    from app.services.ai_chat.gate import LOCAL_GREETING, LOCAL_OFFTOPIC, classify_message

    assert classify_message("hôm nay tập gì") == "allow"
    assert classify_message("Hôm nay tập gì vậy?") == "allow"
    assert classify_message("tôi tập gì") == "allow"
    assert classify_message("hôm nay ăn gì") == "allow"
    assert classify_message("lịch hôm nay") == "allow"
    assert classify_message("Lịch tập hiện tại có phù hợp tăng cơ không?") == "allow"
    assert classify_message("Ăn bao nhiêu protein mỗi ngày?") == "allow"
    assert classify_message("Calo TDEE của tôi là bao nhiêu?") == "allow"
    assert classify_message("Form squat như nào cho đúng?") == "allow"
    assert classify_message("Xin chào") == "greeting"
    assert classify_message("hello") == "greeting"
    assert classify_message("hôm nay xem phim gì") == "offtopic"
    assert classify_message("Viết giúp mình code Python") == "offtopic"
    assert classify_message("Thời tiết hôm nay thế nào?") == "offtopic"
    assert classify_message("Làm bài tập toán giúp mình") == "offtopic"
    # Follow-up in an ongoing coaching thread
    assert classify_message("còn sao nữa?", last_assistant="Ngực 8 hard sets/tuần là ổn.") == "allow"
    # After a local refuse, short chatter stays local
    assert classify_message("ừ rồi", last_assistant=LOCAL_OFFTOPIC) == "offtopic"
    assert classify_message("kể chuyện vui đi", last_assistant=LOCAL_GREETING) == "offtopic"


def test_drop_heavy_fields_strips_media_and_steps():
    payload = {
        "days": [
            {
                "title_vi": "Push",
                "gif_url": "https://cdn.example/x.gif",
                "image_url": "https://cdn.example/x.png",
                "video_url": "https://cdn.example/x.mp4",
                "instruction_steps_vi": ["bước 1", "bước 2"],
                "exercises": [
                    {
                        "name_vi": "Bench",
                        "sets": 3,
                        "reps": "8",
                        "gif_url": "https://cdn.example/bench.gif",
                    }
                ],
            }
        ]
    }
    out = drop_heavy_fields(payload)
    day = out["days"][0]
    assert "gif_url" not in day
    assert "image_url" not in day
    assert "video_url" not in day
    assert "instruction_steps_vi" not in day
    assert day["exercises"][0]["name_vi"] == "Bench"
    assert day["exercises"][0]["sets"] == 3
    assert "gif_url" not in day["exercises"][0]


def test_resolve_today_day_number_from_start():
    assert (
        resolve_today_day_number(
            start_date=date(2026, 9, 1),
            day_numbers=[1, 2, 3, 4],
            today=date(2026, 9, 3),
        )
        == 3
    )
    # template cycles when plan is a 4-day week without 100-day expand
    assert (
        resolve_today_day_number(
            start_date=date(2026, 9, 1),
            day_numbers=[1, 2, 3, 4],
            today=date(2026, 9, 6),
        )
        == 2
    )
    assert week_day_range([1, 2, 3, 4], sessions_per_week=4, challenge=False) == (1, 4)


def test_week_day_range_challenge_samples_one_week():
    nums = list(range(1, 53))
    start_date = date(2026, 1, 1)
    today = date(2026, 1, 8)  # week 1 (0-indexed week 1)
    window = week_day_range(
        nums,
        sessions_per_week=4,
        challenge=True,
        start_date=start_date,
        today=today,
    )
    assert window == (5, 8)


def test_tools_have_no_user_id_parameter():
    names = set()
    for spec in TOOLS:
        fn = spec["function"]
        names.add(fn["name"])
        props = (fn.get("parameters") or {}).get("properties") or {}
        assert "user_id" not in props
        blob = str(fn.get("parameters") or {})
        assert "user_id" not in blob
    assert names == TOOL_NAMES
    assert "analyze_plan_for_goal" in names
    assert "get_plan_overview" in names


def test_unknown_tool_does_not_raise():
    out = execute_tool(MagicMock(), "user-1", "not_a_real_tool", {})
    assert "unknown_tool" in out


def test_tool_loop_caps_rounds():
    calls = {"n": 0}

    def complete_fn(messages, tools=None):
        calls["n"] += 1
        if tools:
            return {
                "content": None,
                "tool_calls": [
                    {"id": f"c{calls['n']}", "name": "get_user_context", "arguments": {}}
                ],
                "raw_tool_calls": None,
                "usage": {"total_tokens": 10},
            }
        return {"content": "ok", "tool_calls": None, "usage": {"total_tokens": 5}}

    executed = []

    def execute_fn(name, arguments):
        executed.append(name)
        return "{}"

    events = list(run_tool_loop([], execute_fn=execute_fn, complete_fn=complete_fn))
    finals = [e for e in events if e.get("event") == "final"]
    assert len(finals) == 1
    assert finals[0]["content"] == "ok"
    assert calls["n"] == MAX_TOOL_ROUNDS + 1
    assert len(executed) == MAX_TOOL_ROUNDS
    assert all(n == "get_user_context" for n in executed)


def test_classify_rate_limit_ai_chat():
    bucket, limit = classify_rate_limit("/api/v1/ai/chat", "POST")
    assert bucket == "ai-chat"
    assert limit <= 30
    gen_bucket, _ = classify_rate_limit("/api/v1/ai/generate-workout-schedule", "POST")
    assert gen_bucket == "ai-gen"
    assert classify_rate_limit("/api/v1/ai/chat/history", "GET")[0] == "ip"


def test_chat_requires_auth():
    from fastapi.testclient import TestClient

    from app.main import create_app

    client = TestClient(create_app())
    res = client.post("/api/v1/ai/chat", json={"message": "xin chào"})
    assert res.status_code == 401
    hist = client.get("/api/v1/ai/chat/history")
    assert hist.status_code == 401


def test_qa_conversation_id_is_uuid_typed():
    """PG column is UUID; Text mapping makes `uuid = varchar` fail at runtime."""
    from sqlalchemy import Uuid

    from app.models.entities import AiQaMessage

    col = AiQaMessage.__table__.c.conversation_id
    assert isinstance(col.type, Uuid)
