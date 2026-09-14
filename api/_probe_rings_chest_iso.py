"""Probe rings + chest_iso pool / validate_slot_picks failure modes."""
from __future__ import annotations

from app.core.database import SessionLocal
from app.services.workout_generation.home_gear_priority import (
    min_gear_pool,
    tier_slot_pool,
    user_gear_set,
)
from app.services.workout_generation.openai_picker import OpenAIPickError, validate_slot_picks
from app.services.workout_generation.session_templates import (
    pools_for_slots,
    slots_for_session,
    slots_to_prompt,
)
from app.services.workout_generation.shortlist import query_filtered_exercises


def build_prompt(cands, compound_n, accessory_n, variants, role_count):
    slots = slots_for_session(
        "push",
        compound_n=compound_n,
        accessory_n=accessory_n,
        location="home",
        experience_level=2,
    )
    pools = pools_for_slots(cands, slots, split_role="push", experience_level=2)
    user = user_gear_set(["gymnastic-rings"])
    need = min_gear_pool(role_count, variants)
    for s in slots:
        tiered, meta = tier_slot_pool(
            pools.get(s.key) or [], user_expanded=user, need=need
        )
        pools[s.key] = tiered
        print(f"  raw/tier {s.key}: meta={meta} ids={[r['id'] for r in tiered]}")
    prompt = []
    for spec in slots_to_prompt(slots, pools, mark_bw=True):
        if spec.get("pool"):
            prompt.append(spec)
    return prompt, need


def main():
    db = SessionLocal()
    try:
        cands = query_filtered_exercises(
            db,
            split_role="push",
            experience_level=2,
            equipment_slugs=["gymnastic-rings"],
            no_equipment=False,
            ai_suggest_equipment=False,
            exclude_ids=set(),
            location="home",
            movement_roles=frozenset({"compound", "isolation", "resistance"}),
            block_key="resistance",
            count_max=4,
        )
        print("cand ids", [x.id for x in cands])
        cases = [
            (2, 2, 1, 1),
            (2, 3, 1, 1),
            (2, 2, 3, 1),
            (1, 1, 1, 1),
            (2, 2, 3, 2),
        ]
        for compound_n, accessory_n, variants, role_count in cases:
            print(
                f"\n=== c={compound_n} a={accessory_n} "
                f"v={variants} rc={role_count} ==="
            )
            prompt, need = build_prompt(
                cands, compound_n, accessory_n, variants, role_count
            )
            keys = [s["key"] for s in prompt]
            print(f"need={need} prompt_keys={keys}")
            for s in prompt:
                print(f"  pool {s['key']}: {[r['id'] for r in s['pool']]}")
            for label, avoid in [("plain", None), ("avoid830", {830}), ("avoid86_830", {86, 830})]:
                try:
                    out = validate_slot_picks(
                        prompt,
                        {"slots": []},
                        split_role="push",
                        avoid_ids=avoid,
                    )
                    print(f"  {label} OK", out.get("_slot_picks"))
                except OpenAIPickError as e:
                    print(f"  {label} FAIL", e)

            # Force GPT to invent wrong id for chest_iso
            if any(s["key"] == "chest_iso" for s in prompt):
                llm = {
                    "slots": [
                        {"key": "h_press", "exercise_ids": [828]},
                        {"key": "chest_iso", "exercise_ids": [99999]},
                        {"key": "push_arm_iso", "exercise_ids": [836]},
                    ]
                }
                try:
                    out = validate_slot_picks(prompt, llm, split_role="push")
                    print("  invent OK", out.get("_slot_picks"))
                except OpenAIPickError as e:
                    print("  invent FAIL", e)

                # Consume 830 via h_press somehow? can't. Consume via used by picking 830 in wrong slot first?
                # Simulate if 830 were wrongly in an earlier pool and used:
                # put 830 only in chest_iso and mark used by pre-seeding via fake earlier pick
                # Actually: what if knee pushup 86 is only remaining after 830 used in avoid+week?
    finally:
        db.close()


if __name__ == "__main__":
    main()
