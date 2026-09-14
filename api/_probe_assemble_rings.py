"""Assemble real frame days for home+rings and inspect chest_iso pools."""
from __future__ import annotations

from app.core.database import SessionLocal
from app.services.workout_generation.assemble import collect_day_shortlists_for_prompt
from app.services.workout_generation.frame_picker import pick_master_frame
from app.services.workout_generation.openai_picker import OpenAIPickError, validate_slot_picks


def main() -> None:
    db = SessionLocal()
    try:
        for sessions in (3, 4, 5, 6):
            frame, days = pick_master_frame(
                db,
                experience_level=2,
                sessions_per_week=sessions,
                gender="male",
                location="home",
                no_equipment=False,
                week_code=None,
            )
            week = getattr(frame, "week_code", None)
            roles = [d.split_role for d in days]
            print(f"\n=== sessions={sessions} week={week} roles={roles} ===")
            for fd in days:
                stored_slots: list = []
                stored_gear: dict = {}
                collect_day_shortlists_for_prompt(
                    db,
                    frame_day=fd,
                    experience_level=2,
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
                    split_role=fd.split_role,
                    exclude_ids=set(),
                    injury=None,
                    out_slots=stored_slots,
                    pushups_max=20,
                    week_role_count=1,
                    pick_variants=1,
                    out_gear_meta=stored_gear,
                )
                keys = [s.get("key") for s in stored_slots]
                print(f"  day{fd.day_index} role={fd.split_role} keys={keys}")
                chest = next((s for s in stored_slots if s.get("key") == "chest_iso"), None)
                if chest:
                    ids = [r.get("id") for r in (chest.get("pool") or [])]
                    print(f"    chest_iso pool={ids} meta={stored_gear.get('chest_iso')}")
                    try:
                        out = validate_slot_picks(
                            [s for s in stored_slots if s.get("pool")],
                            {"slots": []},
                            split_role=fd.split_role,
                        )
                        sp = out.get("_slot_picks") or {}
                        print(f"    validate OK chest_iso={sp.get('chest_iso')} all={sp}")
                    except OpenAIPickError as e:
                        print(f"    validate FAIL: {e}")
                        # dump used progression
                        from app.services.workout_generation.openai_picker import (
                            _llm_picks_by_slot,
                            _next_pool_id,
                            _shortlist_ids,
                        )

                        used: set[int] = set()
                        for spec in stored_slots:
                            if not spec.get("pool"):
                                continue
                            key = spec["key"]
                            n = int(spec.get("pick") or 1)
                            pool = list(spec.get("pool") or [])
                            allowed = _shortlist_ids(pool)
                            print(
                                f"      before {key}: used={sorted(used)} "
                                f"pool={sorted(allowed)} overlap={sorted(used & allowed)}"
                            )
                            chosen = []
                            while len(chosen) < n:
                                alt = _next_pool_id(
                                    pool,
                                    used=used | set(chosen),
                                    avoid_ids=set(),
                                    avoid_stems=set(),
                                    allow_avoided=True,
                                )
                                if alt is None:
                                    break
                                chosen.append(alt)
                            print(f"      fill {key} -> {chosen}")
                            used.update(chosen)
                else:
                    print(f"    no chest_iso; strength keys={[k for k in keys if k]}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
