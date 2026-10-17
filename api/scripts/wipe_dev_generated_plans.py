"""Wipe generated workout plans + AI snapshots on local/dev databases.

Keeps catalog (foods/exercises/equipment), users, shop, meal_plans.
Default is dry-run. Refuses production and non-localhost URLs.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

API_DIR = Path(__file__).resolve().parents[1]
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import Session

from app.models.entities import (
    AiGeneration,
    Export,
    UserDailyPlan,
    UserDailyPlanDay,
    UserDailyPlanExercise,
    UserDailyPlanMeal,
)

PROD_ENVS = frozenset({"production", "prod"})
LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})


class WipeBlockedError(RuntimeError):
    """Raised when the target database is not a safe local/dev instance."""


def is_local_database_url(url: str) -> bool:
    parsed = make_url(url)
    driver = (parsed.drivername or "").lower()
    if driver.startswith("sqlite"):
        return True
    host = (parsed.host or "").lower()
    return host in LOCAL_HOSTS


def assert_wipe_allowed(app_env: str, database_url: str, *, allow_remote: bool = False) -> None:
    env = (app_env or "").strip().lower()
    if env in PROD_ENVS:
        raise WipeBlockedError("Refusing to wipe: app_env is production.")
    if not is_local_database_url(database_url) and not allow_remote:
        raise WipeBlockedError(
            "Refusing to wipe: database host is not localhost. Pass --allow-remote for non-prod remotes."
        )


def count_wipe_targets(db: Session) -> dict[str, int]:
    return {
        "user_daily_plan_exercises": db.query(UserDailyPlanExercise).count(),
        "user_daily_plan_meals": db.query(UserDailyPlanMeal).count(),
        "user_daily_plan_days": db.query(UserDailyPlanDay).count(),
        "user_daily_plans": db.query(UserDailyPlan).count(),
        "ai_generations": db.query(AiGeneration).count(),
        "exports_daily_plan": db.query(Export).filter(Export.export_type == "daily_plan").count(),
    }


def wipe_generated_plans(db: Session, *, execute: bool) -> dict[str, Any]:
    before = count_wipe_targets(db)
    deleted = {k: 0 for k in before}
    if not execute:
        return {"dry_run": True, "before": before, "deleted": deleted, "after": before}

    deleted["user_daily_plan_exercises"] = db.query(UserDailyPlanExercise).delete(
        synchronize_session=False
    )
    deleted["user_daily_plan_meals"] = db.query(UserDailyPlanMeal).delete(
        synchronize_session=False
    )
    deleted["user_daily_plan_days"] = db.query(UserDailyPlanDay).delete(
        synchronize_session=False
    )
    deleted["user_daily_plans"] = db.query(UserDailyPlan).delete(synchronize_session=False)
    deleted["ai_generations"] = db.query(AiGeneration).delete(synchronize_session=False)
    deleted["exports_daily_plan"] = (
        db.query(Export)
        .filter(Export.export_type == "daily_plan")
        .delete(synchronize_session=False)
    )
    db.commit()
    after = count_wipe_targets(db)
    return {"dry_run": False, "before": before, "deleted": deleted, "after": after}


def _print_report(result: dict[str, Any]) -> None:
    mode = "dry-run" if result["dry_run"] else "executed"
    print(f"wipe_dev_generated_plans ({mode})")
    for key in result["before"]:
        print(
            f"  {key}: before={result['before'][key]} "
            f"deleted={result['deleted'][key]} after={result['after'][key]}"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually delete rows. Without this flag, only counts are printed.",
    )
    parser.add_argument(
        "--allow-remote",
        action="store_true",
        help="Allow non-localhost hosts. Still refused when APP_ENV is production.",
    )
    args = parser.parse_args(argv)

    from app.core.config import get_settings
    from app.core.database import SessionLocal

    settings = get_settings()
    assert_wipe_allowed(
        settings.app_env,
        settings.database_url,
        allow_remote=args.allow_remote,
    )
    db = SessionLocal()
    try:
        result = wipe_generated_plans(db, execute=args.execute)
    finally:
        db.close()
    _print_report(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
