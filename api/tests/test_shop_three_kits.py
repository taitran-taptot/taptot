"""Shop catalog is three wizard kits at 500_000 VND."""

from datetime import UTC, datetime

from sqlalchemy import create_engine, text

from app.core.migrations.ensures import (
    ensure_home_equipment_catalog_v2,
    ensure_shop_three_kits,
)


def _engine():
    engine = create_engine("sqlite:///:memory:")
    now = datetime.now(UTC).isoformat()
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE equipment (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    slug TEXT NOT NULL UNIQUE,
                    name_vi TEXT NOT NULL,
                    name_en TEXT,
                    category TEXT,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    sort_order INTEGER NOT NULL DEFAULT 0,
                    image_url TEXT
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE shop_products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    slug TEXT UNIQUE NOT NULL,
                    name_vi TEXT NOT NULL,
                    description_vi TEXT,
                    price_vnd INTEGER NOT NULL,
                    stock_qty INTEGER NOT NULL DEFAULT 0,
                    image_url TEXT,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO shop_products
                    (slug, name_vi, description_vi, price_vnd, stock_qty, image_url,
                     is_active, created_at, updated_at)
                VALUES
                    ('gymnastic-rings', 'Vòng treo', NULL, 0, 0, NULL, 1, :now, :now),
                    ('pull-up-bar', 'Xà đơn', NULL, 200000, 5, NULL, 1, :now, :now),
                    ('resistance-band-2', 'Tube', NULL, 100000, 5, NULL, 1, :now, :now)
                """
            ),
            {"now": now},
        )
    return engine


def test_shop_three_kits_replaces_catalog():
    engine = _engine()
    ensure_home_equipment_catalog_v2(engine)
    ensure_shop_three_kits(engine)
    with engine.begin() as conn:
        rows = conn.execute(
            text("SELECT slug, name_vi, price_vnd, is_active FROM shop_products ORDER BY slug")
        ).fetchall()
    slugs = [r[0] for r in rows]
    assert slugs == ["bar-and-rings", "dumbbell", "resistance-band"]
    assert all(r[2] == 500000 for r in rows)
    assert all(r[3] == 1 for r in rows)
    names = {r[0]: r[1] for r in rows}
    assert names["resistance-band"] == "Dây kháng lực"
    assert names["dumbbell"] == "Tạ đơn"
    assert names["bar-and-rings"] == "Xà đơn treo tường và Vòng treo"


def test_home_catalog_no_longer_inserts_rings_shop_sku():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE equipment (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    slug TEXT NOT NULL UNIQUE,
                    name_vi TEXT NOT NULL,
                    name_en TEXT,
                    category TEXT,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    sort_order INTEGER NOT NULL DEFAULT 0,
                    image_url TEXT
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE shop_products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    slug TEXT UNIQUE NOT NULL,
                    name_vi TEXT NOT NULL,
                    description_vi TEXT,
                    price_vnd INTEGER NOT NULL,
                    stock_qty INTEGER NOT NULL DEFAULT 0,
                    image_url TEXT,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
                """
            )
        )
    ensure_home_equipment_catalog_v2(engine)
    with engine.begin() as conn:
        shop = conn.execute(text("SELECT COUNT(*) FROM shop_products")).scalar()
        rings = conn.execute(
            text("SELECT COUNT(*) FROM equipment WHERE slug = 'gymnastic-rings'")
        ).scalar()
    assert shop == 0
    assert rings == 1
