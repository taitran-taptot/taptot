"""Find all rings configs that fail chest_iso without forcing LLM picks."""
from __future__ import annotations

from collections import Counter

from app.core.database import SessionLocal
from app.services.workout_generation.assemble import collect_day_shortlists_for_prompt
from app.services.workout_generation.fb_rotation import effective_pick_role, is_full_body_role
from app.services.workout_generation.frame_picker import pick_master_frame
from app.services.workout_generation.openai_picker import OpenAIPickError, validate_slot_picks
def safe(s: object) -> str:
    return str(s).encode("ascii", "backslashreplace").decode("ascii")


def main() -> None:
    db = SessionLocal()
    try:
        failures = []
        for level in (1, 2, 3):
            for sessions in (2, 3, 4, 5, 6):
                for curriculum in (False, True):
                    for pushups in (None, 5, 20):
                        # mimic service week pick lightly
                        try:
                            frame, days = pick_master_frame(
                                db,
                                experience_level=level,
                                sessions_per_week=sessions,
                                gender="male",
                                location="home",
                                no_equipment=False,
                                week_code=None,
                            )
                        except Exception as e:
                            print("frame fail", level, sessions, safe(e))
                            continue
                        pick_variants = 3 if curriculum else 1
                        _pick_roles = []
                        _fb = 0
                        for fd in days:
                            if is_full_body_role(fd.split_role):
                                _pick_roles.append(
                                    str(effective_pick_role(fd.split_role, fb_offset=_fb))
                                )
                                _fb += 1
                            else:
                                _pick_roles.append(str(fd.split_role))
                        role_counts = Counter(_pick_roles)
                        fb_offset = 0
                        for fd in days:
                            if is_full_body_role(fd.split_role):
                                pick_role = effective_pick_role(
                                    fd.split_role, fb_offset=fb_offset
                                )
                                fb_offset += 1
                            else:
                                pick_role = fd.split_role
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
                                split_role=pick_role,
                                exclude_ids=set(),
                                injury=None,
                                out_slots=slots,
                                pushups_max=pushups,
                                week_role_count=int(
                                    role_counts.get(str(pick_role), 1) or 1
                                ),
                                pick_variants=pick_variants,
                            )
                            prompt = [s for s in slots if s.get("pool")]
                            if not any(s.get("key") == "chest_iso" for s in prompt):
                                continue
                            chest = next(s for s in prompt if s["key"] == "chest_iso")
                            h = next((s for s in prompt if s["key"] == "h_press"), None)
                            chest_ids = [r["id"] for r in chest["pool"]]
                            h_ids = [r["id"] for r in (h["pool"] if h else [])]
                            overlap = sorted(set(chest_ids) & set(h_ids))

                            # Case A: empty LLM
                            # Case B: LLM picks overlap id for h_press if possible
                            # Case C: avoid all non-overlap h_press ids
                            cases = [("empty", {"slots": []}, None)]
                            if h and overlap:
                                cases.append(
                                    (
                                        "h_takes_overlap",
                                        {
                                            "slots": [
                                                {
                                                    "key": "h_press",
                                                    "exercise_ids": [overlap[0]],
                                                }
                                            ]
                                        },
                                        None,
                                    )
                                )
                            if h:
                                non_chest = [i for i in h_ids if i not in chest_ids]
                                cases.append(
                                    (
                                        "avoid_h_non_chest",
                                        {"slots": []},
                                        set(non_chest) if non_chest else None,
                                    )
                                )

                            for label, llm, avoid in cases:
                                try:
                                    validate_slot_picks(
                                        prompt,
                                        llm,
                                        split_role=pick_role,
                                        avoid_ids=avoid,
                                        experience_level=level,
                                    )
                                except OpenAIPickError as e:
                                    failures.append(
                                        {
                                            "level": level,
                                            "sessions": sessions,
                                            "curriculum": curriculum,
                                            "pushups": pushups,
                                            "day": fd.day_index,
                                            "role": pick_role,
                                            "label": label,
                                            "chest": chest_ids,
                                            "h": h_ids,
                                            "overlap": overlap,
                                            "err": safe(e),
                                        }
                                    )
        print(f"failures={len(failures)}")
        for f in failures[:40]:
            print(f)
    finally:
        db.close()


if __name__ == "__main__":
    main()
