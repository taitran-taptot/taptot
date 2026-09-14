import json
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from app.services.workout_generation.dose_bounds import (
    bodyweight_test_max,
    dose_bounds_for_item,
)

tok = "P0SqydMZPYJE3PvvpzpPQA"
p = json.load(urllib.request.urlopen(f"http://localhost:8000/api/v1/plans/share/{tok}"))
print("title:", p.get("title_vi"))
print("desc:", (p.get("description_vi") or "")[:400])
print("created:", p.get("created_at"))

ids = sorted(
    {
        int(e["exercise_id"])
        for d in p["days"]
        for e in (d.get("exercises") or [])
        if e.get("exercise_id")
    }
)


def fetch(i):
    try:
        with urllib.request.urlopen(f"http://localhost:8000/api/v1/exercises/{i}", timeout=8) as r:
            return i, json.load(r)
    except Exception as exc:  # noqa: BLE001
        return i, {"error": str(exc)}


with ThreadPoolExecutor(8) as pool:
    cats = dict(pool.map(fetch, ids))

needles = ("hộp", "hop", "box", "cầu mông", "glute", "ếch", "frog", "xổm", "squat", "một chân", "single")
base_guess = {"pushups_max": 45, "squats_max": 40, "pullups_max": 8}

for d in p["days"][:4]:
    print("---", d.get("day_number"), d.get("title_vi"), d.get("split_role"))
    for e in d.get("exercises") or []:
        if e.get("section") not in ("main", "warmup"):
            continue
        ex = cats.get(int(e["exercise_id"]), {})
        blob = f"{ex.get('name_vi')} {ex.get('name_en')}".lower()
        if not any(n in blob for n in needles):
            continue
        item = {
            "name_vi": ex.get("name_vi"),
            "name_en": ex.get("name_en"),
            "movement_role": ex.get("movement_role"),
            "movement_pattern": ex.get("movement_pattern"),
            "muscle_slug": (ex.get("muscle_group") or {}).get("slug")
            if isinstance(ex.get("muscle_group"), dict)
            else None,
        }
        tmax = bodyweight_test_max(item, base_guess, no_equipment=True)
        b = dose_bounds_for_item(
            item, experience_level=1, fitness_baseline=base_guess, no_equipment=True
        )
        print(
            f"  ACT {e.get('section')} {e.get('sets')}x{e.get('reps')} notes={e.get('notes_vi')!r} | "
            f"{ex.get('name_vi')} / {ex.get('name_en')} | {ex.get('movement_role')}/{ex.get('movement_pattern')} | "
            f"now tmax={tmax} bounds={b.get('reps_min')}-{b.get('reps_max')}"
        )
