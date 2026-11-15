"""Export the active local catalog as a Postgres 16 seed file.

The file truncates every public table, then loads only the rows that should
replace production: active exercises (except the E2E fixture), active foods,
published cooking and knowledge, the three shop products, their unused redeem
codes, site media, and the two staff accounts.
"""

from __future__ import annotations

import sys
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = ROOT / "api" / ".env"
OUT_PATHS = [
    ROOT / "tmp" / "taptot-production-seed.sql",
    Path.home() / "taptot-production-seed.sql",
]

STAFF_EMAILS = ("AdminTAPTOT@taptot.vn", "HLVTAPTOT@taptot.vn")
SHOP_SLUGS = ("ta-don", "day-khang-luc", "xa-don-va-vong-treo")
E2E_EXERCISE_ID = 935


def load_database_url() -> str:
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() == "DATABASE_URL":
            return value.strip().strip('"').replace("postgresql+psycopg://", "postgresql://", 1)
    raise SystemExit("DATABASE_URL missing from api/.env")


def columns(cur, table: str) -> list[str]:
    cur.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        ORDER BY ordinal_position
        """,
        (table,),
    )
    return [row[0] for row in cur.fetchall()]


def qident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def write_copy(out, cur, table: str, select_sql: str, params: tuple = ()) -> int:
    cols = columns(cur, table)
    select_cols = ", ".join(qident(col) for col in cols)
    out.write(
        f"COPY public.{qident(table)} ({', '.join(qident(col) for col in cols)}) FROM stdin;\n".encode()
    )
    query = f"COPY ({select_sql.format(cols=select_cols)}) TO STDOUT"
    with cur.copy(query, params) as copy:
        row_count = 0
        while True:
            chunk = copy.read()
            if not chunk:
                break
            block = bytes(chunk)
            out.write(block)
            row_count += block.count(b"\n")
    out.write(b"\\.\n\n")
    return row_count


def main() -> None:
    conn = psycopg.connect(load_database_url())
    cur = conn.cursor()
    staff_sql = ", ".join("%s" for _ in STAFF_EMAILS)
    shop_sql = ", ".join("%s" for _ in SHOP_SLUGS)

    copies: list[tuple[str, str, tuple]] = [
        (
            "users",
            "SELECT {cols} FROM users WHERE email IN (" + staff_sql + ") ORDER BY email",
            STAFF_EMAILS,
        ),
        (
            "user_profiles",
            "SELECT p.* FROM user_profiles p JOIN users u ON u.id = p.user_id "
            "WHERE u.email IN (" + staff_sql + ") ORDER BY p.id",
            STAFF_EMAILS,
        ),
        ("muscle_groups", "SELECT {cols} FROM muscle_groups ORDER BY id", ()),
        ("equipment", "SELECT {cols} FROM equipment WHERE is_active ORDER BY id", ()),
        (
            "exercises",
            "SELECT {cols} FROM exercises WHERE is_active AND id <> %s ORDER BY id",
            (E2E_EXERCISE_ID,),
        ),
        (
            "exercise_equipment",
            "SELECT ee.* FROM exercise_equipment ee "
            "JOIN exercises e ON e.id = ee.exercise_id "
            "JOIN equipment q ON q.id = ee.equipment_id "
            "WHERE e.is_active AND e.id <> %s AND q.is_active "
            "ORDER BY ee.exercise_id, ee.equipment_id",
            (E2E_EXERCISE_ID,),
        ),
        (
            "exercise_prescription_defaults",
            "SELECT {cols} FROM exercise_prescription_defaults ORDER BY id",
            (),
        ),
        (
            "session_block_templates",
            "SELECT {cols} FROM session_block_templates ORDER BY id",
            (),
        ),
        ("food_categories", "SELECT {cols} FROM food_categories ORDER BY id", ()),
        (
            "foods",
            "SELECT {cols} FROM foods WHERE status = 'active' ORDER BY id",
            (),
        ),
        (
            "food_portions",
            "SELECT p.* FROM food_portions p JOIN foods f ON f.id = p.food_id "
            "WHERE f.status = 'active' ORDER BY p.id",
            (),
        ),
        (
            "food_aliases",
            "SELECT a.* FROM food_aliases a JOIN foods f ON f.id = a.food_id "
            "WHERE f.status = 'active' ORDER BY a.id",
            (),
        ),
        (
            "cooking_posts",
            "SELECT {cols} FROM cooking_posts WHERE is_published ORDER BY id",
            (),
        ),
        (
            "knowledge_articles",
            "SELECT {cols} FROM knowledge_articles WHERE is_published ORDER BY id",
            (),
        ),
        (
            "shop_products",
            "SELECT {cols} FROM shop_products WHERE slug IN (" + shop_sql + ") ORDER BY id",
            SHOP_SLUGS,
        ),
        (
            "product_redeem_batches",
            "SELECT DISTINCT b.id, b.product_id, b.qty, b.note, "
            "CASE WHEN u.email IN (" + staff_sql + ") THEN b.created_by ELSE NULL END, "
            "b.created_at "
            "FROM product_redeem_batches b "
            "JOIN product_redeem_codes c ON c.batch_id = b.id "
            "LEFT JOIN shop_products p ON p.id = b.product_id "
            "LEFT JOIN users u ON u.id = b.created_by "
            "WHERE c.status = 'unused' AND (b.product_id IS NULL OR p.slug IN ("
            + shop_sql
            + ")) ORDER BY b.id",
            STAFF_EMAILS + SHOP_SLUGS,
        ),
        (
            "product_redeem_codes",
            "SELECT c.* FROM product_redeem_codes c "
            "JOIN product_redeem_batches b ON b.id = c.batch_id "
            "LEFT JOIN shop_products p ON p.id = b.product_id "
            "WHERE c.status = 'unused' AND (b.product_id IS NULL OR p.slug IN ("
            + shop_sql
            + ")) ORDER BY c.id",
            SHOP_SLUGS,
        ),
        ("site_page_media", "SELECT {cols} FROM site_page_media ORDER BY id", ()),
    ]

    for path in OUT_PATHS:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as out:
            out.write(
                b"-- TAPTOT production catalog seed. UTF-8, no transaction_timeout.\n"
                b"-- Replaces every public table with the active local catalog.\n"
                b"\\set ON_ERROR_STOP on\n"
                b"BEGIN;\n"
                b"DO $$\n"
                b"DECLARE stmt text;\n"
                b"BEGIN\n"
                b"  SELECT 'TRUNCATE TABLE ' || string_agg(format('%I.%I', schemaname, tablename), ', ')\n"
                b"         || ' RESTART IDENTITY CASCADE'\n"
                b"    INTO stmt\n"
                b"    FROM pg_tables\n"
                b"   WHERE schemaname = 'public';\n"
                b"  IF stmt IS NOT NULL THEN\n"
                b"    EXECUTE stmt;\n"
                b"  END IF;\n"
                b"END $$;\n\n"
            )
            counts: list[tuple[str, int]] = []
            for table, select_sql, params in copies:
                count = write_copy(out, cur, table, select_sql, params)
                counts.append((table, count))
            cur.execute(
                """
                SELECT c.relname
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = 'public' AND c.relkind = 'S'
                ORDER BY 1
                """
            )
            for (sequence,) in cur.fetchall():
                table = sequence.removesuffix("_id_seq")
                if not any(name == table for name, _ in counts):
                    continue
                out.write(
                    (
                        "SELECT setval(pg_get_serial_sequence('public.{table}', 'id'), "
                        "COALESCE((SELECT MAX(id) FROM public.{table}), 1), "
                        "(SELECT MAX(id) IS NOT NULL FROM public.{table}));\n"
                    )
                    .format(table=table)
                    .encode()
                )
            out.write(b"COMMIT;\n")
        print(path)
        for table, count in counts:
            print(f"  {table}: {count}")
    conn.close()


if __name__ == "__main__":
    sys.exit(main())
