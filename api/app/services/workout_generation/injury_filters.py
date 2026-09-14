"""Keyword injury / age denylist for exercise shortlists."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any

from app.services.workout_generation.coverage import family_of

_JUMP_TOKENS = frozenset(
    {
        "nhay",
        "nhảy",
        "jump",
        "plyo",
        "kipping",
        "kip ",
        "burpee",
        "box jump",
        "goi cao",
        "gối cao",
        "high knee",
        "lunge jump",
        "pistol",
    }
)


def fold_vi(text: str) -> str:
    raw = unicodedata.normalize("NFD", (text or "").lower())
    return "".join(c for c in raw if unicodedata.category(c) != "Mn")


@dataclass
class InjuryConstraints:
    denied_patterns: frozenset[str] = frozenset()
    denied_families: frozenset[str] = frozenset()
    denied_name_tokens: frozenset[str] = frozenset()
    notes_vi: list[str] = field(default_factory=list)
    relaxed_patterns: bool = False

    def blocks_exercise(
        self,
        *,
        pattern: str | None,
        muscle_slug: str | None,
        name_vi: str | None,
        ignore_patterns: bool = False,
    ) -> bool:
        pat = (pattern or "").strip().lower()
        name = fold_vi(name_vi or "")
        if not ignore_patterns and pat and pat in self.denied_patterns:
            return True
        fam = family_of(pat) if pat else ""
        if fam and fam in self.denied_families:
            return True
        blob = f"{name} {fold_vi(pat)} {fold_vi(muscle_slug or '')}"
        for token in self.denied_name_tokens:
            if fold_vi(token) in blob:
                return True
        return False


def parse_injury_constraints(
    health_note: str | None,
    *,
    age: Any = None,
) -> InjuryConstraints:
    patterns: set[str] = set()
    families: set[str] = set()
    tokens: set[str] = set(_JUMP_TOKENS) if _age_ge(age, 45) else set()
    notes: list[str] = []
    folded = fold_vi(health_note or "")

    if not folded and not tokens:
        return InjuryConstraints()

    if _age_ge(age, 45):
        notes.append("Từ 45 tuổi: tránh bài nhảy / plyo / kipping.")

    if _has_term(folded, "goi", "meniscus", "khop goi"):
        patterns.add("squat")
        families.add("squat")
        tokens.update(_JUMP_TOKENS)
        notes.append("Ghi chú gối: loại squat sâu và bài nhảy.")
    if _has_term(folded, "vai", "rotator"):
        patterns.add("v_push")
        notes.append("Ghi chú vai: loại đẩy trên đầu.")
    if _has_term(folded, "lung", "cot song", "dia dem", "thoat vi"):
        patterns.add("hinge")
        families.add("hinge")
        notes.append("Ghi chú lưng: loại hinge/deadlift nặng.")
    if _has_term(folded, "co chan", "mat ca", "got chan", "ankle"):
        tokens.update(_JUMP_TOKENS)
        notes.append("Ghi chú cổ chân: loại bài nhảy.")
    if _has_term(folded, "co tay", "wrist"):
        tokens.update({"barbell", "ta don"})
        notes.append("Ghi chú cổ tay: hạn chế tạ đòn.")

    if not patterns and not families and not tokens:
        return InjuryConstraints()

    return InjuryConstraints(
        denied_patterns=frozenset(patterns),
        denied_families=frozenset(families),
        denied_name_tokens=frozenset(tokens),
        notes_vi=notes,
    )


def _age_ge(age: Any, threshold: int) -> bool:
    try:
        return int(age) >= threshold
    except (TypeError, ValueError):
        return False


def _has_term(folded: str, *needles: str) -> bool:
    for needle in needles:
        n = fold_vi(needle)
        if " " in n:
            if n in folded:
                return True
            continue
        if re.search(rf"(^|[^a-z]){re.escape(n)}([^a-z]|$)", folded):
            return True
    return False
