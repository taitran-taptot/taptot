"""OpenAI picker for exercise ids within shortlists; deterministic helper for tests."""

from __future__ import annotations

import json
import logging
import copy
import time
import urllib.error
import urllib.request
from typing import Any

from app.core.config import get_settings

logger = logging.getLogger(__name__)

OPENAI_PICK_FAIL_VI = (
    "TAPTOT không tạo được lịch vì OpenAI lỗi / thiếu cấu hình. Thử lại sau."
)

_STRENGTH_KEYS = frozenset({"compound", "accessory", "resistance", "conditioning"})
_MOBILITY_KEYS = frozenset({"general_warmup", "dynamic_mobility", "cooldown"})
# Isolation/accessory blocks that week B may swap. Compounds stay on week A.
ISO_SWAP_KEYS = frozenset({"accessory", "resistance", "conditioning", "core", "cardio"})
SLOT_PICKS_KEY = "_slot_picks"
DOSE_PICKS_KEY = "_dose_by_exercise"


def _copy_picks(picks: dict[str, Any] | None) -> dict[str, Any]:
    return copy.deepcopy(picks or {})


class OpenAIPickError(Exception):
    """Hard-fail when OpenAI cannot pick exercises for the plan."""

    def __init__(self, message: str = OPENAI_PICK_FAIL_VI) -> None:
        self.message = message
        super().__init__(message)


def _item_eid(item: object) -> int:
    return int(item["id"]) if isinstance(item, dict) else int(item.id)


def _item_muscle(item: object) -> str | None:
    if isinstance(item, dict):
        raw = item.get("muscle") or item.get("muscle_slug")
    else:
        raw = getattr(item, "muscle_slug", None) or getattr(item, "muscle", None)
    slug = str(raw or "").strip().lower()
    return slug or None


def _item_name(item: object) -> str | None:
    if isinstance(item, dict):
        raw = item.get("name_vi")
    else:
        raw = getattr(item, "name_vi", None)
    name = str(raw or "").strip()
    return name or None


def _item_name_en(item: object) -> str | None:
    if isinstance(item, dict):
        raw = item.get("name_en")
    else:
        raw = getattr(item, "name_en", None)
    name = str(raw or "").strip()
    return name or None


def _trained_slugs_from_picks(day_blocks: list[dict], picks: dict[str, list[int]]) -> frozenset[str]:
    by_id: dict[int, str] = {}
    for block in day_blocks:
        key = str(block.get("block_key") or "")
        if key in _MOBILITY_KEYS:
            continue
        for x in block.get("shortlist") or []:
            slug = _item_muscle(x)
            if slug:
                by_id[_item_eid(x)] = slug
    slugs: set[str] = set()
    for key, ids in picks.items():
        if str(key).startswith("_") or key in _MOBILITY_KEYS:
            continue
        for eid in ids or []:
            slug = by_id.get(int(eid))
            if slug:
                slugs.add(slug)
    return frozenset(slugs)


def deterministic_picks(
    day_blocks: list[dict],
    *,
    split_role: str | None = None,
    focus_slugs: frozenset[str] | None = None,
    used_ids: set[int] | None = None,
    avoid_compound_patterns: frozenset[str] | None = None,
    day_index: int = 0,
    avoid_ids: set[int] | frozenset[int] | None = None,
    avoid_stems: set[str] | frozenset[str] | None = None,
    prefer_knee: bool = False,
) -> dict[str, list[int]]:
    """Slot-template / diversified deterministic picks, then day coverage repair.

    Used by free_home generation and unit tests (not the OpenAI pick path).
    """
    from app.services.workout_generation.coverage import (
        diversified_pick,
        family_of,
        repair_day_coverage,
    )
    from app.services.workout_generation.muscle_quotas import repair_muscle_quotas
    from app.services.workout_generation.session_templates import (
        fill_strength_slots,
        slots_for_session,
        uses_session_templates,
    )
    from app.services.workout_generation.split_map import mobility_match_rank

    role = split_role
    blocks_by_key = {str(b.get("block_key")): b for b in day_blocks}

    def _item_eid(item: object) -> int:
        return int(item["id"]) if isinstance(item, dict) else int(item.id)

    def _pick_mobility(
        shortlist: list,
        n: int,
        used: set[int],
        *,
        cooldown: bool,
        trained_slugs: frozenset[str] | None = None,
    ) -> list[int]:
        ranked = sorted(
            shortlist,
            key=lambda x: (
                mobility_match_rank(
                    muscle_slug=_item_muscle(x),
                    name_vi=_item_name(x),
                    split_role=role,
                    cooldown=cooldown,
                    trained_slugs=trained_slugs,
                ),
                _item_eid(x),
            ),
        )
        ids: list[int] = []
        for x in ranked:
            eid = _item_eid(x)
            if eid in used:
                continue
            ids.append(eid)
            used.add(eid)
            if len(ids) >= n:
                break
        return ids

    primary_key = "resistance" if "resistance" in blocks_by_key else "compound"
    secondary_key = "conditioning" if "conditioning" in blocks_by_key else "accessory"
    primary_block = blocks_by_key.get(primary_key) or {}
    secondary_block = blocks_by_key.get(secondary_key) or {}
    location = "home" if primary_key == "resistance" else "gym"

    if uses_session_templates(role):
        primary_n = int(primary_block.get("count_max") or 0) if primary_block.get("pick") else 0
        secondary_n = int(secondary_block.get("count_max") or 0) if secondary_block.get("pick") else 0
        if location == "home":
            if primary_n <= 1:
                compound_n, accessory_n = primary_n, 0
            elif primary_n == 2:
                compound_n, accessory_n = 1, 1
            else:
                compound_n, accessory_n = 2, primary_n - 2
        else:
            compound_n = primary_n
            accessory_n = secondary_n if secondary_key == "accessory" else 0
        pool: list = []
        week_skip = set(used_ids or ())
        strength_keys = (primary_key, secondary_key) if location == "gym" else (primary_key,)
        for key in strength_keys:
            b = blocks_by_key.get(key) or {}
            if not b.get("pick"):
                continue
            for x in list(b.get("shortlist") or []):
                if _item_eid(x) in week_skip:
                    continue
                row = dict(x) if isinstance(x, dict) else {
                    "id": int(x.id),
                    "movement_pattern": getattr(x, "movement_pattern", None),
                    "movement_role": getattr(x, "movement_role", None),
                    "muscle": getattr(x, "muscle_slug", None) or getattr(x, "muscle", None),
                    "name_vi": getattr(x, "name_vi", ""),
                }
                row["_block"] = key
                pool.append(row)
        slots = slots_for_session(
            role,
            compound_n=compound_n,
            accessory_n=accessory_n,
            location=location,
            focus_slugs=focus_slugs,
            day_index=day_index,
            allow_bar_moves=location != "home",
            experience_level=2,
        )
        filled = fill_strength_slots(
            role,
            slots,
            pool,
            used_ids=week_skip,
            avoid_compound_patterns=avoid_compound_patterns,
            focus_slugs=focus_slugs,
            avoid_ids=avoid_ids,
            avoid_stems=avoid_stems,
            prefer_knee=prefer_knee,
        )
        out: dict[str, list[int]] = {k: list(v) for k, v in filled.items()}
        if primary_key not in out:
            out[primary_key] = []
        if location == "gym" and secondary_key not in out:
            out[secondary_key] = []
        used = set(week_skip)
        for ids in out.values():
            used.update(ids)
        trained = _trained_slugs_from_picks(day_blocks, out)
        for block in day_blocks:
            if not block.get("pick"):
                continue
            key = str(block["block_key"])
            if key in out:
                continue
            n = int(block.get("count_max") or 0)
            shortlist = list(block.get("shortlist") or [])
            if n <= 0:
                out[key] = []
                continue
            if block.get("is_optional") and not shortlist:
                out[key] = []
                continue
            cooldown = key == "cooldown"
            warmup = key in {"general_warmup", "dynamic_mobility"}
            if warmup or cooldown:
                out[key] = _pick_mobility(
                    shortlist, n, used, cooldown=cooldown, trained_slugs=trained
                )
            else:
                ids = []
                for x in shortlist:
                    eid = _item_eid(x)
                    if eid in used:
                        continue
                    ids.append(eid)
                    used.add(eid)
                    if len(ids) >= n:
                        break
                out[key] = ids
        out = repair_muscle_quotas(
            day_blocks, out, split_role=role, focus_slugs=focus_slugs
        )
        out = repair_day_coverage(day_blocks, out, split_role=role)
        return fill_mobility_picks(day_blocks, out, split_role=role)

    out = {}
    used_ids = set(used_ids or ())
    covered: set[str] = set()
    for block in day_blocks:
        if not block.get("pick"):
            continue
        key = str(block["block_key"])
        n = int(block.get("count_max") or 0)
        shortlist = list(block.get("shortlist") or [])
        if n <= 0:
            out[key] = []
            continue
        if block.get("is_optional") and not shortlist:
            out[key] = []
            continue
        cooldown = key == "cooldown"
        warmup = key in {"general_warmup", "dynamic_mobility"}
        if warmup or cooldown:
            ids = _pick_mobility(shortlist, n, used_ids, cooldown=cooldown)
        elif key in {"compound", "accessory", "resistance", "conditioning"}:
            ids = diversified_pick(
                shortlist,
                count=n,
                split_role=role,
                used_ids=used_ids,
                block_key=key,
                already_covered=covered,
            )
        else:
            ids = []
            for x in shortlist:
                eid = _item_eid(x)
                if eid in used_ids:
                    continue
                ids.append(eid)
                if len(ids) >= n:
                    break
            if block.get("is_optional") and not ids:
                out[key] = []
                continue
        if block.get("is_optional") and not ids:
            out[key] = []
            continue
        out[key] = ids
        for eid in ids:
            used_ids.add(eid)
        if key not in {"compound", "accessory", "resistance", "conditioning"}:
            continue
        for x in shortlist:
            eid = _item_eid(x)
            if eid not in ids:
                continue
            pat = None
            if isinstance(x, dict):
                pat = x.get("movement_pattern")
            else:
                pat = getattr(x, "movement_pattern", None)
            fam = family_of(str(pat).lower() if pat else None)
            if fam:
                covered.add(fam)
    out = repair_day_coverage(day_blocks, out, split_role=role)
    return fill_mobility_picks(day_blocks, out, split_role=role)


def _strip_code_fence(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def _parse_llm_json(raw: str) -> Any:
    return json.loads(_strip_code_fence(raw))


def _parse_llm_days(raw: str) -> list[dict[str, Any]]:
    data = _parse_llm_json(raw)
    if isinstance(data, dict) and "days" in data:
        return list(data["days"])
    if isinstance(data, dict) and "blocks" in data:
        return [data]
    if isinstance(data, list):
        return data
    raise ValueError("Unexpected LLM JSON shape")


def _require_openai_settings():
    settings = get_settings()
    if not bool(getattr(settings, "workout_gen_use_openai", True)):
        raise OpenAIPickError(
            "Gen lịch yêu cầu OpenAI chọn bài (WORKOUT_GEN_USE_OPENAI=true)."
        )
    if not (settings.openai_api_key or "").strip():
        raise OpenAIPickError(
            "Thiếu OPENAI_API_KEY — không thể tạo lịch tập. Thêm key rồi thử lại."
        )
    return settings


def _openai_chat_content(body: dict[str, Any]) -> str:
    """POST /chat/completions and return message content. Retries 429 up to 5 times."""
    settings = get_settings()
    url = settings.openai_base_url.rstrip("/") + "/chat/completions"
    timeout = min(60, int(settings.openai_timeout_seconds or 60))
    max_out = min(
        int(body.get("max_completion_tokens") or body.get("max_tokens") or 2048),
        8192,
    )

    def _request(payload: dict[str, Any]) -> str:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"]

    last_exc: Exception | None = None
    for attempt in range(1, 6):
        try:
            return _request(body)
        except urllib.error.HTTPError as exc:
            err_body = ""
            try:
                err_body = exc.read().decode("utf-8", errors="replace")
            except Exception:
                pass
            if exc.code == 400 and "max_completion_tokens" in err_body:
                legacy = {k: v for k, v in body.items() if k != "max_completion_tokens"}
                legacy["max_tokens"] = max_out
                try:
                    return _request(legacy)
                except (
                    urllib.error.URLError,
                    urllib.error.HTTPError,
                    KeyError,
                    IndexError,
                    json.JSONDecodeError,
                    ValueError,
                    TimeoutError,
                ) as retry_exc:
                    logger.warning("OpenAI exercise pick failed (legacy params): %s", retry_exc)
                    raise OpenAIPickError(OPENAI_PICK_FAIL_VI) from retry_exc
            if exc.code == 429:
                wait = 3 * attempt
                marker = "Please try again in "
                if marker in err_body:
                    try:
                        after = err_body.split(marker, 1)[1].split("s", 1)[0].strip()
                        wait = max(wait, int(float(after)) + 1)
                    except (TypeError, ValueError):
                        pass
                logger.warning(
                    "OpenAI rate limited (attempt %s/5), sleeping %ss", attempt, wait
                )
                last_exc = exc
                time.sleep(wait)
                continue
            logger.warning("OpenAI exercise pick failed: %s %s", exc, err_body[:300])
            raise OpenAIPickError(OPENAI_PICK_FAIL_VI) from exc
        except (
            urllib.error.URLError,
            KeyError,
            IndexError,
            json.JSONDecodeError,
            ValueError,
            TimeoutError,
            OSError,
        ) as exc:
            logger.warning("OpenAI exercise pick failed: %s", exc)
            raise OpenAIPickError(OPENAI_PICK_FAIL_VI) from exc
    raise OpenAIPickError(OPENAI_PICK_FAIL_VI) from last_exc


def isolation_ids_from_picks(picks: dict[str, list[int]] | None) -> list[int]:
    """Isolation/accessory/cardio ids from a day's picks (compounds excluded)."""
    out: list[int] = []
    seen: set[int] = set()
    for key, ids in (picks or {}).items():
        if str(key).startswith("_"):
            continue
        if str(key) not in ISO_SWAP_KEYS:
            continue
        for raw in ids or []:
            try:
                eid = int(raw)
            except (TypeError, ValueError):
                continue
            if eid not in seen:
                seen.add(eid)
                out.append(eid)
    return out


def strength_ids_from_picks(picks: dict[str, list[int]] | None) -> list[int]:
    """Compound + isolation ids to avoid repeating across phases."""
    out: list[int] = []
    seen: set[int] = set()
    for key, ids in (picks or {}).items():
        if str(key).startswith("_"):
            continue
        if str(key) not in _STRENGTH_KEYS:
            continue
        for raw in ids or []:
            try:
                eid = int(raw)
            except (TypeError, ValueError):
                continue
            if eid not in seen:
                seen.add(eid)
                out.append(eid)
    return out


def stems_from_picks(
    picks: dict[str, list[int]] | None,
    day_blocks: list[dict] | None = None,
) -> list[str]:
    """Movement-family stems (step-up / lunge / push-up) for prior-phase avoid."""
    from app.services.workout_generation.weekly_volume import lift_stem

    names: dict[int, tuple[str | None, str | None]] = {}
    for block in day_blocks or []:
        for x in block.get("shortlist") or []:
            try:
                eid = _item_eid(x)
            except (TypeError, ValueError, KeyError, AttributeError):
                continue
            names[eid] = (_item_name(x), _item_name_en(x))
    out: list[str] = []
    seen: set[str] = set()
    for eid in strength_ids_from_picks(picks):
        nv, ne = names.get(eid, (None, None))
        stem = lift_stem(nv, ne)
        if stem and stem not in seen:
            seen.add(stem)
            out.append(stem)
    return out


def _avoid_id_set(avoid_ids: set[int] | frozenset[int] | list[int] | None) -> set[int]:
    out: set[int] = set()
    for raw in avoid_ids or ():
        try:
            out.add(int(raw))
        except (TypeError, ValueError):
            continue
    return out


def _avoid_stem_set(avoid_stems: set[str] | frozenset[str] | list[str] | None) -> set[str]:
    return {str(s).strip() for s in (avoid_stems or ()) if str(s).strip()}


def _item_stem(item: object) -> str | None:
    from app.services.workout_generation.weekly_volume import lift_stem

    return lift_stem(_item_name(item), _item_name_en(item))


def _item_is_avoided(
    item: object,
    avoid_ids: set[int],
    avoid_stems: set[str],
) -> bool:
    try:
        eid = _item_eid(item)
    except (TypeError, ValueError, KeyError, AttributeError):
        return False
    if eid in avoid_ids:
        return True
    stem = _item_stem(item)
    return bool(stem and stem in avoid_stems)


def _swap_avoided_picks(
    cleaned: list[int],
    shortlist: list,
    *,
    avoid_ids: set[int],
    avoid_stems: set[str],
    extra_used: set[int],
) -> list[int]:
    """Replace reused ids/stems when the shortlist still has a fresh option."""
    if not avoid_ids and not avoid_stems:
        return cleaned
    by_id = {}
    for x in shortlist:
        try:
            by_id[_item_eid(x)] = x
        except (TypeError, ValueError, KeyError, AttributeError):
            continue
    fresh = [
        _item_eid(x)
        for x in shortlist
        if not _item_is_avoided(x, avoid_ids, avoid_stems)
    ]
    taken = set(extra_used)
    out: list[int] = []
    for eid in cleaned:
        item = by_id.get(eid)
        if item is not None and _item_is_avoided(item, avoid_ids, avoid_stems):
            alt = next((f for f in fresh if f not in taken and f not in out), None)
            if alt is not None:
                out.append(alt)
                taken.add(alt)
                continue
        out.append(eid)
        taken.add(eid)
    return out


def _replace_same_day_duplicates(
    cleaned: list[int],
    shortlist: list,
    *,
    used: set[int],
    count_max: int,
) -> list[int]:
    """Swap ids already used in this session; reuse only when the shortlist is exhausted."""
    allowed = _shortlist_ids(shortlist)
    fresh = [
        eid
        for x in shortlist
        for eid in (_item_eid(x),)
        if eid in allowed and eid not in used
    ]
    out: list[int] = []
    taken = set(used)
    for eid in cleaned:
        if eid in taken:
            alt = next((f for f in fresh if f not in taken and f not in out), None)
            if alt is not None:
                out.append(alt)
                taken.add(alt)
                continue
        out.append(eid)
        taken.add(eid)
    while len(out) < count_max:
        alt = next((f for f in fresh if f not in out), None)
        if alt is None:
            break
        out.append(alt)
    return out[: max(count_max, 0)] if count_max else out


def _parse_llm_slot_ids(raw: dict[str, Any]) -> list[int]:
    ids: list[int] = []
    seen: set[int] = set()
    values = list(raw.get("exercise_ids") or [])
    values.extend(
        item.get("exercise_id")
        for item in (raw.get("exercises") or [])
        if isinstance(item, dict)
    )
    for x in values:
        try:
            eid = int(x)
        except (TypeError, ValueError):
            continue
        if eid not in seen:
            seen.add(eid)
            ids.append(eid)
    if raw.get("exercise_id") is not None:
        try:
            eid = int(raw.get("exercise_id"))
        except (TypeError, ValueError):
            eid = None
        if eid is not None and eid not in seen:
            ids.append(eid)
    return ids


def _llm_dose_by_exercise(llm_day: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    """Collect optional model doses; exercise selection is validated separately."""
    out: dict[str, dict[str, Any]] = {}
    for container in ("slots", "blocks"):
        for raw in (llm_day or {}).get(container) or []:
            if not isinstance(raw, dict):
                continue
            proposals = list(raw.get("exercises") or raw.get("prescriptions") or [])
            if raw.get("exercise_id") is not None and raw.get("sets") is not None:
                proposals.append(raw)
            for proposal in proposals:
                if not isinstance(proposal, dict):
                    continue
                try:
                    eid = int(proposal.get("exercise_id"))
                except (TypeError, ValueError):
                    continue
                if proposal.get("sets") is not None and proposal.get("reps") is not None:
                    rest = proposal.get("rest_seconds")
                    if rest is None:
                        rest = proposal.get("rest")
                    dose = {
                        "sets": proposal.get("sets"),
                        "reps": proposal.get("reps"),
                    }
                    if rest is not None:
                        dose["rest_seconds"] = rest
                    load_kg = proposal.get("load_kg")
                    if load_kg is None:
                        load_kg = proposal.get("kg")
                    if load_kg is not None:
                        try:
                            dose["load_kg"] = float(load_kg)
                        except (TypeError, ValueError):
                            pass
                    note = proposal.get("load_note_vi") or proposal.get("note_vi")
                    if note:
                        dose["load_note_vi"] = str(note).strip()
                    out[str(eid)] = dose
    return out


def _llm_picks_by_slot(
    llm_day: dict[str, Any] | None,
    prompt_slots: list[dict[str, Any]],
) -> dict[str, list[int]]:
    """Map LLM output onto slot keys. Accepts slots[] or legacy blocks[]."""
    out: dict[str, list[int]] = {}
    for raw in (llm_day or {}).get("slots") or []:
        if not isinstance(raw, dict):
            continue
        key = str(raw.get("key") or raw.get("slot_key") or "")
        if key:
            out[key] = _parse_llm_slot_ids(raw)
    if out:
        return out
    by_block: dict[str, list[int]] = {}
    for b in (llm_day or {}).get("blocks") or []:
        if not isinstance(b, dict):
            continue
        key = str(b.get("block_key") or "")
        if not key:
            continue
        by_block[key] = _parse_llm_slot_ids(b)
    cursor: dict[str, int] = {}
    for spec in prompt_slots:
        skey = str(spec.get("key") or "")
        block = str(spec.get("block_key") or "")
        n = max(0, int(spec.get("pick") or 1))
        src = by_block.get(block) or []
        start = cursor.get(block, 0)
        out[skey] = src[start : start + n]
        cursor[block] = start + n
    return out


def _fold_slot_picks(
    prompt_slots: list[dict[str, Any]],
    slot_picks: dict[str, list[int]],
) -> dict[str, list[int]]:
    out: dict[str, list[int]] = {}
    for spec in prompt_slots:
        block = str(spec.get("block_key") or "")
        key = str(spec.get("key") or "")
        ids = list(slot_picks.get(key) or [])
        if block:
            out.setdefault(block, []).extend(ids)
    out[SLOT_PICKS_KEY] = {k: list(v) for k, v in slot_picks.items()}
    return out


def _next_pool_id(
    pool: list,
    *,
    used: set[int],
    avoid_ids: set[int],
    avoid_stems: set[str],
    allow_avoided: bool,
) -> int | None:
    for x in pool:
        try:
            eid = _item_eid(x)
        except (TypeError, ValueError, KeyError, AttributeError):
            continue
        if eid in used:
            continue
        if not allow_avoided and _item_is_avoided(x, avoid_ids, avoid_stems):
            continue
        return eid
        return None


def validate_slot_picks(
    prompt_slots: list[dict[str, Any]],
    llm_day: dict[str, Any] | None,
    *,
    split_role: str | None = None,
    avoid_ids: set[int] | frozenset[int] | list[int] | None = None,
    avoid_stems: set[str] | frozenset[str] | list[str] | None = None,
    experience_level: int = 2,
    skill_signals: Any = None,
    phase_i: int | None = None,
) -> dict[str, list[int]]:
    """Keep GPT ids that sit in the slot pool. Fill only the missing slot from that pool."""
    from app.services.workout_generation.coverage import family_of
    from app.services.workout_generation.session_templates import (
        is_decline_chest_compound,
        is_free_weight_chest_press,
        is_triceps_press_imposter,
        slot_allows_week_b_swap,
    )

    avoid_eids = _avoid_id_set(avoid_ids)
    avoid_stem_keys = _avoid_stem_set(avoid_stems)
    raw = _llm_picks_by_slot(llm_day, prompt_slots)
    used: set[int] = set()
    slot_picks: dict[str, list[int]] = {}
    seen_compound_fams: set[str] = set()
    level = int(experience_level or 2)

    for spec in prompt_slots:
        key = str(spec.get("key") or "")
        n = max(0, int(spec.get("pick") or 1))
        required = bool(spec.get("required", True))
        pool = list(spec.get("pool") or [])
        if key in {"h_press", "extra_press"}:
            pool = [
                x
                for x in pool
                if not is_decline_chest_compound(x) and not is_triceps_press_imposter(x)
            ]
        allowed = _shortlist_ids(pool)
        if n <= 0:
            slot_picks[key] = []
            continue
        if not pool:
            if required:
                raise OpenAIPickError(f"Kho bài không đủ cho slot `{key}`.")
            slot_picks[key] = []
            continue

        chosen: list[int] = []
        invented = False
        for eid in raw.get(key) or []:
            if eid not in allowed:
                invented = True
                continue
            if eid in used or eid in chosen:
                continue
            chosen.append(eid)
            if len(chosen) >= n:
                break
        chosen = _swap_avoided_picks(
            chosen,
            pool,
            avoid_ids=avoid_eids,
            avoid_stems=avoid_stem_keys,
            extra_used=used,
        )
        chosen = _replace_same_day_duplicates(
            chosen, pool, used=used, count_max=n
        )
        if skill_signals is not None and phase_i is not None:
            from app.services.workout_generation.skill_gate import replace_gated_ids

            chosen = replace_gated_ids(chosen, pool, phase_i, skill_signals)
        is_compound_slot = not slot_allows_week_b_swap(spec)
        if is_compound_slot and chosen:
            by_id = {}
            for x in pool:
                try:
                    by_id[_item_eid(x)] = x
                except (TypeError, ValueError, KeyError, AttributeError):
                    continue
            replaced: list[int] = []
            for eid in chosen:
                item = by_id.get(eid)
                fam = family_of(
                    (_item_pattern(item) if item is not None else None)
                )
                if fam and fam in seen_compound_fams:
                    alt = None
                    for x in pool:
                        try:
                            xid = _item_eid(x)
                        except (TypeError, ValueError, KeyError, AttributeError):
                            continue
                        if xid in used or xid in replaced or xid in chosen:
                            continue
                        xfam = family_of(_item_pattern(x))
                        if xfam and xfam in seen_compound_fams:
                            continue
                        if _item_is_avoided(x, avoid_eids, avoid_stem_keys):
                            continue
                        alt = xid
                        fam = xfam
                        break
                    if alt is not None:
                        replaced.append(alt)
                        if fam:
                            seen_compound_fams.add(fam)
                        continue
                replaced.append(eid)
                if fam:
                    seen_compound_fams.add(fam)
            chosen = replaced

        if key in {"h_press", "extra_press"} and level >= 2 and chosen:
            fw_ids: list[int] = []
            by_id: dict[int, Any] = {}
            for x in pool:
                try:
                    xid = _item_eid(x)
                except (TypeError, ValueError, KeyError, AttributeError):
                    continue
                by_id[xid] = x
                if is_free_weight_chest_press(x):
                    fw_ids.append(xid)
            if fw_ids:
                swapped: list[int] = []
                for eid in chosen:
                    item = by_id.get(eid)
                    if item is not None and is_free_weight_chest_press(item):
                        swapped.append(eid)
                        continue
                    alt = next(
                        (
                            fid
                            for fid in fw_ids
                            if fid not in used and fid not in swapped
                        ),
                        None,
                    )
                    swapped.append(alt if alt is not None else eid)
                chosen = swapped

        while len(chosen) < n:
            alt = _next_pool_id(
                pool,
                used=used | set(chosen),
                avoid_ids=avoid_eids,
                avoid_stems=avoid_stem_keys,
                allow_avoided=False,
            )
            if alt is None:
                alt = _next_pool_id(
                    pool,
                    used=used | set(chosen),
                    avoid_ids=avoid_eids,
                    avoid_stems=avoid_stem_keys,
                    allow_avoided=True,
                )
            if alt is None:
                break
            chosen.append(alt)

        if len(chosen) < n and required:
            raise OpenAIPickError(
                f"OpenAI chọn sai số bài cho slot `{key}` "
                f"(cần đúng {n}, nhận {len(chosen)})."
            )
        if invented and not chosen and required:
            raise OpenAIPickError(
                f"OpenAI chọn id không có trong pool của slot `{key}`."
            )
        used.update(chosen[:n])
        slot_picks[key] = chosen[:n]

    return _fold_slot_picks(prompt_slots, slot_picks)


def _item_pattern(item: object) -> str | None:
    if isinstance(item, dict):
        raw = item.get("pattern") or item.get("movement_pattern")
    else:
        raw = getattr(item, "movement_pattern", None)
    pat = str(raw or "").strip().lower()
    return pat or None


def merge_week_b_isolation_picks(
    picks_a: dict[str, list[int]],
    llm_b_day: dict[str, Any] | None,
    day_blocks: list[dict],
    *,
    split_role: str | None = None,
    focus_slugs: frozenset[str] | None = None,
    avoid_ids: set[int] | frozenset[int] | list[int] | None = None,
    avoid_stems: set[str] | frozenset[str] | list[str] | None = None,
    slots: list[dict[str, Any]] | None = None,
) -> dict[str, list[int]]:
    """Keep week-A compounds/warmup; swap isolation if week_b supplies valid ids."""
    if slots:
        return _merge_week_b_slots(
            picks_a,
            llm_b_day,
            day_blocks,
            slots,
            split_role=split_role,
            avoid_ids=avoid_ids,
            avoid_stems=avoid_stems,
        )
    merged = _copy_picks(picks_a)
    if not llm_b_day:
        return merged
    by_key: dict[str, list[int]] = {}
    for b in llm_b_day.get("blocks") or []:
        key = str(b.get("block_key") or "")
        if key not in ISO_SWAP_KEYS:
            continue
        ids: list[int] = []
        for x in b.get("exercise_ids") or []:
            try:
                ids.append(int(x))
            except (TypeError, ValueError):
                continue
        if key:
            by_key[key] = ids
    if not by_key:
        return merged
    iso_blocks = [
        b
        for b in day_blocks
        if b.get("pick") and str(b.get("block_key")) in ISO_SWAP_KEYS
    ]
    if not iso_blocks:
        return merged
    try:
        validated = validate_openai_picks(
            iso_blocks,
            by_key,
            split_role=split_role,
            avoid_ids=avoid_ids,
            avoid_stems=avoid_stems,
        )
    except OpenAIPickError:
        return _copy_picks(picks_a)
    changed = False
    for key, ids in validated.items():
        if ids and ids != merged.get(key):
            merged[key] = list(ids)
            changed = True
    if not changed:
        return _copy_picks(picks_a)
    try:
        merged = repair_strength_picks(
            day_blocks, merged, split_role=split_role, focus_slugs=focus_slugs
        )
        merged = fill_mobility_picks(day_blocks, merged, split_role=split_role)
    except OpenAIPickError:
        return _copy_picks(picks_a)
    for key, ids in (picks_a or {}).items():
        if str(key).startswith("_"):
            merged[key] = copy.deepcopy(ids)
            continue
        if str(key) not in ISO_SWAP_KEYS:
            merged[key] = list(ids)
    return merged


def _merge_week_b_slots(
    picks_a: dict[str, list[int]],
    llm_b_day: dict[str, Any] | None,
    day_blocks: list[dict],
    slots: list[dict[str, Any]],
    *,
    split_role: str | None,
    avoid_ids: set[int] | frozenset[int] | list[int] | None,
    avoid_stems: set[str] | frozenset[str] | list[str] | None,
) -> dict[str, list[int]]:
    from app.services.workout_generation.session_templates import slot_allows_week_b_swap

    a_slots = dict((picks_a or {}).get(SLOT_PICKS_KEY) or {})
    if not a_slots and not llm_b_day:
        return _copy_picks(picks_a)
    b_raw = _llm_picks_by_slot(llm_b_day, slots) if llm_b_day else {}
    avoid_eids = _avoid_id_set(avoid_ids)
    avoid_stem_keys = _avoid_stem_set(avoid_stems)
    used: set[int] = set()
    merged_slots: dict[str, list[int]] = {}
    for spec in slots:
        key = str(spec.get("key") or "")
        n = max(0, int(spec.get("pick") or 1))
        pool = list(spec.get("pool") or [])
        allowed = _shortlist_ids(pool)
        keep = [int(x) for x in (a_slots.get(key) or []) if int(x)]
        if not slot_allows_week_b_swap(spec):
            chosen = [eid for eid in keep if eid in allowed or not allowed][:n]
            merged_slots[key] = chosen
            used.update(chosen)
            continue
        b_ids = [
            eid
            for eid in (b_raw.get(key) or [])
            if eid in allowed and eid not in used and eid not in keep
        ]
        chosen: list[int] = []
        for eid in b_ids:
            if eid not in chosen:
                chosen.append(eid)
            if len(chosen) >= n:
                break
        if chosen:
            chosen = _swap_avoided_picks(
                chosen,
                pool,
                avoid_ids=avoid_eids,
                avoid_stems=avoid_stem_keys,
                extra_used=used | set(keep),
            )
        while len(chosen) < n:
            alt = _next_pool_id(
                pool,
                used=used | set(chosen) | set(keep),
                avoid_ids=avoid_eids,
                avoid_stems=avoid_stem_keys,
                allow_avoided=False,
            )
            if alt is None:
                break
            chosen.append(alt)
        # A small pool may not have enough replacements for every picked id.
        for eid in keep:
            if len(chosen) >= n:
                break
            if eid not in used and eid not in chosen:
                chosen.append(eid)
        while len(chosen) < n:
            alt = _next_pool_id(
                pool,
                used=used | set(chosen),
                avoid_ids=avoid_eids,
                avoid_stems=avoid_stem_keys,
                allow_avoided=True,
            )
            if alt is None:
                break
            chosen.append(alt)
        merged_slots[key] = chosen[:n]
        used.update(merged_slots[key])
    folded = _fold_slot_picks(slots, merged_slots)
    for key, ids in (picks_a or {}).items():
        if str(key).startswith("_"):
            continue
        if key in _MOBILITY_KEYS:
            folded[key] = list(ids)
    try:
        folded = fill_mobility_picks(day_blocks, folded, split_role=split_role)
    except OpenAIPickError:
        return _copy_picks(picks_a)
    folded[DOSE_PICKS_KEY] = copy.deepcopy((picks_a or {}).get(DOSE_PICKS_KEY) or {})
    return folded


def clamp_pick_count(count_max: int, n_allowed: int) -> int:
    """Lower recipe count when the shortlist is smaller. Empty catalog is the caller's problem."""
    if count_max <= 0:
        return 0
    if n_allowed <= 0:
        return int(count_max)
    return min(int(count_max), int(n_allowed))


def _shortlist_ids(shortlist: list) -> set[int]:
    out: set[int] = set()
    for x in shortlist:
        try:
            if isinstance(x, dict):
                out.add(int(x["id"]))
            else:
                out.add(int(x.id))
        except (TypeError, ValueError, KeyError, AttributeError):
            continue
    return out


def validate_openai_picks(
    day_blocks: list[dict],
    picks: dict[str, list[int]],
    *,
    split_role: str | None = None,
    avoid_ids: set[int] | frozenset[int] | list[int] | None = None,
    avoid_stems: set[str] | frozenset[str] | list[str] | None = None,
) -> dict[str, list[int]]:
    """
    Validate ids ⊆ shortlist. Required blocks must reach count_max; if the LLM
    under-picks, fill remaining slots from the shortlist. Empty shortlist still
    raises. Duplicate strength ids within the day raise.
    Reused avoid_ids/stems are swapped when a fresh shortlist option exists.
    """
    from app.services.workout_generation.coverage import diversified_pick

    result: dict[str, list[int]] = {}
    strength_used: set[int] = set()
    avoid_eids = _avoid_id_set(avoid_ids)
    avoid_stem_keys = _avoid_stem_set(avoid_stems)

    for block in day_blocks:
        if not block.get("pick"):
            continue
        key = str(block["block_key"])
        count_max = int(block.get("count_max") or 0)
        optional = bool(block.get("is_optional"))
        shortlist = list(block.get("shortlist") or [])
        allowed = _shortlist_ids(shortlist)

        raw = list(picks.get(key) or [])
        cleaned: list[int] = []
        invented = False
        for eid in raw:
            try:
                eid_i = int(eid)
            except (TypeError, ValueError):
                continue
            if eid_i not in allowed:
                invented = True
                continue
            if eid_i not in cleaned:
                cleaned.append(eid_i)

        if count_max <= 0:
            result[key] = []
            continue

        if optional and not shortlist:
            result[key] = []
            continue

        cleaned = cleaned[:count_max]
        if key in _STRENGTH_KEYS:
            cleaned = _swap_avoided_picks(
                cleaned,
                shortlist,
                avoid_ids=avoid_eids,
                avoid_stems=avoid_stem_keys,
                extra_used=strength_used,
            )
            cleaned = _replace_same_day_duplicates(
                cleaned,
                shortlist,
                used=strength_used,
                count_max=count_max if not optional else max(len(cleaned), 0),
            )

        if optional:
            result[key] = cleaned
            if key in _STRENGTH_KEYS:
                strength_used.update(cleaned)
            continue

        if key in _MOBILITY_KEYS:
            result[key] = cleaned
            continue

        if not allowed:
            raise OpenAIPickError(
                f"Kho bài không đủ cho block `{key}` (cần {count_max}, có 0)."
            )
        if invented:
            raise OpenAIPickError(
                f"OpenAI chọn id không có trong shortlist của block `{key}`."
            )
        count_max = clamp_pick_count(count_max, len(allowed))
        cleaned = cleaned[:count_max]
        if len(cleaned) < count_max:
            fresh_sl = [
                x
                for x in shortlist
                if not _item_is_avoided(x, avoid_eids, avoid_stem_keys)
            ]
            used_now = set(cleaned) | strength_used
            extras = diversified_pick(
                fresh_sl or shortlist,
                count=count_max - len(cleaned),
                split_role=split_role,
                used_ids=used_now,
                block_key=key,
            )
            if len(extras) < count_max - len(cleaned) and fresh_sl:
                extras = extras + diversified_pick(
                    shortlist,
                    count=count_max - len(cleaned) - len(extras),
                    split_role=split_role,
                    used_ids=used_now | set(extras),
                    block_key=key,
                )
            for eid in extras:
                if eid in allowed and eid not in cleaned and eid not in strength_used:
                    cleaned.append(eid)
                if len(cleaned) >= count_max:
                    break
            if len(cleaned) < count_max:
                for x in shortlist:
                    try:
                        eid = _item_eid(x)
                    except (TypeError, ValueError, KeyError, AttributeError):
                        continue
                    if eid in allowed and eid not in cleaned:
                        cleaned.append(eid)
                    if len(cleaned) >= count_max:
                        break
            cleaned = cleaned[:count_max]
        if len(cleaned) != count_max:
            raise OpenAIPickError(
                f"OpenAI chọn sai số bài cho block `{key}` "
                f"(cần đúng {count_max}, nhận {len(cleaned)})."
            )

        if key in _STRENGTH_KEYS:
            strength_used.update(cleaned)

        result[key] = cleaned

    return result


def fill_mobility_picks(
    day_blocks: list[dict],
    picks: dict[str, list[int]],
    *,
    split_role: str | None = None,
) -> dict[str, list[int]]:
    """Fill leftover warmup/cooldown slots and replace poor LLM mobility picks. Never invents ids."""
    from app.services.workout_generation.split_map import mobility_match_rank

    out: dict[str, Any] = {}
    for k, v in picks.items():
        if k == SLOT_PICKS_KEY:
            out[k] = v
            continue
        out[k] = list(v)
    trained = _trained_slugs_from_picks(day_blocks, out)
    used: set[int] = set()
    for key, ids in out.items():
        if str(key).startswith("_"):
            continue
        used.update(ids or [])

    for block in day_blocks:
        if not block.get("pick"):
            continue
        key = str(block["block_key"])
        if key not in _MOBILITY_KEYS:
            continue
        shortlist = list(block.get("shortlist") or [])
        allowed = _shortlist_ids(shortlist)
        n = clamp_pick_count(int(block.get("count_max") or 0), len(allowed))
        if n <= 0:
            out[key] = []
            continue
        cur = [eid for eid in (out.get(key) or []) if eid in allowed]
        cooldown = key == "cooldown"

        def _rank(item: object) -> int:
            return mobility_match_rank(
                muscle_slug=_item_muscle(item),
                name_vi=_item_name(item),
                split_role=split_role,
                cooldown=cooldown,
                trained_slugs=trained,
            )

        ranked = sorted(shortlist, key=lambda x: (_rank(x), _item_eid(x)))
        by_eid = {_item_eid(x): x for x in shortlist}
        for eid in list(cur):
            used.discard(eid)
        selected: list[int] = []
        for eid in cur:
            item = by_eid.get(eid)
            r = _rank(item) if item is not None else 99
            if item is not None and r <= 1:
                selected.append(eid)
                continue
            replacement = None
            for x in ranked:
                xid = _item_eid(x)
                if xid in used or xid in selected:
                    continue
                if _rank(x) < r:
                    replacement = xid
                    break
            if replacement is not None:
                selected.append(replacement)
            elif item is not None:
                selected.append(eid)
        cur = selected
        used.update(cur)
        for x in ranked:
            if len(cur) >= n:
                break
            eid = _item_eid(x)
            if eid in used or eid in cur:
                continue
            cur.append(eid)
            used.add(eid)
        out[key] = cur[:n]
        used.update(out[key])
    return out


def repair_strength_picks(
    day_blocks: list[dict],
    picks: dict[str, list[int]],
    *,
    split_role: str | None = None,
    focus_slugs: frozenset[str] | None = None,
) -> dict[str, list[int]]:
    """Swap compound/accessory ids inside shortlists to cover quota/pattern gaps."""
    from app.services.workout_generation.coverage import repair_day_coverage
    from app.services.workout_generation.muscle_quotas import repair_muscle_quotas

    out = repair_muscle_quotas(
        day_blocks, picks, split_role=split_role, focus_slugs=focus_slugs
    )
    return repair_day_coverage(day_blocks, out, split_role=split_role)


def picks_from_llm_day(
    llm_day: dict[str, Any] | None,
    day_blocks: list[dict],
    *,
    split_role: str | None = None,
    focus_slugs: frozenset[str] | None = None,
    avoid_ids: set[int] | frozenset[int] | list[int] | None = None,
    avoid_stems: set[str] | frozenset[str] | list[str] | None = None,
    slots: list[dict[str, Any]] | None = None,
    experience_level: int = 2,
    skill_signals: Any = None,
    phase_i: int | None = None,
) -> dict[str, list[int]]:
    """Parse one LLM day into block picks, then mobility fill. Slot path skips quota rewrite."""
    if not llm_day:
        raise OpenAIPickError("OpenAI thiếu dữ liệu ngày trong lịch.")

    role = split_role or (str(llm_day.get("split_role") or "") or None)
    if slots:
        picks = validate_slot_picks(
            slots,
            llm_day,
            split_role=role,
            avoid_ids=avoid_ids,
            avoid_stems=avoid_stems,
            experience_level=experience_level,
            skill_signals=skill_signals,
            phase_i=phase_i,
        )
        slot_picks = dict(picks.get(SLOT_PICKS_KEY) or {})
        # Some compact slot schemas intentionally omit a whole required block
        # (for example L1 Legs only exposes the squat slot). Fill that block
        # deterministically from its validated shortlist before strict assembly.
        picks = validate_openai_picks(
            day_blocks,
            picks,
            split_role=role,
            avoid_ids=avoid_ids,
            avoid_stems=avoid_stems,
        )
        picks[SLOT_PICKS_KEY] = slot_picks
        picks = fill_mobility_picks(day_blocks, picks, split_role=role)
        picks[DOSE_PICKS_KEY] = _llm_dose_by_exercise(llm_day)
        return picks

    by_key: dict[str, list[int]] = {}
    for b in llm_day.get("blocks") or []:
        key = str(b.get("block_key") or "")
        ids: list[int] = []
        raw_ids = list(b.get("exercise_ids") or [])
        raw_ids.extend(
            item.get("exercise_id")
            for item in (b.get("exercises") or [])
            if isinstance(item, dict)
        )
        for x in raw_ids:
            try:
                ids.append(int(x))
            except (TypeError, ValueError):
                continue
        if key:
            by_key[key] = ids
    picks = validate_openai_picks(
        day_blocks,
        by_key,
        split_role=role,
        avoid_ids=avoid_ids,
        avoid_stems=avoid_stems,
    )
    picks = repair_strength_picks(
        day_blocks, picks, split_role=role, focus_slugs=focus_slugs
    )
    picks = fill_mobility_picks(day_blocks, picks, split_role=role)
    picks[DOSE_PICKS_KEY] = _llm_dose_by_exercise(llm_day)
    return picks


PROMPT_SHORTLIST_CAP = 20
PICK_BATCH_SIZE = 2
CHEST_COMPOUND_HINT = (
    "Chest compounds: L1 machine; L2+ barbell or dumbbell. Only flat and incline. "
    "Never decline. First chest slot flat; second incline if present."
)
CHEST_COMPOUND_HINT_VI = (
    "Ngực compound: L1 máy; L2+ tạ đòn/tạ đơn. Chỉ nằm và dốc lên, không dốc xuống. "
    "Slot ngực 1 nằm, slot 2 (nếu có) dốc lên."
)
HOME_CHEST_COMPOUND_HINT = (
    "Home chest: push-up, dumbbell, or band press. Only flat and incline. Never decline. "
    "Mix selected implements — do not use only dumbbells if bands are in the pools."
)
HOME_GEAR_HINT = (
    "Home with equipment: use every selected implement across the week. "
    "Pools are ordered gear-first; items marked bw are bodyweight fallback — pick them "
    "only when every gear option in that slot is already used this week or in avoid_ids. "
    "Back/pull: prefer tube band (resistance-band-2) rows and pulldowns. "
    "Legs: prefer loop/mini band (resistance-band-1) squats and glutes. "
    "Unassisted pull-up/chin-up: only if profile.home_l1_bar_hint or skill_prompt_vi allows it; "
    "never pick dip or muscle-up at L1. Prefer assisted, scapular, inverted/australian/ring row otherwise. "
    "Home no-equipment Pull is back + core bodyweight (superman, bird-dog, Y-T-W), "
    "not gym pull-ups or rows. Lift-day cardio/conditioning: only Shadow Boxing, Jumping Jack, "
    "Jump Rope, Running Intervals (multiple sets × seconds), or Hiking / Trail Run "
    "(1 set = leftover minutes). Never burpees, high knees, or mountain climbers."
)


def compact_day_for_prompt(
    day: dict[str, Any],
    *,
    cap: int | None = PROMPT_SHORTLIST_CAP,
    avoid_ids: set[int] | frozenset[int] | list[int] | None = None,
    avoid_stems: set[str] | frozenset[str] | list[str] | None = None,
) -> dict[str, Any]:
    """Prepare the GPT payload. Slot pools are sent in full; leftover blocks may be capped."""
    avoid_eids = _avoid_id_set(avoid_ids)
    avoid_stem_keys = _avoid_stem_set(avoid_stems)
    out = {k: v for k, v in day.items() if k not in {"blocks", "slots"}}

    def _order_items(items: list) -> list:
        if not (avoid_eids or avoid_stem_keys):
            return list(items)
        return sorted(
            list(items),
            key=lambda x: (
                1 if _item_is_avoided(x, avoid_eids, avoid_stem_keys) else 0,
            ),
        )

    slots_out: list[dict[str, Any]] = []
    for spec in day.get("slots") or []:
        ns = {k: v for k, v in spec.items() if k != "pool"}
        ns["pool"] = _order_items(list(spec.get("pool") or []))
        slots_out.append(ns)
    if slots_out:
        out["slots"] = slots_out
        if any(str(s.get("key") or "") in {"h_press", "extra_press"} for s in slots_out):
            loc = str(day.get("location") or out.get("location") or "").strip().lower()
            out["chest_compound_hint"] = (
                HOME_CHEST_COMPOUND_HINT if loc == "home" else CHEST_COMPOUND_HINT
            )

    skip_blocks = frozenset()
    if slots_out:
        skip_blocks = _STRENGTH_KEYS | {"core", "cardio"}
    blocks = []
    for b in day.get("blocks") or []:
        key = str(b.get("block_key") or "")
        if key in skip_blocks:
            continue
        nb = {k: v for k, v in b.items() if k != "shortlist"}
        items = _order_items(list(b.get("shortlist") or []))
        if cap is None:
            nb["shortlist"] = items
        else:
            nb["shortlist"] = items[: max(1, int(cap))] if items else []
        blocks.append(nb)
    if blocks:
        out["blocks"] = blocks
    return out


def pick_with_openai(
    week_payload: list[dict[str, Any]],
    *,
    profile: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """
    week_payload: [{day_index, split_role, label_vi, blocks: [...]}]
    Picks in batches of two days. Returns days with blocks[{block_key, exercise_ids}].
    Raises OpenAIPickError on any failure (hard fail — no silent fallback).
    """
    settings = get_settings()
    if not bool(getattr(settings, "workout_gen_use_openai", True)):
        raise OpenAIPickError(
            "Gen lịch yêu cầu OpenAI chọn bài (WORKOUT_GEN_USE_OPENAI=true)."
        )
    if not (settings.openai_api_key or "").strip():
        raise OpenAIPickError(
            "Thiếu OPENAI_API_KEY — không thể tạo lịch tập. Thêm key rồi thử lại."
        )

    system_blocks = (
        "You are a strength coach for TAPTOT (Vietnamese beginners). "
        "Pick exercises ONLY from each block's shortlist ids. "
        "For every block with pick=true that is not optional, choose exactly count_max "
        "distinct exercise_ids from that block's shortlist. "
        "Optional blocks may use [] if shortlist is empty, otherwise up to count_max. "
        "Do not invent ids or change count_max. For every selected id, propose sets/reps "
        "inside that candidate's dose_bounds. "
        "Prefer variety: avoid exercise_ids listed in avoid_ids when shortlists allow. "
        "Never pick two main lifts with the same movement pattern or the same family "
        "(e.g. two step-ups or two lunges) in one session. "
        "Respond with JSON covering every day in the user payload: "
        '{"days":[{"day_index":0,"blocks":[{"block_key":"compound","exercises":'
        '[{"exercise_id":1,"sets":3,"reps":"8-10"}]}]}]}'
    )
    system_slots = (
        "You are a strength coach for TAPTOT (Vietnamese beginners). "
        "Each day has slots. Pick exercises ONLY from that slot's pool ids. "
        "For every required slot, choose exactly `pick` distinct exercise_ids from that slot's pool. "
        "Optional slots may use []. Do not invent ids or change pick counts. "
        "For every selected id, propose sets/reps inside that candidate's dose_bounds. "
        "Prefer variety: avoid exercise_ids listed in avoid_ids when the slot pool still has another option. "
        "Never pick two main lifts with the same movement pattern or the same family "
        "(e.g. two step-ups or two lunges) in one session. "
        "Chest compounds: L1 machine; L2+ barbell or dumbbell. Only flat and incline. "
        "Never decline. First chest slot flat; second incline if present. "
        "Respond with JSON covering every day: "
        '{"days":[{"day_index":0,"slots":[{"key":"h_press","exercises":'
        '[{"exercise_id":10,"sets":3,"reps":"8-10"}]}]}]}'
    )
    home_system_slots = (
        "You are a strength coach for TAPTOT (Vietnamese beginners). "
        "Each day has slots. Pick exercises ONLY from that slot's pool ids. "
        "For every required slot, choose exactly `pick` distinct exercise_ids from that slot's pool. "
        "Optional slots may use []. Do not invent ids or change pick counts. "
        "For every selected id, propose sets/reps inside that candidate's dose_bounds. "
        "Prefer variety: avoid exercise_ids listed in avoid_ids when the slot pool still has another option. "
        "Never pick two main lifts with the same movement pattern or the same family "
        "(e.g. two step-ups or two lunges) in one session. "
        f"{HOME_CHEST_COMPOUND_HINT} {HOME_GEAR_HINT} "
        "Respond with JSON covering every day: "
        '{"days":[{"day_index":0,"slots":[{"key":"h_press","exercises":'
        '[{"exercise_id":10,"sets":3,"reps":"8-10"}]}]}]}'
    )
    use_slots = any(d.get("slots") for d in week_payload)
    loc = str((profile or {}).get("location") or "").strip().lower()
    if use_slots and loc == "home":
        system = home_system_slots
    elif use_slots:
        system = system_slots
    else:
        system = system_blocks
    max_out = min(8192, max(2048, int(settings.openai_max_tokens or 2048)))
    if not use_slots:
        max_out = min(2048, int(settings.openai_max_tokens or 2048))

    def _request_one(body: dict[str, Any]) -> list[dict[str, Any]]:
        return _parse_llm_days(_openai_chat_content(body))

    out_by_idx: dict[int, dict[str, Any]] = {}
    avoid_ids: list[int] = []
    retry_left = 1

    def _collect_avoid(chosen: dict[str, Any]) -> None:
        for b in chosen.get("blocks") or []:
            if str(b.get("block_key") or "") not in _STRENGTH_KEYS:
                continue
            for raw in b.get("exercise_ids") or []:
                try:
                    avoid_ids.append(int(raw))
                except (TypeError, ValueError):
                    continue
        for s in chosen.get("slots") or []:
            if not isinstance(s, dict):
                continue
            for raw in s.get("exercise_ids") or []:
                try:
                    avoid_ids.append(int(raw))
                except (TypeError, ValueError):
                    continue
            if s.get("exercise_id") is not None:
                try:
                    avoid_ids.append(int(s.get("exercise_id")))
                except (TypeError, ValueError):
                    continue

    def _run_batch(days: list[dict[str, Any]]) -> None:
        nonlocal retry_left
        compact = [
            compact_day_for_prompt(
                {**d, "location": loc} if loc else d,
                cap=None if d.get("slots") else PROMPT_SHORTLIST_CAP,
                avoid_ids=avoid_ids,
            )
            for d in days
        ]
        user_obj: dict[str, Any] = {"days": compact, "avoid_ids": avoid_ids}
        if profile:
            user_obj["profile"] = profile
        body = {
            "model": settings.openai_model,
            "temperature": min(0.4, float(settings.openai_temperature or 0.4)),
            "max_completion_tokens": max_out,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(user_obj, ensure_ascii=False)},
            ],
        }
        parsed = _request_one(body)
        if not parsed:
            raise OpenAIPickError(OPENAI_PICK_FAIL_VI)
        by_idx: dict[int, dict[str, Any]] = {}
        for d in parsed:
            try:
                by_idx[int(d.get("day_index"))] = d
            except (TypeError, ValueError):
                continue
        if len(days) == 1 and parsed and int(days[0].get("day_index")) not in by_idx:
            try:
                want = int(days[0].get("day_index"))
            except (TypeError, ValueError):
                want = 0
            by_idx[want] = {**parsed[0], "day_index": want}
        missing: list[dict[str, Any]] = []
        for day in days:
            try:
                want = int(day.get("day_index"))
            except (TypeError, ValueError):
                continue
            chosen = by_idx.get(want)
            if chosen is None:
                missing.append(day)
                continue
            out_by_idx[want] = chosen
            _collect_avoid(chosen)
        if missing:
            if retry_left <= 0:
                raise OpenAIPickError(
                    "OpenAI trả thiếu ngày trong lịch. Thử tạo lại."
                )
            retry_left -= 1
            _run_batch(missing[:1])
            if len(missing) > 1:
                raise OpenAIPickError(
                    "OpenAI trả thiếu ngày trong lịch. Thử tạo lại."
                )

    for i in range(0, len(week_payload), PICK_BATCH_SIZE):
        _run_batch(week_payload[i : i + PICK_BATCH_SIZE])

    out_days: list[dict[str, Any]] = []
    for day in week_payload:
        try:
            want = int(day.get("day_index"))
        except (TypeError, ValueError):
            continue
        if want not in out_by_idx:
            raise OpenAIPickError(
                "OpenAI trả thiếu ngày trong lịch. Thử tạo lại."
            )
        out_days.append(out_by_idx[want])
    return out_days


def _wanted_day_indexes(week_payload: list[dict[str, Any]]) -> list[int]:
    out: list[int] = []
    for day in week_payload:
        try:
            out.append(int(day.get("day_index")))
        except (TypeError, ValueError):
            continue
    return out


def _index_llm_days(
    parsed: list[Any],
    week_payload: list[dict[str, Any]],
) -> dict[int, dict[str, Any]]:
    """Map LLM days onto payload day_index.

    GPT often returns 1-based indexes (1,2,3) or omits day_index. If the whole
    set is shifted by +1, remap; otherwise match exact indexes then leftover
    rows by order.
    """
    wanted = _wanted_day_indexes(week_payload)
    wanted_set = set(wanted)
    ordered = [d for d in parsed if isinstance(d, dict)]
    by_idx: dict[int, dict[str, Any]] = {}
    used: set[int] = set()

    def _take(pos: int, want: int) -> None:
        by_idx[want] = {**ordered[pos], "day_index": want}
        used.add(pos)

    parsed_nums: list[int | None] = []
    for d in ordered:
        try:
            parsed_nums.append(int(d.get("day_index")))
        except (TypeError, ValueError):
            parsed_nums.append(None)
    present = [n for n in parsed_nums if n is not None]
    if (
        wanted
        and present
        and len(present) == len(wanted)
        and set(present) == {w + 1 for w in wanted}
    ):
        for i, d in enumerate(ordered):
            try:
                want = int(d.get("day_index")) - 1
            except (TypeError, ValueError):
                continue
            if want in wanted_set and want not in by_idx:
                _take(i, want)
        return by_idx

    for i, d in enumerate(ordered):
        try:
            idx = int(d.get("day_index"))
        except (TypeError, ValueError):
            continue
        if idx in wanted_set and idx not in by_idx:
            _take(i, idx)

    unused = [i for i in range(len(ordered)) if i not in used]
    missing = [w for w in wanted if w not in by_idx]
    for want, pos in zip(missing, unused):
        _take(pos, want)
    return by_idx


def pick_challenge_phase_with_openai(
    week_payload: list[dict[str, Any]],
    *,
    profile: dict[str, Any] | None = None,
    phase: dict[str, Any] | None = None,
    avoid_ids: list[int] | None = None,
    avoid_stems: list[str] | None = None,
) -> dict[str, Any]:
    """One GPT request for a challenge mesocycle: week A, isolation week B, why.

    Meals are assembled later by meal_engine. Returns ``{days, week_b, rationale_vi}``.
    Hard-fails like ``pick_with_openai``.
    """
    settings = _require_openai_settings()
    max_out = min(8192, max(4096, int(settings.openai_max_tokens or 4096)))
    system = (
        "You are a strength coach for TAPTOT planning ONE mesocycle of a 100-day challenge. "
        "Each day has slots. Pick exercises ONLY from that slot's pool ids. "
        "For every required slot, choose exactly `pick` distinct exercise_ids from that slot's pool. "
        "Optional slots may use []. Do not invent ids or change pick counts. "
        "Prefer exercises that use the same implement as profile.test_kit "
        "(dumbbell / band / bar_rings) when that slot's pool still has a matching option. "
        "Prescribe sets, reps, rest_seconds, and optional load_kg from profile.load_hints "
        "and tests_vi — never invent kilograms. Copy load_kg from the matching hint when "
        "the chosen lift uses dumbbells; omit load_kg for bodyweight or band work. "
        "dose_bounds on each candidate are hints, not hard limits — except dip / "
        "HSPU / pike / muscle-up, which MUST stay inside that candidate's dose_bounds "
        "(those already apply a hardness factor; do not use 70–80% of the push-up test). "
        "Typical ranges: 2–5 sets, rest 30–180 seconds, working reps ≈ 70–80% of the "
        "matching test (L1 or strength_tier=weak: 60–75%; isolation can be 12–15 when the "
        "test max is high — do not default to 8). "
        "day_index is 0-based and MUST match required_day_indexes exactly — "
        "return one days[] object for every required index. "
        "days = week A (full session slot picks). "
        "week_b: same compound slot exercise_ids as days (h_press, v_press, squat, hinge, "
        "v_pull, h_pull, extra_press, extra_pull). Only isolation slots "
        "(keys containing iso) plus cardio/core/conditioning may differ. "
        "If no valid isolation alternative exists, omit week_b or return []. "
        "MUST pick a different exercise_id than avoid_ids when that slot's pool "
        "still has another option — compounds and isolation. Do not reuse a prior-phase "
        "lift family in avoid_stems (step-up, lunge, push-up) when another family exists. "
        "Never pick two main lifts with the same movement "
        "(e.g. two step-ups) in one session. "
        "Chest compounds: L1 machine; L2+ barbell or dumbbell. Only flat and incline. "
        "Never decline. First chest slot flat; second incline if present. "
        "Do not copy the previous phase's full isolation lineup. "
        "Do not pick foods or meals — the server builds the meal plan separately. "
        "rationale_vi: 3–5 Vietnamese sentences explaining this phase's training only. "
        "If profile.focus_areas_vi is non-empty, prefer those muscle groups when the slot "
        "pool still has a matching option, and mention those Vietnamese labels in rationale_vi. "
        "Follow phase.knowledge_playbook_vi and phase.skill_prompt_vi — cite those Vietnamese "
        "knowledge labels in rationale_vi. L1 phase 1: form, do not add sets. "
        "Working reps start at the low end of dose_bounds; the engine adds +1 rep each "
        "non-deload week up to the high end. "
        "Cardio/conditioning: only Shadow Boxing, Jumping Jack, Jump Rope, Running Intervals "
        "(sets × seconds) or Hiking / Trail Run (1 set leftover minutes). "
        "Drop-set / rest-pause only if want_intensity_tech and only on isolation. "
        "Respond with JSON: "
        '{"days":[{"day_index":0,"slots":[{"key":"h_press","exercises":'
        '[{"exercise_id":1,"sets":3,"reps":"12-15","rest_seconds":90,'
        '"load_kg":10,"load_note_vi":"tạ đơn 10kg mỗi tay"}]}]}],'
        '"week_b":[{"day_index":0,"slots":[{"key":"chest_iso","exercise_ids":[10]}]}],'
        '"rationale_vi":"..."}'
    )

    def _phase_user_obj(days: list[dict[str, Any]]) -> dict[str, Any]:
        loc = str((profile or {}).get("location") or "").strip().lower()
        compact = [
            compact_day_for_prompt(
                {**d, "location": loc} if loc else d,
                cap=None if d.get("slots") else 12,
                avoid_ids=avoid_ids,
                avoid_stems=avoid_stems,
            )
            for d in days
        ]
        user_obj: dict[str, Any] = {
            "days": compact,
            "required_day_indexes": _wanted_day_indexes(days),
            "avoid_ids": list(avoid_ids or []),
            "avoid_stems": list(avoid_stems or []),
        }
        if profile:
            user_obj["profile"] = profile
        if phase:
            user_obj["phase"] = phase
        return user_obj

    def _phase_body(days: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "model": settings.openai_model,
            "temperature": min(0.4, float(settings.openai_temperature or 0.4)),
            "max_completion_tokens": max_out,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": json.dumps(_phase_user_obj(days), ensure_ascii=False),
                },
            ],
        }

    def _parse_phase_response(raw: Any) -> dict[str, Any]:
        if isinstance(raw, list):
            return {"days": raw}
        if isinstance(raw, dict):
            return raw
        raise OpenAIPickError(OPENAI_PICK_FAIL_VI)

    accumulated: dict[int, dict[str, Any]] = {}
    week_b_acc: dict[int, dict[str, Any]] = {}
    data_acc: dict[str, Any] = {}
    pending = list(week_payload)
    retry_left = 2

    while pending:
        try:
            parsed = _parse_llm_json(_openai_chat_content(_phase_body(pending)))
        except (json.JSONDecodeError, ValueError) as exc:
            raise OpenAIPickError(OPENAI_PICK_FAIL_VI) from exc
        data = _parse_phase_response(parsed)
        indexed = _index_llm_days(list(data.get("days") or []), pending)
        for idx, chosen in indexed.items():
            accumulated[idx] = chosen
        b_indexed = _index_llm_days(
            list(data.get("week_b") or data.get("weekB") or []),
            pending,
        )
        for idx, chosen in b_indexed.items():
            week_b_acc[idx] = chosen
        if str(data.get("rationale_vi") or "").strip() and not data_acc.get("rationale_vi"):
            data_acc["rationale_vi"] = data.get("rationale_vi")

        pending = [
            day
            for day in week_payload
            if _safe_day_index(day) is not None
            and _safe_day_index(day) not in accumulated
        ]
        if not pending:
            break
        if retry_left <= 0:
            logger.warning(
                "Phase pick still missing day_index=%s after retries",
                [_safe_day_index(d) for d in pending],
            )
            raise OpenAIPickError("OpenAI trả thiếu ngày trong lịch. Thử tạo lại.")
        retry_left -= 1
        logger.warning(
            "Phase pick missing days %s; retrying those only",
            [_safe_day_index(d) for d in pending],
        )

    out_days: list[dict[str, Any]] = []
    out_b: list[dict[str, Any]] = []
    for day in week_payload:
        want = _safe_day_index(day)
        if want is None:
            continue
        chosen = accumulated.get(want)
        if chosen is None:
            raise OpenAIPickError("OpenAI trả thiếu ngày trong lịch. Thử tạo lại.")
        out_days.append(chosen)
        if want in week_b_acc:
            out_b.append(week_b_acc[want])

    rationale = str(data_acc.get("rationale_vi") or "").strip()
    if len(rationale) > 1200:
        rationale = rationale[:1200].rstrip()
    return {
        "days": out_days,
        "week_b": out_b,
        "rationale_vi": rationale,
    }


def _safe_day_index(day: dict[str, Any]) -> int | None:
    try:
        return int(day.get("day_index"))
    except (TypeError, ValueError):
        return None


MEAL_SLOT_KEYS = ("breakfast", "lunch", "dinner", "snack", "rest")


def compact_food_for_prompt(food: Any) -> dict[str, Any]:
    roles = getattr(food, "roles", None)
    slots = getattr(food, "slots", None)
    if isinstance(food, dict):
        fid = food.get("food_id") or food.get("id")
        roles = food.get("roles")
        slots = food.get("slots")
        return {
            "food_id": int(fid),
            "name_vi": str(food.get("name_vi") or ""),
            "roles": sorted(str(r) for r in (roles or [])),
            "slots": sorted(str(s) for s in (slots or [])),
            "calories": food.get("calories"),
            "protein_g": food.get("protein_g"),
            "carbs_g": food.get("carbs_g"),
            "fat_g": food.get("fat_g"),
        }
    return {
        "food_id": int(food.id),
        "name_vi": str(getattr(food, "name_vi", "") or ""),
        "roles": sorted(str(r) for r in (roles or [])),
        "slots": sorted(str(s) for s in (slots or [])),
        "calories": getattr(food, "calories", None),
        "protein_g": getattr(food, "protein_g", None),
        "carbs_g": getattr(food, "carbs_g", None),
        "fat_g": getattr(food, "fat_g", None),
    }


def parse_challenge_meal_slots(raw: Any, allowed_ids: set[int]) -> dict[str, list[int]]:
    """Keep only in-pool food_ids per breakfast/lunch/dinner/snack/rest."""
    out: dict[str, list[int]] = {key: [] for key in MEAL_SLOT_KEYS}
    if not isinstance(raw, dict):
        return out
    slots = raw.get("slots") if isinstance(raw.get("slots"), dict) else raw
    if not isinstance(slots, dict):
        return out
    for key in MEAL_SLOT_KEYS:
        items = slots.get(key)
        if not isinstance(items, list):
            continue
        seen: set[int] = set()
        ids: list[int] = []
        for item in items:
            fid: Any = item.get("food_id") if isinstance(item, dict) else item
            if isinstance(item, dict) and fid is None:
                fid = item.get("id")
            try:
                food_id = int(fid)
            except (TypeError, ValueError):
                continue
            if food_id in allowed_ids and food_id not in seen:
                seen.add(food_id)
                ids.append(food_id)
        out[key] = ids
    return out


def pick_challenge_meals_with_openai(
    pool: list[Any],
    *,
    profile: dict[str, Any] | None = None,
    targets: dict[str, Any] | None = None,
) -> dict[str, list[int]]:
    """One GPT call: pick breakfast/lunch/dinner/snack/rest from the given pool only."""
    foods = [compact_food_for_prompt(item) for item in pool]
    allowed = {int(item["food_id"]) for item in foods}
    if not allowed:
        return {key: [] for key in MEAL_SLOT_KEYS}
    settings = _require_openai_settings()
    max_out = min(4096, max(1024, int(settings.openai_max_tokens or 2048)))
    system = (
        "You are a nutrition coach for TAPTOT. Pick everyday lean ingredients for "
        "breakfast, lunch, dinner, snack, and rest-day meals. "
        "Use ONLY food_id values from the provided pool. Do not invent ids. "
        "Prefer protein + carb + produce on main meals; snack can be protein or fruit. "
        "If profile.knowledge_by_phase is present, there are 3 mesocycles (months 1–3). "
        "Follow that phase's briefs: carb cycling means more starch on training slots "
        "and less on the rest slot; L1 keeps macros stable — never carb-cycle L1. "
        "Protein grams stay near targets. Do not invent food_id values. "
        "servings are optional hints — the server will scale portions to daily calories. "
        "Respond with JSON: "
        '{"slots":{"breakfast":[{"food_id":1,"servings":1}],'
        '"lunch":[{"food_id":2}],"dinner":[{"food_id":3}],'
        '"snack":[{"food_id":4}],"rest":[{"food_id":2}]}}'
    )
    user_obj: dict[str, Any] = {"pool": foods}
    if profile:
        user_obj["profile"] = {
            k: profile.get(k)
            for k in (
                "goal",
                "gender",
                "age",
                "height_cm",
                "weight_kg",
                "session_minutes",
                "coach_brief_vi",
                "fitness_baseline",
                "knowledge_by_phase",
                "tests_vi",
                "focus_areas_vi",
            )
            if profile.get(k) is not None
        }
    if targets:
        user_obj["targets"] = targets
    body = {
        "model": settings.openai_model,
        "temperature": min(0.4, float(settings.openai_temperature or 0.4)),
        "max_completion_tokens": max_out,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(user_obj, ensure_ascii=False)},
        ],
    }
    try:
        parsed = _parse_llm_json(_openai_chat_content(body))
    except (json.JSONDecodeError, ValueError) as exc:
        raise OpenAIPickError(OPENAI_PICK_FAIL_VI) from exc
    picks = parse_challenge_meal_slots(parsed, allowed)
    if not any(picks.values()):
        raise OpenAIPickError("OpenAI không chọn được món trong kho thức ăn. Thử tạo lại.")
    return picks

