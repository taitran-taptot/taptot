"""Local intent gate: only fitness/nutrition questions hit OpenAI."""

from __future__ import annotations

import re
import unicodedata
from typing import Literal

Intent = Literal["allow", "greeting", "offtopic"]

LOCAL_GREETING = (
    "Xin chào! Mình là TAPTOT, hỗ trợ lịch tập, bài tập, ăn uống và kiến thức luyện tập. "
    "Bạn muốn hỏi gì nào?"
)

LOCAL_OFFTOPIC = (
    "Mình chỉ trả lời về lịch tập, bài tập, dinh dưỡng và kiến thức luyện tập. "
    "Bạn hỏi một chủ đề trong phạm vi này giúp mình nhé."
)

LOCAL_REPLIES = {
    "greeting": LOCAL_GREETING,
    "offtopic": LOCAL_OFFTOPIC,
}

# Folded (no diacritics), length >= 4 uses substring; shorter uses word boundary.
_FITNESS_TERMS = (
    "hom nay tap",
    "tap hom nay",
    "tap gi",
    "tap nao",
    "bai nao",
    "buoi nay",
    "buoi hom nay",
    "lich hom nay",
    "hom nay an",
    "an gi",
    "an hom nay",
    "lich tap",
    "lich an",
    "bai tap",
    "buoi tap",
    "tap luyen",
    "tap luyen",
    "tap gym",
    "tap nha",
    "tap nguc",
    "tap lung",
    "tap vai",
    "tap chan",
    "tap bung",
    "tap tay",
    "khoi dong",
    "gian co",
    "giam can",
    "giam mo",
    "tang co",
    "tang can",
    "giu can",
    "thuc an",
    "thuc pham",
    "thuc don",
    "bua an",
    "bua sang",
    "bua trua",
    "bua toi",
    "dinh duong",
    "chat dam",
    "chat beo",
    "bot duong",
    "kcal",
    "calo",
    "calorie",
    "protein",
    "carb",
    "carbs",
    "macro",
    "tdee",
    "bmr",
    "bmi",
    "deficit",
    "surplus",
    "workout",
    "exercise",
    "hypertrophy",
    "cardio",
    "hiit",
    "yoga",
    "stretch",
    "mobility",
    "warmup",
    "cooldown",
    "squat",
    "deadlift",
    "bench",
    "deadlift",
    "plank",
    "pushup",
    "pullup",
    "push-up",
    "pull-up",
    "dumbbell",
    "barbell",
    "kettlebell",
    "volume",
    "intensity",
    "frequency",
    "overload",
    "recovery",
    "deload",
    "sets",
    "reps",
    "rep ",
    "gym",
    "hlv",
    "pt ",
    "trainer",
    "taptot",
    "tfit",
    "vietfit",
    "dung cu",
    "thiet bi",
    "may tap",
    "ta don",
    "ta ta",
    "form ",
    "ky thuat",
    "chan thuong",
    "phuc hoi",
    "ngu nghi",
    "uong nuoc",
    "hydration",
    "meal",
    "nutrition",
    "muscle",
    "strength",
    "endurance",
    "flexibility",
    "nguc",
    "lung",
    "vai ",
    "mong",
    "dui ",
    "gap bung",
    "co bung",
    "co lung",
    "co nguc",
    "tay truoc",
    "tay sau",
    "xien vai",
    "toan than",
    "fullbody",
    "full body",
    "upper",
    "lower",
    "push pull",
    "split",
    "session",
    "periodization",
    "prog ",
    "progression",
)

_GREETING_EXACT = frozenset(
    {
        "hi",
        "hello",
        "hey",
        "yo",
        "chao",
        "xin chao",
        "chao ban",
        "chao minh",
        "alo",
        "hallo",
        "good morning",
        "good evening",
        "cam on",
        "cam on nhe",
        "thanks",
        "thank you",
        "ok",
        "okay",
        "oke",
        "uk",
        "uhm",
        "um",
        "da",
        "vang",
        "roi",
        "duoc",
        "nhan",
    }
)

_OFFTOPIC_TERMS = (
    "chinh tri",
    "bau cu",
    "dang phai",
    "bitcoin",
    "crypto",
    "chung khoan",
    "forex",
    "lap trinh",
    "javascript",
    "typescript",
    "html",
    "css",
    "python",
    "java ",
    "golang",
    "source code",
    "viet code",
    "viet web",
    "bai tap toan",
    "bai tap van",
    "bai tap ly",
    "bai tap hoa",
    "bai tap anh",
    "bai tap tieng",
    "lam giup bai",
    "ket qua bong",
    "ty so",
    "gia iphone",
    "gia vang",
    "gia usd",
    "thoi tiet",
    "du lich",
    "ve may bay",
    "dat phong",
    "phim ",
    "ca si",
    "dien vien",
    "tin tuc",
    "chuyen tinh",
    "hen ho",
)


def fold_text(text: str) -> str:
    raw = unicodedata.normalize("NFD", (text or "").lower().strip())
    folded = "".join(ch for ch in raw if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", folded).strip()


def _has_term(folded: str, term: str) -> bool:
    needle = term.strip()
    if not needle:
        return False
    if len(needle) >= 4:
        return needle in folded
    return re.search(rf"(?<![a-z0-9]){re.escape(needle)}(?![a-z0-9])", folded) is not None


def _has_any(folded: str, terms: tuple[str, ...]) -> bool:
    return any(_has_term(folded, t) for t in terms)


def _is_greeting(folded: str) -> bool:
    if folded in _GREETING_EXACT:
        return True
    if len(folded) <= 24 and folded.startswith(("xin chao", "chao ", "hi ", "hello")):
        return True
    return False


def _is_short_followup(folded: str) -> bool:
    if len(folded) > 48:
        return False
    words = folded.split()
    return 1 <= len(words) <= 8


def _is_schedule_now_question(folded: str) -> bool:
    """Colloquial: 'hôm nay tập gì', 'tôi tập gì', 'hôm nay ăn gì'."""
    if _has_term(folded, "tap gi") or _has_term(folded, "tap nao") or _has_term(folded, "an gi"):
        return True
    todayish = (
        _has_term(folded, "hom nay")
        or folded.startswith("nay ")
        or _has_term(folded, "bay gio")
        or _has_term(folded, "luc nay")
    )
    action = (
        _has_term(folded, "tap")
        or _has_term(folded, "an")
        or _has_term(folded, "lich")
        or _has_term(folded, "bai")
        or _has_term(folded, "buoi")
    )
    return todayish and action


def classify_message(text: str, *, last_assistant: str | None = None) -> Intent:
    """Return allow (OpenAI) or a local intent. Never calls a model."""
    folded = fold_text(text)
    if not folded:
        return "offtopic"
    if _has_any(folded, _OFFTOPIC_TERMS) and not _has_any(folded, _FITNESS_TERMS):
        if _is_schedule_now_question(folded) and not _has_any(folded, _OFFTOPIC_TERMS):
            return "allow"
        return "offtopic"
    if _is_schedule_now_question(folded) and not _has_any(folded, _OFFTOPIC_TERMS):
        return "allow"
    if _has_any(folded, _FITNESS_TERMS):
        # "bai tap toan" contains bai tap AND offtopic school subject
        if _has_any(folded, _OFFTOPIC_TERMS):
            return "offtopic"
        return "allow"
    if _is_greeting(folded):
        return "greeting"
    last = (last_assistant or "").strip()
    in_thread = bool(last) and last not in LOCAL_REPLIES.values()
    if in_thread and _is_short_followup(folded) and not _has_any(folded, _OFFTOPIC_TERMS):
        return "allow"
    return "offtopic"
