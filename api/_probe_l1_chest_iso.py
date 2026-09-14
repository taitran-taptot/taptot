"""Narrow reproduction: L1 rings chest_iso exhausted by h_press taking 86."""
from __future__ import annotations

import sys

from app.core.database import SessionLocal
from app.services.exercise_catalog_classify import difficulty_band_for_experience
from app.services.workout_generation.assemble import collect_day_shortlists_for_prompt
from app.services.workout_generation.frame_picker import pick_master_frame
from app.services.workout_generation.openai_picker import OpenAIPickError, validate_slot_picks
from app.services.workout_generation.shortlist import query_filtered_exercises


def safe(s: object) -> str:
    return str(s).encode("ascii", "backslashreplace").decode("ascii")


def main() -> None:
    print("L1 band", difficulty_band_for_experience(1))
    print("L2 band", difficulty_band_for_experience(2))
    db = SessionLocal()
    try:
        for level, variants, force_h_86 in [
            (1, 1, False),
            (1, 1, True),
            (1, 3, False),
            (1, 3, True),
            (2, 3, True),
        ]:
            frame, days = pick_master_frame(
                db,
                experience_level=level,
                sessions_per_week=3,
                gender="male",
                location="home",
                no_equipment=False,
                week_code=None,
            )
            fd = days[0]
            slots = []
            collect_day_shortlists_for_prompt(
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
                split_role="push",
                exclude_ids=set(),
                injury=None,
                out_slots=slots,
                pushups_max=10,
                week_role_count=1,
                pick_variants=variants,
            )
            by_key = {s["key"]: s for s in slots if s.get("pool")}
            print(
                f"\nL={level} variants={variants} force86={force_h_86} "
                f"keys={list(by_key)} "
                f"h={ [r['id'] for r in by_key.get('h_press',{}).get('pool',[])] } "
                f"chest={ [r['id'] for r in by_key.get('chest_iso',{}).get('pool',[])] }"
            )
            llm = {"slots": []}
            if force_h_86 and "h_press" in by_key:
                ids = [r["id"] for r in by_key["h_press"]["pool"]]
                if 86 in ids:
                    llm = {"slots": [{"key": "h_press", "exercise_ids": [86]}]}
            # also test avoid of ring compounds (phase 2+)
            for label, avoid in [
                ("none", None),
                ("avoid_ring_press", {828, 829}),
            ]:
                try:
                    out = validate_slot_picks(
                        list(by_key.values()),
                        llm,
                        split_role="push",
                        avoid_ids=avoid,
                        experience_level=level,
                    )
                    print(f"  {label}: OK {out.get('_slot_picks')}")
                except OpenAIPickError as e:
                    print(f"  {label}: FAIL {safe(e)}")

        # Confirm 830 excluded at L1
        cands = query_filtered_exercises(
            db,
            split_role="push",
            experience_level=1,
            equipment_slugs=["gymnastic-rings"],
            no_equipment=False,
            ai_suggest_equipment=False,
            location="home",
            movement_roles=frozenset({"compound", "isolation", "resistance"}),
            block_key="resistance",
            count_max=4,
        )
        print("\nL1 candidate ids", [c.id for c in cands])
        print("830 in L1 cands?", any(c.id == 830 for c in cands))
        cands2 = query_filtered_exercises(
            db,
            split_role="push",
            experience_level=2,
            equipment_slugs=["gymnastic-rings"],
            no_equipment=False,
            ai_suggest_equipment=False,
            location="home",
            movement_roles=frozenset({"compound", "isolation", "resistance"}),
            block_key="resistance",
            count_max=4,
        )
        print("830 in L2 cands?", any(c.id == 830 for c in cands2))
    finally:
        db.close()


if __name__ == "__main__":
    main()
