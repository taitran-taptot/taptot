"""Reproduce chest_iso failure: h_press consumes 86, simulate 830 missing."""
from __future__ import annotations

from app.core.database import SessionLocal
from app.services.workout_generation.assemble import collect_day_shortlists_for_prompt
from app.services.workout_generation.frame_picker import pick_master_frame
from app.services.workout_generation.openai_picker import (
    OpenAIPickError,
    picks_from_llm_day,
    validate_slot_picks,
)
from app.services.workout_generation.fb_rotation import effective_pick_role, is_full_body_role
from collections import Counter


def main() -> None:
    db = SessionLocal()
    try:
        # curriculum path: pick_variants=3
        for curriculum, sessions, level, pushups in [
            (False, 3, 2, 20),
            (True, 3, 2, 20),
            (True, 6, 2, 20),
            (False, 3, 1, 10),
            (True, 3, 1, 10),
            (False, 4, 2, 5),  # knee pushups preferred?
            (True, 4, 2, 5),
        ]:
            frame, days = pick_master_frame(
                db,
                experience_level=level,
                sessions_per_week=sessions,
                gender="male",
                location="home",
                no_equipment=False,
                week_code=None,
            )
            pick_variants = 3 if curriculum else 1
            _pick_roles = []
            _fb = 0
            for fd in days:
                if is_full_body_role(fd.split_role):
                    _pick_roles.append(str(effective_pick_role(fd.split_role, fb_offset=_fb)))
                    _fb += 1
                else:
                    _pick_roles.append(str(fd.split_role))
            role_counts = Counter(_pick_roles)
            print(
                f"\n=== curr={curriculum} sess={sessions} L={level} "
                f"pu={pushups} week={getattr(frame,'week_code',None)} "
                f"roles={_pick_roles} variants={pick_variants} ==="
            )
            fb_offset = 0
            for fd in days:
                if is_full_body_role(fd.split_role):
                    pick_role = effective_pick_role(fd.split_role, fb_offset=fb_offset)
                    fb_offset += 1
                else:
                    pick_role = fd.split_role
                stored_slots = []
                day_blocks = collect_day_shortlists_for_prompt(
                    db,
                    frame_day=fd,
                    experience_level=level,
                    session_minutes=60,
                    equipment_slugs=["gymnastic-rings"],
                    no_equipment=False,
                    ai_suggest_equipment=False,
                    location="home",
                    focus_slugs=None,
                    cardio_on_lift_days=False,
                    liss_finisher=False,
                    goal="hypertrophy",
                    extra_goals=[],
                    split_role=pick_role,
                    exclude_ids=set(),
                    injury=None,
                    out_slots=stored_slots,
                    pushups_max=pushups,
                    week_role_count=int(role_counts.get(str(pick_role), 1) or 1),
                    pick_variants=pick_variants,
                )
                chest = next((s for s in stored_slots if s.get("key") == "chest_iso"), None)
                if not chest:
                    continue
                pool_ids = [r["id"] for r in chest.get("pool") or []]
                print(
                    f"  day{fd.day_index} role={pick_role} keys="
                    f"{[s['key'] for s in stored_slots if s.get('pool')]} "
                    f"chest_iso={pool_ids}"
                )
                # Simulate LLM picking knee pushup for h_press when available
                h = next((s for s in stored_slots if s.get("key") == "h_press"), None)
                h_ids = [r["id"] for r in (h.get("pool") if h else []) or []]
                llm_slots = []
                if h and 86 in h_ids:
                    llm_slots.append({"key": "h_press", "exercise_ids": [86]})
                if chest:
                    # invent bad id so filler runs
                    llm_slots.append({"key": "chest_iso", "exercise_ids": [999]})
                try:
                    out = validate_slot_picks(
                        [s for s in stored_slots if s.get("pool")],
                        {"slots": llm_slots},
                        split_role=pick_role,
                        experience_level=level,
                    )
                    print(f"    OK picks={out.get('_slot_picks')}")
                except OpenAIPickError as e:
                    print(f"    FAIL validate: {e}")

                # Also try picks_from_llm_day with empty-ish LLM
                llm_day = {
                    "day_index": fd.day_index,
                    "slots": llm_slots
                    or [{"key": s["key"], "exercise_ids": []} for s in stored_slots if s.get("pool")],
                }
                try:
                    picks_from_llm_day(
                        llm_day,
                        day_blocks,
                        split_role=pick_role,
                        slots=stored_slots,
                        experience_level=level,
                    )
                    print("    picks_from_llm_day OK")
                except OpenAIPickError as e:
                    print(f"    picks_from_llm_day FAIL: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
