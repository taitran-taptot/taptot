#!/usr/bin/env python3
"""Delete all generated daily plans (user + guest) without touching catalog/users.

Uses DELETE FROM user_daily_plans so ON DELETE CASCADE clears days/exercises/meals
and ON DELETE SET NULL clears FKs on workout_sessions / trainer_assigned_plans.
Does not TRUNCATE CASCADE (that would wipe journal sessions).
"""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[1]
API_DIR = ROOT / "api"
sys.path.insert(0, str(API_DIR))

from app.core.config import get_settings  # noqa: E402

PLAN_TABLES = (
    "user_daily_plans",
    "user_daily_plan_days",
    "user_daily_plan_exercises",
    "user_daily_plan_meals",
)
KEEP_TABLES = (
    "users",
    "exercises",
    "foods",
    "shop_products",
    "cooking_posts",
    "workout_sessions",
)


def _count(conn, table: str) -> int:
    return int(conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar() or 0)


def _rel_size(conn, table: str) -> int:
    return int(
        conn.execute(
            text("SELECT pg_total_relation_size(CAST(:t AS regclass))"),
            {"t": table},
        ).scalar()
        or 0
    )


def _mb(n: int) -> str:
    return f"{n / (1024 * 1024):.2f} MB"


def _snapshot(conn) -> dict[str, tuple[int, int]]:
    out: dict[str, tuple[int, int]] = {}
    for table in PLAN_TABLES + KEEP_TABLES:
        out[table] = (_count(conn, table), _rel_size(conn, table))
    return out


def _print_snap(title: str, snap: dict[str, tuple[int, int]]) -> None:
    print(title)
    for table, (n, size) in snap.items():
        print(f"  {table:28} count={n:<8} size={_mb(size)}")


def main() -> int:
    url = get_settings().database_url
    engine = create_engine(url)

    with engine.connect() as conn:
        before = _snapshot(conn)
        _print_snap("BEFORE", before)
        plan_n = before["user_daily_plans"][0]
        print(f"\nDeleting {plan_n} user_daily_plans (+ cascaded children)...")
        conn.execute(text("DELETE FROM user_daily_plans"))
        conn.commit()

    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        conn.execute(
            text(
                "VACUUM (FULL, ANALYZE) user_daily_plans, user_daily_plan_days, "
                "user_daily_plan_exercises, user_daily_plan_meals"
            )
        )
    print("VACUUM (FULL, ANALYZE) done.")

    with engine.connect() as conn:
        after = _snapshot(conn)
        _print_snap("AFTER", after)
        for table in PLAN_TABLES:
            n = after[table][0]
            if n != 0:
                print(f"ERROR: {table} still has {n} rows")
                return 1
        for table in KEEP_TABLES:
            if after[table][0] != before[table][0]:
                print(
                    f"ERROR: {table} count changed "
                    f"{before[table][0]} -> {after[table][0]}"
                )
                return 1
        plan_before = sum(before[t][1] for t in PLAN_TABLES)
        plan_after = sum(after[t][1] for t in PLAN_TABLES)
        print(f"\nPlan tables size: {_mb(plan_before)} -> {_mb(plan_after)}")
        print("OK: plans empty; users/catalog/shop/journal counts unchanged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
